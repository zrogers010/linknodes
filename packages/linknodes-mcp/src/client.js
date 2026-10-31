const DEFAULT_BASE = "https://www.linknodes.io";
const DEFAULT_TIMEOUT_MS = 15_000;
const SEARCH_LIMIT_MAX = 25;

export function apiBase(env = process.env) {
  return (env.LINKNODES_API_BASE || DEFAULT_BASE).replace(/\/$/, "");
}

export function timeoutMs(env = process.env) {
  const parsed = Number(env.LINKNODES_TIMEOUT_MS);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_TIMEOUT_MS;
}

export async function fetchJson(path, { base, timeout, fetchImpl } = {}) {
  const url = `${base || apiBase()}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout ?? timeoutMs());
  try {
    const fetchFn = fetchImpl || fetch;
    const response = await fetchFn(url, {
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "User-Agent": "linknodes-mcp/0.1.0 (+https://www.linknodes.io)",
      },
    });
    const text = await response.text();
    let body;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { error: "non-JSON response", text };
    }
    if (!response.ok) {
      const detail = body && typeof body === "object" ? body.detail || body.error : text;
      throw new Error(`HTTP ${response.status} ${url}: ${detail || response.statusText}`);
    }
    return body;
  } catch (err) {
    if (err && err.name === "AbortError") {
      throw new Error(`Timed out after ${timeout ?? timeoutMs()}ms: ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export function searchFeeds(registry, { query = "", network = "", limit = 15 } = {}) {
  const q = String(query || "").trim().toLowerCase();
  const netFilter = String(network || "").trim().toLowerCase();
  const cap = Math.max(1, Math.min(Number(limit) || 15, SEARCH_LIMIT_MAX));
  const matches = [];
  const networks = registry && registry.networks ? registry.networks : {};
  for (const [netSlug, net] of Object.entries(networks)) {
    if (netFilter && netSlug !== netFilter) continue;
    const feeds = net.feeds || {};
    for (const [slug, feed] of Object.entries(feeds)) {
      const name = String(feed.name || "").toLowerCase();
      if (q && !slug.includes(q) && !name.includes(q)) continue;
      matches.push({
        network: netSlug,
        network_label: net.label,
        feed: slug,
        name: feed.name,
        address: feed.address,
        decimals: feed.decimals,
        heartbeat: feed.heartbeat,
        category: feed.category,
      });
      if (matches.length >= cap) {
        return { count: matches.length, truncated: true, results: matches };
      }
    }
  }
  return { count: matches.length, truncated: false, results: matches };
}

export function textResult(payload, isError = false) {
  return {
    content: [{ type: "text", text: typeof payload === "string" ? payload : JSON.stringify(payload, null, 2) }],
    isError,
  };
}

export function errorResult(err) {
  return textResult({ error: err instanceof Error ? err.message : String(err) }, true);
}
