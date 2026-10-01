# LinkNodes.io — The Developer Toolkit for Chainlink

The "Postman" for Chainlink. A free, un-gated web platform for interactively testing
**every Chainlink service** — Data Feeds, CCIP, Functions, VRF, and Automation. The Data
Feeds sandbox is fully live with 1,400+ feeds across 13 mainnets. Additional product
sandboxes offer interactive previews, architecture exploration, and example code for the
complete Chainlink suite.

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

### Homepage & Product Suite (`/`)
- **Marketing homepage** — hero, value proposition, and product cards for the complete
  Chainlink suite (Data Feeds, CCIP, Functions, VRF, Automation)
- **Product navigation** — unified tabs across all Chainlink services with consistent UX

### Product Sandboxes
- **Data Feeds (`/products/data-feeds`)** — fully live interactive sandbox: query 1,400+
  feeds across 13 chains, time-travel through historical rounds, grab production snippets.
  The flagship feature with real mainnet data.
- **CCIP (`/products/ccip`)** — cross-chain messaging preview: explore chain selectors,
  message structures, and transfer flows. Full testnet sandbox coming soon.
- **Functions (`/products/functions`)** — serverless compute preview: example JavaScript
  scripts, API integration patterns, execution flow. Full testnet executor coming soon.
- **VRF (`/products/vrf`)** — verifiable randomness preview: simulate random number
  generation, explore use cases, integration examples. Full testnet sandbox coming soon.
- **Automation (`/products/automation`)** — keeper preview: design upkeep logic,
  understand execution flow, explore automation strategies. Full testnet registration
  coming soon.

### Secondary Pages
- **Feed Catalog (`/feeds`)** — every feed aggregated across chains as sortable cards.
  Sort by chain coverage, fastest heartbeat, or name; filter by asset class.
- **Node Operators (`/operators`)** — curated directory of well-known Chainlink node
  operators served from `backend/operators.json`.

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

## Deployment

### Local Development (docker-compose)

One command to run both services (frontend on :8080, nginx proxies `/v1` to the engine):

```bash
docker compose up --build
```

### Production (AWS App Runner, ~$10-15/month)

Production-ready Dockerfiles are provided for both backend and frontend services. Deploy as two separate App Runner services with automatic scaling and monitoring.

**See [docs/DEPLOY_APP_RUNNER.md](docs/DEPLOY_APP_RUNNER.md)** for the complete step-by-step guide covering:
- Building and pushing images to ECR
- Creating backend and frontend App Runner services
- Custom domain configuration
- Cost estimates and monitoring
- CI/CD setup options

The backend container refreshes the feed catalog from Chainlink's directory at every
start, so redeploys automatically pick up newly launched feeds.

### Other Options

- **Backend:** any container platform (Fly.io, Railway, Cloud Run). Stateless design — scale horizontally by adding replicas.
- **Frontend:** `npm run build` produces a static bundle; host on any CDN (Cloudflare Pages, Netlify, S3). Configure `VITE_API_BASE_URL` during build to point to your backend API.
