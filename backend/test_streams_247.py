"""24/7 stream sidecar + compact() flags. Does not change on-chain feed shape tests."""

import json
from pathlib import Path

from build_registry import (
    _is_247_stream_entry,
    compact,
    compact_247_stream,
    extract_247_streams,
    include,
)


def _stream_fixture(**overrides):
    feed = {
        "name": "TSLA/USD-Streams-247-mainnet-production",
        "path": "tsla-usd-streams-247-mainnet-production",
        "proxyAddress": None,
        "feedId": "0x0002b9e03e28cc440c411328950626324203d6de30ecbe778debb7a812aad324",
        "feedType": "247Price",
        "assetName": "Tesla",
        "sourceChain": 42161,
        "docs": {
            "assetClass": "Equities",
            "attributeType": "247",
            "baseAsset": "TSLA",
            "quoteAsset": "USD",
            "productTypeCode": "247",
            "schema": "v2",
            "feedType": "247Price",
            "marketHours": "Crypto",
        },
    }
    feed.update(overrides)
    if "docs" in overrides:
        docs = dict(feed["docs"])
        docs.update(overrides["docs"])
        feed["docs"] = docs
    return feed


def test_streams_are_excluded_from_onchain_registry():
    assert include(_stream_fixture()) is False


def test_custom_price_v11_is_not_a_v2_stream():
    feed = _stream_fixture(
        name="GOOGL/USD-Streams-247CustomPrice-mainnet-production",
        docs={"schema": "v11"},
    )
    assert _is_247_stream_entry(feed) is False


def test_stream_with_proxy_is_rejected():
    feed = _stream_fixture(proxyAddress="0x369C67E8b026CC4Ef98350f332D7Dd52b85b7674")
    assert _is_247_stream_entry(feed) is False


def test_extract_seventeen_unique_v2_streams():
    raw = [
        _stream_fixture(),
        _stream_fixture(),  # duplicate feedId
        _stream_fixture(
            name="XAU/USD-Streams-247-mainnet-production",
            path="xau-usd-streams-247-mainnet-production",
            feedId="0xaaa",
            docs={"baseAsset": "XAU", "quoteAsset": "USD", "assetClass": "Forex", "schema": "v2"},
        ),
        _stream_fixture(
            name="GOOGL/USD-Streams-247CustomPrice-mainnet-production",
            feedId="0xbbb",
            docs={"schema": "v11"},
        ),
    ]
    streams = extract_247_streams(raw, "arbitrum", 42161)
    assert len(streams) == 2
    by_base = {s["base"]: s for s in streams}
    assert by_base["TSLA"]["schema"] == "v2"
    assert by_base["TSLA"]["asset_class"] == "Equities"
    assert by_base["XAU"]["asset_class"] == "Commodities"
    assert "address" not in streams[0]
    assert "proxy" not in streams[0]
    compacted = compact_247_stream(_stream_fixture(), "arbitrum", 42161)
    assert compacted["feed_id"].startswith("0x")
    assert compacted["chain_id"] == 42161


def test_compact_saves_attribute_type_and_is_247():
    feed = {
        "name": "tGLD/USD - 24/7 Blended Price",
        "path": "tgld-usd",
        "proxyAddress": "0x369C67E8b026CC4Ef98350f332D7Dd52b85b7674",
        "docs": {
            "attributeType": "247",
            "productTypeCode": "247",
            "productType": "Price",
            "baseAsset": "tGLD",
            "quoteAsset": "USD",
            "marketHours": "Crypto",
        },
    }
    compacted = compact(feed)
    assert compacted["attribute_type"] == "247"
    assert compacted["product_type_code"] == "247"
    assert compacted["is_247"] is True
    assert compacted["address"] == feed["proxyAddress"]


def test_committed_streams_file_shape():
    path = Path(__file__).parent / "streams_247.json"
    if not path.exists():
        return
    doc = json.loads(path.read_text())
    assert doc["count"] == len(doc["streams"])
    assert doc["count"] == 17
    assert doc["chain_id"] == 42161
    names = {s["name"] for s in doc["streams"]}
    assert "TSLA/USD-Streams-247-mainnet-production" in names
    assert all(s.get("schema") == "v2" for s in doc["streams"])
    assert all(s.get("feed_id") for s in doc["streams"])
    assert all("address" not in s for s in doc["streams"])
    # Do not claim on-chain 24/7 stock feeds
    assert "proxy" not in json.dumps(doc).lower() or all(
        not s.get("proxyAddress") for s in doc["streams"]
    )
