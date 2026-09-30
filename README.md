# LinkNodes.io — The Oracle Query Sandbox for Chainlink Developers

The "Postman" for Chainlink. A free, un-gated web utility for interactively querying the
**entire Chainlink Data Feeds catalog** — 1,400+ live feeds across 13 mainnet chains —
with no code, no account, and no API key. Search any feed (crypto, forex, equities,
commodities, macro), fire a live on-chain read, time-travel through historical rounds,
and grab production-ready integration snippets.

## Architecture

```
frontend (React + Tailwind, static)  ──►  backend (FastAPI, stateless)
                                              │
                                              ▼
                                   free public RPC nodes
                                   (eth_call, read-only, with failover)
```

- **No database, no cache layer, no blockchain node.** Every query is a set of concurrent
  read-only `eth_call`s via `web3.py` `AsyncWeb3` + `asyncio.gather`.
- **Full official catalog.** `backend/build_registry.py` ingests Chainlink's own
  reference-data directory (the source behind docs.chain.link) and compiles
  `registry.json`: feed addresses, decimals, heartbeats, deviation thresholds, risk
  categories, and market hours for every visible mainnet feed. Loaded into memory at
  boot for O(1) lookups; refresh anytime by re-running the script.
- **RPC failover.** Each chain lists multiple free public RPCs; the engine falls through
  on infrastructure failures while surfacing deterministic contract reverts honestly.
- **Micro-cache + rate limit.** Latest-round responses cache in-memory for 5 s
  (historical rounds for 1 h — they're immutable), bounding upstream RPC load to
  O(feeds) instead of O(users). A per-IP limit of 120 req/min protects the shared
  public RPCs without ever bothering a human user.
- **Historical rounds.** Add `round_id` to any query to hit `getRoundData()` instead of
  `latestRoundData()`.
- **Cross-chain compare.** `GET /v1/compare/{feed}` queries a feed on every chain it's
  deployed on concurrently and reports per-chain prices plus the spread in bps.
- **Shareable state.** Selections sync to URL params (`?chain=arbitrum&feed=xau-usd`)
  so any console state can be pasted into a team channel.

## Pages

- **Sandbox (`/`)** — the interactive query console: pick a chain and feed, fire live or
  historical reads, grab integration snippets.
- **Feed Catalog (`/feeds`)** — every feed aggregated across chains as sortable cards.
  Sort by chain coverage (the best public proxy for feed adoption), fastest heartbeat,
  or name; filter by asset class; click any chain chip to open that exact route in the
  sandbox.
- **Node Operators (`/operators`)** — a curated directory of well-known Chainlink node
  operators (independents, staking providers, telecoms, enterprises) served from
  `backend/operators.json`. Chainlink publishes no official operator directory, so this
  list is illustrative and clearly labeled as such.

## Running locally

Backend (port 8000):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build_registry.py   # optional: refresh the feed catalog
.venv/bin/uvicorn main:app --port 8100
```

Frontend (port 5173, proxies `/v1` to the backend):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## API

| Endpoint | Description |
| --- | --- |
| `GET /v1/registry` | Full static catalog (chains, feeds, metadata) — gzipped to ~66 KB |
| `GET /v1/query/{chain}/{feed}` | Live `latestRoundData()` read |
| `GET /v1/query/{chain}/{feed}?round_id=N` | Historical `getRoundData()` read |
| `GET /v1/compare/{feed}` | Query a feed on every deployed chain, with spread summary |
| `GET /v1/operators` | Curated node operator directory |
| `GET /healthz` | Liveness probe + catalog stats |

Examples:

```bash
curl "http://localhost:8100/v1/query/arbitrum/xau-usd"
curl "http://localhost:8100/v1/query/ethereum/aapl-usd"
curl "http://localhost:8100/v1/query/arbitrum/eur-usd?round_id=36893488147419105538"
```

## Supported chains

Ethereum, Arbitrum One, Base, OP Mainnet, Polygon PoS, Avalanche C-Chain,
BNB Smart Chain, Gnosis, Scroll, Linea, Celo, Sonic, ZKsync Era.

Adding a chain is a single entry in `build_registry.py` (RDD file + RPC URLs) — no code
changes anywhere else.

## Deployment (< $10/month)

One command with Docker (frontend on :8080, nginx proxies `/v1` to the engine and
serves the SPA with fallback):

```bash
docker compose up --build
```

The backend container refreshes the feed catalog from Chainlink's directory at every
start, so redeploys automatically pick up newly launched feeds.

Or piece by piece:

- **Backend:** any single small container/instance (Fly.io, Railway, a $5 VPS). It is
  stateless — scale horizontally by just adding replicas.
- **Frontend:** `npm run build` produces a static bundle; host on any static CDN tier
  (Cloudflare Pages, Netlify, S3). Point the host's `/v1/*` rewrite at the backend and
  enable SPA fallback (serve `index.html` for unknown paths) so `/feeds` and
  `/operators` resolve on hard refresh.
