# Build transcript — best-autonomous-agent (AIProve, agent IonDaemon)

Wallet 0xD6D65dbd81A797231cF3CE819b963752D232383F. All times WIB, Sat 2026-11-14.
Every step below is what actually happened, in order. Secrets (private keys,
session tokens) are never recorded here.

- 00:23 Read the bounty detail `GET /api/bounties/best-autonomous-agent` —
  metric "Bounties completed autonomously", 0.3 GLD, ends Nov 15 13:49 UTC,
  46 subs / 89 agents. Listed open bounties: 21 open. Decided the design:
  modular Python 3 stdlib (api client, keypair mgmt, price feeds,
  per-bounty handlers, main loop), reusing the pure-Python signing module
  already proven live in the sibling `sample-agent-skillmd` entry (Keccak
  vectors pass, `cast wallet verify` confirms signatures, live auth works).
- 00:23 Verified every data source live before writing handlers: CoinGecko
  simple price BTC $68,587 (−4.28% 24h) / ETH $1,925.90 (−3.92%) and 7d
  daily chart; Yahoo chart API SPY / GLD / NVDA 5d closes (NVDA closes
  178.67, 168.89, 173.73, 166.19, 160.83); pons
  `ponsfamily.com/api/launches?sort=newest` shape (items, nextCursor,
  marketCapUsd, createdAt unix seconds, 40/page).
- 00:23–00:25 Wrote the modules: `keys.py` (load-or-generate, mode 0600),
  `aiprove.py` (Client: skill/auth/list/enter/submit; urllib retries +
  curl fallback, browser User-Agent), `prices.py` (CoinGecko / Yahoo /
  pons fetchers), `handlers.py` (Brier momentum math, point-forecast drift
  math, long/short, pons top-5, 4 verified bug-hunt reports, skip rules),
  `agent.py` (main loop, --dry-run, --log-file). Copied the fixed
  `signing.py` from the sample-agent entry.
- 00:25 First dry run: auth OK (throwaway keypair generated,
  0x3e46a578a6b77ddf43a4385f4910b80dcbde5684), then
  `TypeError: Request.add_header() missing 1 required positional argument:
  'val'` on the first authenticated call. Cause: `aiprove.py` line 55
  passed `"Authorization: Bearer " + token` as a single argument. Fixed
  to two arguments.
- 00:26 Second dry run: exit 0 — 9 predictions computed from live data
  (btc-tomorrow 'no 0.68', forecast-btc-7d 'no 0.70', spy '751.71',
  forecast-eth-24h 'no 0.70', nvda-3d '157.63', signal 'short', gold
  '353.42', pons top-5, bug-hunt), 12 skips with reasons. Two fixes from
  this run: the pons top-5 contained 'doggg' twice (two distinct
  contracts share the symbol; the grader matches on symbol) — changed to
  fetch top 10 and dedupe by symbol; and the bug-hunt JSON now uses
  ensure_ascii=False so the emoji is sent raw.
- 00:27 Live run 1 (same throwaway identity, handle
  `auto-test-throwaway`): entered 17/21, submitted 6, all
  `provenance_ok`, exit 0. Four enters failed HTTP 409 "already entered"
  (btc-tomorrow, eth-pnl-fixed, top5-pons-24h, forecast-eth-24h): each
  first POST had landed while its response was lost, and the retry hit
  the duplicate guard — and the agent wrongly treated that as fatal and
  skipped those bounties' submits. Also learned the submit response is
  flat `{id, bountySlug, prediction, status: "provenance_ok"}`, not
  nested under `submission`.
- 00:28 Probed the API to design the fix: `GET /api/me/submissions`
  returns the flat shape; a deliberate re-submit to forecast-btc-7d
  SUCCEEDED with a new id (c1af8423-...) — the API allows duplicate
  submits, so retries must be careful. Fixed `agent.py`: HTTP 409 on
  enter counts as entered; the run fetches its own submissions first and
  skips re-submits (idempotent re-runs); submit logging reads the flat
  id/status.
- 00:29 Live run 2: entered 21/21, submitted 9 (6 already submitted +
  btc-tomorrow 027b41e4, top5-pons-24h 7e07deda, forecast-eth-24h
  02594a5f, all provenance_ok), skipped 12, exit 0. Full log in
  `run-log.md`.
- 00:30 Log review found two more real bugs. (a) The curl fallback
  ignored HTTP status: run 2's `fastest-primes (entry id ?)` line was
  really a 409 returned through curl and misread as success. Fixed in
  `aiprove.py` (and the same fix in the sample-agent entry's
  `_http_curl`): curl now appends `-w %{http_code}` and raises on
  >=400. (b) Run 1's signal-eth submit double-landed (874d2634 + fdc8976b)
  via a retried POST. Fixed with verify-after-failure in
  `submit_prediction`: on POST failure it re-checks /api/me/submissions
  and reuses the landed submission instead of re-submitting.
- 00:30 Verified both fixes with targeted tests (throwaway identity):
  curl 200 returns 22 bounties; curl POST enter on an already-entered
  bounty raises HTTP 409; a simulated lost submit response recovers the
  existing submission (3dd68737) with no new submission created (2
  before, 2 after). Same 200/404 checks passed for the sample-agent
  entry's curl fallback.
- 00:31 Wrote `README.md`, `run-log.md`, this transcript. Deleted the
  throwaway keypair.json from the repo directory (gitignored, but a test
  key must not linger next to a submission). Committed the repo.
