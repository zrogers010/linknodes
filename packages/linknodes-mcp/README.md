# linknodes-mcp

Read-only [MCP](https://modelcontextprotocol.io) server for the public [LinkNodes](https://www.linknodes.io) API. It runs **on your machine** (stdio) and calls `https://www.linknodes.io`. No API key. No extra LinkNodes hosting.

This package is **not published yet**. The repo owner will publish it to npm. Until then, run it from a clone.

## Tools

| Tool | What it calls |
| --- | --- |
| `search_feeds` | `GET /v1/registry` (cached 10 min) then filters locally |
| `lookup_feed` | `GET /v1/query/{network}/{feed}` |
| `compare_feed` | `GET /v1/compare/{feed}` |
| `ccip_registry` | `GET /v1/ccip/registry` |
| `ccip_lane` | `GET /v1/ccip/lane/{source}/{dest}` |
| `list_streams_247` | `GET /v1/streams-247` |
| `list_operators` | `GET /v1/operators` |
| `agents_catalog` | `GET /v1/agents/catalog` |

All tools are read-only. Timeouts default to 15 seconds (`LINKNODES_TIMEOUT_MS`). Override the API host with `LINKNODES_API_BASE` (local backend: `http://127.0.0.1:8100`).

## Run from a clone

```bash
cd packages/linknodes-mcp
npm install
node src/index.js
```

The process waits on stdin. Do not `console.log` — stdout is the MCP channel.

## Cursor

In Cursor MCP settings (`~/.cursor/mcp.json` or project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "linknodes": {
      "command": "node",
      "args": ["/absolute/path/to/linknodes/packages/linknodes-mcp/src/index.js"],
      "env": {
        "LINKNODES_API_BASE": "https://www.linknodes.io"
      }
    }
  }
}
```

After the owner publishes to npm:

```json
{
  "mcpServers": {
    "linknodes": {
      "command": "npx",
      "args": ["-y", "linknodes-mcp"]
    }
  }
}
```

## Claude Code

From a clone:

```bash
claude mcp add --transport stdio linknodes -- node /absolute/path/to/linknodes/packages/linknodes-mcp/src/index.js
```

After publish:

```bash
claude mcp add --transport stdio linknodes -- npx -y linknodes-mcp
```

## Optional: hosted Streamable HTTP

The same tools are also mounted on the **existing** LinkNodes backend at `/mcp` (no new AWS service). Use the backend service URL, or `https://www.linknodes.io/mcp` only after the production proxy forwards `/mcp` the same way it already forwards `/v1`.

```json
{
  "mcpServers": {
    "linknodes": {
      "url": "https://www.linknodes.io/mcp"
    }
  }
}
```

Prefer the stdio package if that path is not proxied yet.

## Publish (repo owner)

Do **not** publish from CI or from an agent. From a clean tree, after reviewing the version in `package.json`:

```bash
cd packages/linknodes-mcp
npm login
npm publish --access public
```

Then bump `version` for the next release. The package name is `linknodes-mcp` (unscoped). Change it to `@linknodes/mcp` before the first publish if you want a scope.
