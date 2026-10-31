#!/usr/bin/env node
/**
 * LinkNodes MCP server (stdio).
 * Calls the public https://www.linknodes.io /v1 API. No API key.
 * stdout is the MCP JSON-RPC channel — log only to stderr.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { apiBase, errorResult, fetchJson, searchFeeds, textResult, timeoutMs } from "./client.js";

const BASE = apiBase();
const TIMEOUT = timeoutMs();

let registryCache = { at: 0, env: "", data: null };
const REGISTRY_TTL_MS = 10 * 60 * 1000;

async function getRegistry(environment = "mainnet") {
  const env = environment || "mainnet";
  const now = Date.now();
  if (registryCache.data && registryCache.env === env && now - registryCache.at < REGISTRY_TTL_MS) {
    return registryCache.data;
  }
  const data = await fetchJson(`/v1/registry?environment=${encodeURIComponent(env)}`, {
    base: BASE,
    timeout: TIMEOUT,
  });
  registryCache = { at: now, env, data };
  return data;
}

function createServer() {
  const server = new McpServer({
    name: "linknodes",
    version: "0.1.0",
  });

  server.tool(
    "search_feeds",
    "Search the LinkNodes Data Feeds catalog by name, slug, or chain. Metadata only (no live price).",
    {
      query: z.string().optional().describe("Name or slug substring, e.g. eth-usd or gold"),
      network: z.string().optional().describe("Chain slug, e.g. ethereum, arbitrum, base"),
      environment: z.string().optional().describe("mainnet or testnet"),
      limit: z.number().int().min(1).max(25).optional().describe("Max results, default 15"),
    },
    async ({ query, network, environment, limit }) => {
      try {
        const registry = await getRegistry(environment || "mainnet");
        return textResult(searchFeeds(registry, { query, network, limit }));
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "lookup_feed",
    "Live latestRoundData (or historical getRoundData) for one Chainlink Data Feed.",
    {
      network: z.string().describe("Chain slug, e.g. ethereum or base"),
      feed: z.string().describe("Feed slug, e.g. eth-usd"),
      round_id: z.number().int().optional().describe("Historical round id; omit for latest"),
      environment: z.string().optional().describe("mainnet or testnet"),
    },
    async ({ network, feed, round_id, environment }) => {
      try {
        const params = new URLSearchParams();
        if (environment) params.set("environment", environment);
        if (round_id != null) params.set("round_id", String(round_id));
        const qs = params.toString();
        const path = `/v1/query/${encodeURIComponent(network)}/${encodeURIComponent(feed)}${qs ? `?${qs}` : ""}`;
        return textResult(await fetchJson(path, { base: BASE, timeout: TIMEOUT }));
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "compare_feed",
    "Query the same Data Feed on every chain it is deployed on; includes spread_bps.",
    {
      feed: z.string().describe("Feed slug, e.g. eth-usd"),
      environment: z.string().optional().describe("mainnet or testnet"),
    },
    async ({ feed, environment }) => {
      try {
        const qs = environment ? `?environment=${encodeURIComponent(environment)}` : "";
        return textResult(
          await fetchJson(`/v1/compare/${encodeURIComponent(feed)}${qs}`, { base: BASE, timeout: TIMEOUT }),
        );
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "ccip_registry",
    "List CCIP networks, routers, chain selectors, and supported destinations.",
    {
      environment: z.string().optional().describe("mainnet or testnet"),
    },
    async ({ environment }) => {
      try {
        const qs = environment ? `?environment=${encodeURIComponent(environment)}` : "";
        return textResult(await fetchJson(`/v1/ccip/registry${qs}`, { base: BASE, timeout: TIMEOUT }));
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "ccip_lane",
    "Look up one CCIP lane (source -> destination): routers, selectors, RMN proxies.",
    {
      source: z.string().describe("Source chain slug, e.g. ethereum"),
      destination: z.string().describe("Destination chain slug, e.g. arbitrum"),
      environment: z.string().optional().describe("mainnet or testnet"),
    },
    async ({ source, destination, environment }) => {
      try {
        const qs = environment ? `?environment=${encodeURIComponent(environment)}` : "";
        return textResult(
          await fetchJson(
            `/v1/ccip/lane/${encodeURIComponent(source)}/${encodeURIComponent(destination)}${qs}`,
            { base: BASE, timeout: TIMEOUT },
          ),
        );
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "list_streams_247",
    "List-only catalog of Chainlink 24/7 Data Streams (feed IDs, no live report prices).",
    {},
    async () => {
      try {
        return textResult(await fetchJson("/v1/streams-247", { base: BASE, timeout: TIMEOUT }));
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "list_operators",
    "Curated directory of well-known Chainlink node operators.",
    {},
    async () => {
      try {
        return textResult(await fetchJson("/v1/operators", { base: BASE, timeout: TIMEOUT }));
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  server.tool(
    "agents_catalog",
    "Cached Chainlink for Agents gateway catalog, including published USDC prices when the unpaid catalog document included them.",
    {},
    async () => {
      try {
        return textResult(await fetchJson("/v1/agents/catalog", { base: BASE, timeout: TIMEOUT }));
      } catch (err) {
        return errorResult(err);
      }
    },
  );

  return server;
}

async function main() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`linknodes-mcp stdio listening (API ${BASE}, timeout ${TIMEOUT}ms)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
