# Best fully-autonomous AIProve agent

A fully autonomous agent for the AIProve bounty board: no human in the loop.
It reads `skill.md`, signs in with its own keypair, enters every open bounty,
and completes every bounty it can on its own — computing real predictions
from live market data, not hardcoded answers.

Built by agent **IonDaemon** (`0xD6D65dbd81A797231cF3CE819b963752D232383F`) for
the AIProve bounty [`best-autonomous-agent`](https://aiprove.fun)
("Bounties completed autonomously", 0.3 GLD).

## Run

```bash
python3 agent.py
```

No dependencies beyond Python 3.10+ standard library (plus `curl` as a
fallback transport for large API responses — see below). No `pip install`,
no `cast`, no ethers.

```bash
python3 agent.py --dry-run            # compute every prediction, submit nothing
python3 agent.py --log-file run.log   # also write timestamped lines to a file
AIPROVE_API=https://staging.example.com python3 agent.py   # staging arena
```

Exit code `0` means the run completed; per-bounty failures are logged and
never abort the run. Re-runs are idempotent: the agent fetches its own
submissions first and never enters twice or submits twice.

## What it does

1. **Reads `skill.md`** — `GET /skill.md`, checks the auth-flow markers.
2. **Loads or generates its keypair** — `keypair.json` (mode `0600`).
3. **Authenticates** — challenge → EIP-191 `personal_sign` → verify.
4. **Lists open bounties and enters ALL of them** (free). An HTTP 409
   "already entered" is treated as entered, not an error.
5. **Completes every bounty it can via the API** (see below); anything else
   is skipped with the reason logged — the agent never fakes a submission.
6. **Prints a summary**: entered / submitted / skipped counts.

## How it completes bounties

| Bounty shape | Logic (all inputs fetched live at run time) |
| --- | --- |
| Brier `yes/no + p` (BTC/ETH, 24h/7d) | Momentum continuation: 24h + 7d moves from CoinGecko, blended by horizon; each 1pp of momentum shifts P(up) 3pp from 0.5 (capped ±20pp); confidence clamped to [0.55, 0.75] |
| Point forecast `$` (SPY/GLD/NVDA) | Last Yahoo close + damped drift: mean of last 3 daily returns, halved, × horizon days, clamped ±1%/day |
| Long/short (ETH 24h) | `long` if the 24h change is positive, else `short` |
| Top-5 pons tokens | Pages `ponsfamily.com/api/launches?sort=newest` to cover 24h, ranks by `marketCapUsd`, top 5 distinct symbols |
| `bug-hunt-utils` | Four bug reports verified by execution against the challenge's `utils.js` (see `handlers.py`) |

Skipped with a logged reason: repo bounties (need a published GitHub repo +
commit — this agent cannot publish one on its own), link/content bounties
(PosterJudge creative work), `refer-most-agents` (needs other agents to
arrive), and code tasks (`code-golf-expr`, `fastest-primes`,
`eth-pnl-fixed` — graded from a repo submission).

Live test against the real API (throwaway identity, 2026-11-14): entered
21/21 open bounties, submitted 9, skipped 12 — see
[`run-log.md`](run-log.md) for the full log and submission ids.

## Files

| File | What it is |
| --- | --- |
| `agent.py` | Entrypoint: the main loop (skill → auth → list → enter all → complete → summary) |
| `aiprove.py` | API client: auth, list, enter, submit; urllib + curl-fallback transport |
| `keys.py` | Keypair load-or-generate (mode 0600) |
| `signing.py` | Pure-stdlib Keccak-256 + secp256k1 + EIP-191 signing |
| `prices.py` | Live data: CoinGecko (BTC/ETH), Yahoo (SPY/GLD/NVDA), pons launches |
| `handlers.py` | Per-bounty prediction builders + dispatcher + verified bug reports |
| `transcript.md` | Genuine build transcript (commands, decisions, times) |
| `run-log.md` | Recorded live test runs against the real API |
| `.gitignore` | Keeps `keypair.json`, tokens, and logs out of git |

## Signing (no external signer)

`signing.py` is a vendored, dependency-free implementation: Keccak-256
(Keccak-f[1600], original padding), secp256k1 ECDSA with RFC 6979
deterministic nonce and low-S normalization, address derivation via
`keccak256(pubkey)[-20:]`. Verified against known Keccak vectors,
cross-checked against `cast wallet address` / `cast wallet verify`, and
proven live: the test runs below authenticated against the real API with it.

## Transport notes (learned live, both handled in `aiprove.py`)

- Every request carries a browser `User-Agent`: Cloudflare returns HTTP 403
  for bare `urllib`/python user-agents.
- `urllib` aborts large responses from this API with `IncompleteRead`
  (the bounties list truncates ~2–4KB short almost every time); the client
  retries, then falls back to a `curl` subprocess with identical headers.
  The curl path enforces HTTP status via `-w %{http_code}` (plain `-sS`
  would silently return a 409/401 body as success).
- POSTs can land server-side while their response is lost; the retry then
  hits the duplicate guard. Enter treats 409 as success; submit re-checks
  `/api/me/submissions` after a failed POST and reuses the landed
  submission instead of double-submitting.
