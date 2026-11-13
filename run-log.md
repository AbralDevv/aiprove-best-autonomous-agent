# Live test runs — best-autonomous-agent

Recorded runs of `agent.py` against the real API (`https://aiprove.fun`),
Sat 2026-11-14. The agent ran under a **fresh throwaway keypair generated
at test time** — address `0x3e46a578a6b77ddf43a4385f4910b80dcbde5684`, handle
`auto-test-throwaway`. This is NOT the IonDaemon identity; the throwaway
keypair was deleted after the runs and is not in this repo.

## Final result (run 2, 00:29:02–00:30:09 WIB)

**AUTONOMOUS RUN COMPLETE, exit 0 — entered 21/21 open bounties,
submitted 9, skipped 12.**

| Submitted bounty | Prediction (computed live) | Submission id | Status |
| --- | --- | --- | --- |
| btc-tomorrow | `no 0.68` (BTC $68,586, 24h −4.64%, 7d −9.48%) | 027b41e4-0d41-4b74-9f49-3de8f598864c | provenance_ok |
| forecast-btc-7d | `no 0.70` (momentum −8.06%) | 3dd68737-cf80-42ca-972b-24ad3259c207 | provenance_ok |
| spy-close-1dollar | `751.91` (last $751.62, drift +0.04%) | ab69279d-f2ae-4b71-bfdb-eb312f1e2035 | provenance_ok |
| top5-pons-24h | `A2, doggg, BULL, APESHIT, GANGSTAZ` | 7e07deda-ca14-40e6-898d-ed31a41a4c19 | provenance_ok |
| forecast-eth-24h | `no 0.70` (ETH $1,928.77, 24h −4.10%, 7d −13.67%) | 02594a5f-4b4a-42df-8123-285daf51107c | provenance_ok |
| forecast-nvda-3d | `157.75` (last $161.31, drift −2.21% over 3d) | af208d8e-4b71-4268-a241-3d4c0f655dac | provenance_ok |
| signal-eth-pnl-24h | `short` (ETH 24h −4.15%) | fdc8976b-c913-4aab-97a9-c0d0fa96df40 | provenance_ok |
| forecast-gold-tomorrow | `353.42` (last $355.63, drift −0.62%) | 049dbe45-a019-41da-b7c4-c031dd12d0ca | provenance_ok |
| bug-hunt-utils | 4 verified bug reports (JSON string) | bd405a6c-b94a-412e-aacd-ae1bd605a439 | provenance_ok |

Skipped (12, each with a logged reason): 6 link/content bounties
(PosterJudge), `refer-most-agents`, 3 code tasks (`eth-pnl-fixed`,
`code-golf-expr`, `fastest-primes`), and the 2 repo bounties
(`sample-agent-skillmd`, `best-autonomous-agent` itself).

Known throwaway noise from testing (not agent bugs in the shipped code):
one duplicate `forecast-btc-7d` submission (`c1af8423-...`, created
deliberately by a probe that re-submitted to learn the API's duplicate
behavior) and one duplicate `signal-eth-pnl-24h` submission
(`874d2634-...`, landed by a retried POST in run 1 before the
verify-after-failure fix). Both are on the throwaway identity only.

## Run 2 log (00:29:02–00:30:09 WIB, exit 0)

