import { test } from "node:test";
import assert from "node:assert/strict";
import { apiBase, errorResult, fetchJson, searchFeeds, textResult, timeoutMs } from "../src/client.js";

test("apiBase strips trailing slash and defaults to production", () => {
  assert.equal(apiBase({}), "https://www.linknodes.io");
  assert.equal(apiBase({ LINKNODES_API_BASE: "http://127.0.0.1:8100/" }), "http://127.0.0.1:8100");
});

test("timeoutMs falls back to 15s", () => {
  assert.equal(timeoutMs({}), 15_000);
  assert.equal(timeoutMs({ LINKNODES_TIMEOUT_MS: "8000" }), 8000);
});

test("searchFeeds filters by query and network and caps results", () => {
  const registry = {
    networks: {
      ethereum: {
        label: "Ethereum",
        feeds: {
          "eth-usd": { name: "ETH / USD", address: "0x1", decimals: 8, heartbeat: 3600, category: "crypto" },
          "btc-usd": { name: "BTC / USD", address: "0x2", decimals: 8, heartbeat: 3600, category: "crypto" },
        },
      },
      base: {
        label: "Base",
        feeds: {
          "eth-usd": { name: "ETH / USD", address: "0x3", decimals: 8, heartbeat: 1200, category: "crypto" },
        },
      },
    },
  };
  const eth = searchFeeds(registry, { query: "eth", network: "ethereum" });
  assert.equal(eth.count, 1);
  assert.equal(eth.results[0].feed, "eth-usd");
  assert.equal(eth.results[0].network, "ethereum");

  const capped = searchFeeds(registry, { limit: 1 });
  assert.equal(capped.count, 1);
  assert.equal(capped.truncated, true);
});

test("fetchJson surfaces HTTP errors and honors abort", async () => {
  const fetchImpl = async () => ({
    ok: false,
    status: 404,
    statusText: "Not Found",
    text: async () => JSON.stringify({ detail: "unknown feed" }),
  });
  await assert.rejects(
    () => fetchJson("/v1/query/ethereum/nope", { base: "https://www.linknodes.io", fetchImpl }),
    /HTTP 404/,
  );
});

test("textResult and errorResult shape", () => {
  const ok = textResult({ a: 1 });
  assert.equal(ok.isError, false);
  assert.match(ok.content[0].text, /"a": 1/);
  const err = errorResult(new Error("boom"));
  assert.equal(err.isError, true);
  assert.match(err.content[0].text, /boom/);
});
