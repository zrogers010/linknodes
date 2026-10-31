"""
Chainlink for Agents catalog builder
====================================
Fetches the public gateway catalog at agents.chain.link and writes
backend/agents_catalog.json.

The list endpoint (GET /v1/catalog) returns name + description only.
Per-item detail (GET /v1/catalog/{name}) is also unpaid and includes
kind, execute_endpoint, and price_usdc when the gateway publishes a
price. HEAD /v1/catalog returns 404; always use GET.

On fetch or validation failure the last good file is left in place
so a downed gateway does not wipe the cached catalog. The daily
refresh workflow keeps running.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

GATEWAY_BASE = "https://agents.chain.link"
CATALOG_URL = f"{GATEWAY_BASE}/v1/catalog"
USER_AGENT = "LinkNodesCatalogRefresh/1.0 (+https://www.linknodes.io)"
TIMEOUT_S = 20.0
OUTPUT_FILENAME = "agents_catalog.json"

# Drop more than this fraction of items vs last good copy → keep last good.
MAX_SHRINK_RATIO = 0.5


def empty_catalog() -> dict:
    return {
        "version": "1.0.0",
        "source": "chainlink-agents-gateway",
        "source_url": CATALOG_URL,
        "generated_at": None,
        "status": "empty",
        "count": 0,
        "workflows": [],
    }


def load_selector_labels(ccip_path: Path) -> dict[str, str]:
    """Map CCIP chain selectors to labels from our own registry (no guesswork)."""
    if not ccip_path.exists():
        return {}
    try:
        data = json.loads(ccip_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    labels: dict[str, str] = {}
    for net in data.get("networks", {}).values():
        selector = net.get("chain_selector")
        label = net.get("label")
        if selector and label:
            labels[str(selector)] = label
    return labels


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=TIMEOUT_S,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def fetch_catalog_list(client: httpx.Client) -> tuple[list, int]:
    response = client.get(CATALOG_URL)
    if response.status_code != 200:
        raise RuntimeError(f"{CATALOG_URL} returned HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("catalog list is empty or not an array")
    for entry in payload:
        if not isinstance(entry, dict) or not entry.get("name"):
            raise RuntimeError("catalog list entry missing name")
    return payload, response.status_code


def fetch_catalog_item(client: httpx.Client, name: str) -> dict:
    url = f"{CATALOG_URL}/{name}"
    response = client.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"{url} returned HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("name") != name:
        raise RuntimeError(f"{url} returned unexpected body")
    return payload


def normalize_item(raw: dict, selector_labels: dict[str, str]) -> dict:
    """Keep only public, verified fields. Omit price unless the gateway sent it."""
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise RuntimeError("workflow missing name")

    item: dict = {
        "name": name,
        "description": raw.get("description") if isinstance(raw.get("description"), str) else "",
        "kind": raw.get("kind") if isinstance(raw.get("kind"), str) else None,
        "execute_endpoint": raw.get("execute_endpoint") if isinstance(raw.get("execute_endpoint"), str) else None,
    }

    price = raw.get("price_usdc")
    if isinstance(price, (str, int, float)) and str(price) != "":
        item["price_usdc"] = str(price)
    else:
        item["price_usdc"] = None

    overrides = raw.get("chain_selector_price_overrides_usdc")
    labeled: list[dict] = []
    if isinstance(overrides, dict):
        for selector, override_price in overrides.items():
            if not isinstance(override_price, (str, int, float)):
                continue
            entry = {
                "chain_selector": str(selector),
                "price_usdc": str(override_price),
            }
            if str(selector) in selector_labels:
                entry["network_label"] = selector_labels[str(selector)]
            labeled.append(entry)
    item["price_overrides"] = labeled

    tier = raw.get("price_tier")
    item["price_tier"] = tier if isinstance(tier, str) else None

    schema = raw.get("input_schema")
    if isinstance(schema, dict):
        item["input_params"] = [
            {
                "name": key,
                "type": value.get("type") if isinstance(value, dict) else None,
                "required": bool(value.get("required")) if isinstance(value, dict) else False,
            }
            for key, value in schema.items()
            if isinstance(key, str)
        ]
    else:
        item["input_params"] = []

    return item


def build_catalog(selector_labels: dict[str, str] | None = None) -> tuple[dict, dict[str, int]]:
    labels = selector_labels or {}
    http_status: dict[str, int] = {}
    with _client() as client:
        listing, status = fetch_catalog_list(client)
        http_status[CATALOG_URL] = status
        workflows = []
        for entry in listing:
            name = entry["name"]
            detail = fetch_catalog_item(client, name)
            http_status[f"{CATALOG_URL}/{name}"] = 200
            workflows.append(normalize_item(detail, labels))

    workflows.sort(key=lambda w: (w.get("kind") or "z", w["name"]))
    return {
        "version": "1.0.0",
        "source": "chainlink-agents-gateway",
        "source_url": CATALOG_URL,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok",
        "count": len(workflows),
        "workflows": workflows,
    }, http_status


def validate_catalog(catalog: dict) -> None:
    if catalog.get("version") != "1.0.0":
        raise RuntimeError("catalog version must be 1.0.0")
    workflows = catalog.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        raise RuntimeError("catalog has no workflows")
    names = []
    for item in workflows:
        if not isinstance(item, dict) or not item.get("name"):
            raise RuntimeError("workflow entry missing name")
        names.append(item["name"])
    if len(names) != len(set(names)):
        raise RuntimeError("catalog has duplicate workflow names")
    if catalog.get("count") != len(workflows):
        raise RuntimeError("catalog count does not match workflows length")


def should_keep_last_good(new_catalog: dict, previous: dict | None) -> str | None:
    """Return a reason to keep the last good copy, or None to write."""
    try:
        validate_catalog(new_catalog)
    except RuntimeError as exc:
        return str(exc)
    if previous:
        old_count = previous.get("count") or len(previous.get("workflows") or [])
        new_count = new_catalog["count"]
        if old_count and new_count < old_count * MAX_SHRINK_RATIO:
            return f"new catalog shrank from {old_count} to {new_count} items"
    return None


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".agents_catalog.", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_existing(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def refresh_catalog(output_path: Path, ccip_path: Path, strict: bool = False) -> int:
    previous = load_existing(output_path)
    labels = load_selector_labels(ccip_path)
    try:
        catalog, statuses = build_catalog(labels)
    except Exception as exc:
        print(f"WARNING: agents catalog fetch failed: {exc}", file=sys.stderr)
        print(f"Keeping last good copy at {output_path}", file=sys.stderr)
        if strict or previous is None:
            return 1
        return 0

    keep_reason = should_keep_last_good(catalog, previous)
    if keep_reason:
        print(f"WARNING: rejecting new catalog ({keep_reason})", file=sys.stderr)
        print(f"Keeping last good copy at {output_path}", file=sys.stderr)
        if strict or previous is None:
            return 1
        return 0

    atomic_write(output_path, catalog)
    print(f"Wrote {catalog['count']} workflows to {output_path}")
    for url, code in statuses.items():
        print(f"  {code} {url}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the cached Chainlink for Agents catalog")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the gateway is down or the new catalog is rejected",
    )
    args = parser.parse_args()
    backend = Path(__file__).parent
    return refresh_catalog(
        output_path=backend / OUTPUT_FILENAME,
        ccip_path=backend / "ccip_registry.json",
        strict=args.strict,
    )


if __name__ == "__main__":
    sys.exit(main())