```text
17:29:05 [http] urllib failed on GET /skill.md (IncompleteRead); falling back to curl
17:29:06 [skill.md] fetched 6722 chars from https://aiprove.fun/skill.md; auth flow confirmed
17:29:06 [keypair] loaded existing keypair 0x3e46a578a6b77ddf43a4385f4910b80dcbde5684
17:29:07 [auth] challenge received (nonce 27caf9dd0511a8b9c6fa094ea8f87a74)
17:29:07 [auth] signed challenge (sig 0xda4319b22f0fd411...7fc61b)
17:29:07 [auth] session token received, expiresAt 1794677348752
17:29:08 [list] 21 open bounties
17:29:09 [list] already submitted to 6: ['bug-hunt-utils', 'forecast-btc-7d', 'forecast-gold-tomorrow', 'forecast-nvda-3d', 'signal-eth-pnl-24h', 'spy-close-1dollar']
17:29:11 [enter] already entered write-article-aiprove (409, treating as entered)
17:29:11 [skip] write-article-aiprove: link/content bounty: needs human-judged creative work posted somewhere
17:29:12 [enter] already entered make-art-aiprove (409, treating as entered)
17:29:12 [skip] make-art-aiprove: link/content bounty: needs human-judged creative work posted somewhere
17:29:13 [enter] already entered make-meme-aiprove (409, treating as entered)
17:29:13 [skip] make-meme-aiprove: link/content bounty: needs human-judged creative work posted somewhere
17:29:14 [enter] already entered refer-most-agents (409, treating as entered)
17:29:14 [skip] refer-most-agents: referral bounty: needs other agents to arrive via a referral link
17:29:15 [enter] already entered post-on-x-aiprove (409, treating as entered)
17:29:15 [skip] post-on-x-aiprove: link/content bounty: needs human-judged creative work posted somewhere
17:29:16 [enter] already entered btc-tomorrow (409, treating as entered)
17:29:17 [predict] btc-tomorrow: 'no 0.68' — BTC $68,586.00, 24h -4.64%, 7d -9.48% -> momentum -6.09% -> no 0.68
17:29:20 [submit] submitted to btc-tomorrow (submission id 027b41e4-0d41-4b74-9f49-3de8f598864c, status provenance_ok)
17:29:20 [enter] already entered eth-pnl-fixed (409, treating as entered)
17:29:20 [skip] eth-pnl-fixed: code task: graded from a repo submission, not API-completable
17:29:21 [enter] already entered aiprove-mascot (409, treating as entered)
17:29:21 [skip] aiprove-mascot: link/content bounty: needs human-judged creative work posted somewhere
17:29:22 [enter] already entered explainer-video-aiprove (409, treating as entered)
17:29:22 [skip] explainer-video-aiprove: link/content bounty: needs human-judged creative work posted somewhere
17:29:23 [enter] already entered sample-agent-skillmd (409, treating as entered)
17:29:23 [skip] sample-agent-skillmd: repo bounty: needs a published GitHub repo + commit (this agent cannot publish one on its own)
17:29:26 [enter] already entered forecast-btc-7d (409, treating as entered)
17:29:26 [submit] already submitted to forecast-btc-7d (submission id 3dd68737-cf80-42ca-972b-24ad3259c207), skipping re-submit
17:29:27 [enter] already entered spy-close-1dollar (409, treating as entered)
17:29:27 [submit] already submitted to spy-close-1dollar (submission id ab69279d-f2ae-4b71-bfdb-eb312f1e2035), skipping re-submit
17:29:30 [enter] already entered top5-pons-24h (409, treating as entered)
17:29:52 [predict] top5-pons-24h: 'A2, doggg, BULL, APESHIT, GANGSTAZ' — top 5 by mcap among last-24h pons launches: A2 $323,983 (6.1h); doggg $323,983 (9.6h); BULL $119,054 (8.3h); APESHIT $48,300 (23.5h); GANGSTAZ $22,935 (0.5h)
17:29:54 [http] urllib failed on POST /api/bounties/top5-pons-24h/submit (RemoteDisconnected); falling back to curl
17:29:55 [submit] submitted to top5-pons-24h (submission id 7e07deda-ca14-40e6-898d-ed31a41a4c19, status provenance_ok)
17:29:56 [enter] already entered forecast-eth-24h (409, treating as entered)
17:29:57 [predict] forecast-eth-24h: 'no 0.70' — ETH $1,928.77, 24h -4.10%, 7d -13.67% -> momentum -6.97% -> no 0.70
17:30:00 [submit] submitted to forecast-eth-24h (submission id 02594a5f-4b4a-42df-8123-285daf51107c, status provenance_ok)
17:30:01 [enter] already entered forecast-nvda-3d (409, treating as entered)
17:30:01 [submit] already submitted to forecast-nvda-3d (submission id af208d8e-4b71-4268-a241-3d4c0f655dac), skipping re-submit
17:30:01 [enter] already entered signal-eth-pnl-24h (409, treating as entered)
17:30:01 [submit] already submitted to signal-eth-pnl-24h (submission id 874d2634-6cc2-48bc-a63d-87eb443a1825), skipping re-submit
17:30:02 [enter] already entered forecast-gold-tomorrow (409, treating as entered)
17:30:02 [submit] already submitted to forecast-gold-tomorrow (submission id 049dbe45-a019-41da-b7c4-c031dd12d0ca), skipping re-submit
17:30:03 [enter] already entered code-golf-expr (409, treating as entered)
17:30:03 [skip] code-golf-expr: code task: graded from a repo submission, not API-completable
17:30:06 [http] urllib failed on POST /api/bounties/fastest-primes/enter (RemoteDisconnected); falling back to curl
17:30:07 [enter] entered fastest-primes (entry id ?)
17:30:07 [skip] fastest-primes: code task: graded from a repo submission, not API-completable
17:30:08 [enter] already entered bug-hunt-utils (409, treating as entered)
17:30:08 [submit] already submitted to bug-hunt-utils (submission id bd405a6c-b94a-412e-aacd-ae1bd605a439), skipping re-submit
17:30:09 [enter] already entered best-autonomous-agent (409, treating as entered)
17:30:09 [skip] best-autonomous-agent: repo bounty: needs a published GitHub repo + commit (this agent cannot publish one on its own)
17:30:09 [done] entered 21/21, submitted 9, skipped 12

AUTONOMOUS RUN COMPLETE: entered 21, submitted 9, skipped 12
agent exit=0
```

(Note: log timestamps are UTC; WIB = UTC+7. The `fastest-primes (entry id ?)`
line is the curl-fallback status bug found in log review and fixed right
after this run — the enter had actually returned 409 through curl, which
the old fallback treated as success. Fixed with `-w %{http_code}` +
status enforcement; see `transcript.md`.)

## Run 1 (00:27:25–00:28:09 WIB, exit 0)

First live run: entered 17/21, submitted 6
(`forecast-btc-7d`, `spy-close-1dollar`, `forecast-nvda-3d`,
`signal-eth-pnl-24h`, `forecast-gold-tomorrow`, `bug-hunt-utils`), all
`provenance_ok`. Four enters failed with HTTP 409 "already entered"
(`btc-tomorrow`, `eth-pnl-fixed`, `top5-pons-24h`, `forecast-eth-24h`) —
each first POST had landed while its response was lost, and the retry hit
the duplicate guard; the agent then wrongly skipped those bounties
entirely. Fixed before run 2 (409 = entered; fetch own submissions first;
idempotent re-runs). Entry ids observed in run 1 include
`d39dc112-...` (write-article), `52f89f67-...` (forecast-btc-7d),
`9216c350-...` (spy-close), `736da119-...` (bug-hunt-utils),
`bf9835a8-...` (best-autonomous-agent).

## Dry run (00:26 WIB, exit 0)

`python3 agent.py --dry-run`: authenticated, computed all 9 predictions
from live data, skipped 12 — no enters, no submits. This run caught the
duplicate-`doggg` issue in the pons top-5 (two distinct contracts share
the symbol), fixed by deduping on symbol before the live runs.
