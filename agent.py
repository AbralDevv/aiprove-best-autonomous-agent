#!/usr/bin/env python3
"""Best fully-autonomous AIProve agent — no human in the loop.

Reads aiprove.fun/skill.md, signs in with its own keypair, and enters and
completes as many open bounties as it can on its own:

  1. Fetch GET /skill.md and confirm the auth flow is described there.
  2. Load or generate the agent's own keypair (keypair.json, mode 0600).
  3. Authenticate: challenge -> EIP-191 personal_sign -> verify.
  4. List open bounties and enter ALL of them (free).
  5. Complete every bounty it can via the API:
       - Brier forecasts (BTC/ETH, 24h/7d) from live CoinGecko momentum
       - point forecasts (SPY/GLD/NVDA) from live Yahoo closes + drift
       - long/short ETH call from the 24h trend
       - top-5 pons tokens from the live launch feed
       - bug-hunt-utils from four verified bug reports
     Repo / link / referral / code-task bounties are skipped with the reason
     logged — the agent never fakes a submission it cannot genuinely make.
  6. Print a summary: entered / submitted / skipped counts.

Dependencies: Python 3.10+ standard library only (plus curl as a fallback
transport for large API responses — see aiprove.py). Signing is the vendored
pure-Python secp256k1 + Keccak-256 implementation in signing.py.

Usage:
  python3 agent.py [--handle NAME] [--log-file run.log] [--dry-run]

  --dry-run computes every prediction but submits nothing (still enters
            nothing either — use it to check the forecast logic).
  --log-file writes the same timestamped lines printed to stdout to a file.

Environment:
  AIPROVE_API     API base URL (default https://aiprove.fun)
  AIPROVE_HANDLE  agent handle (default IonDaemon)
  AIPROVE_KEYFILE keypair path (default ./keypair.json)
"""
import argparse
import datetime
import os
import sys

from aiprove import ApiError, Client
from handlers import handle
from keys import load_or_create_keypair

API = os.environ.get("AIPROVE_API", "https://aiprove.fun")
HANDLE = os.environ.get("AIPROVE_HANDLE", "IonDaemon")
HERE = os.path.dirname(os.path.abspath(__file__))
KEYFILE = os.environ.get("AIPROVE_KEYFILE", os.path.join(HERE, "keypair.json"))


class Logger:
    def __init__(self, logfile=None):
        self.f = open(logfile, "a") if logfile else None

    def __call__(self, step, msg):
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
        line = f"{ts} [{step}] {msg}"
        print(line, flush=True)
        if self.f:
            self.f.write(line + "\n")
            self.f.flush()

    def close(self):
        if self.f:
            self.f.close()


def main():
    ap = argparse.ArgumentParser(description="Fully autonomous AIProve agent.")
    ap.add_argument("--handle", default=HANDLE)
    ap.add_argument("--log-file", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="compute predictions but enter/submit nothing")
    args = ap.parse_args()

    log = Logger(args.log_file)
    client = Client(API, log=log)
    entered, submitted, skipped = [], [], []

    try:
        # 1. Read skill.md — the agent's instructions, fetched live.
        skill = client.read_skill()
        log("skill.md", f"fetched {len(skill)} chars from {API}/skill.md; auth flow confirmed")

        # 2. Identity: the agent's own keypair.
        priv, addr, created = load_or_create_keypair(KEYFILE)
        log("keypair", f"{'generated new' if created else 'loaded existing'} keypair {addr}"
            + (" (saved mode 0600)" if created else f" from {KEYFILE}"))

        # 3. Authenticate.
        expires = client.authenticate(priv, addr)
        log("auth", f"session token received, expiresAt {expires}")

        # 4. List open bounties, and check what this identity already did
        # (makes re-runs idempotent: never enter twice, never submit twice).
        bounties = client.list_open_bounties()
        log("list", f"{len(bounties)} open bounties")
        already_submitted = {}
        try:
            mine = client.http("GET", "/api/me/submissions")
            for s in mine.get("submissions", []):
                already_submitted.setdefault(s["bountySlug"], s["id"])
            if already_submitted:
                log("list", f"already submitted to {len(already_submitted)}: "
                    f"{sorted(already_submitted)}")
        except ApiError as e:
            log("list", f"could not fetch own submissions ({e}); proceeding fresh")

        # 5. Enter all, then complete what can be completed.
        for b in bounties:
            slug = b["slug"]
            if args.dry_run:
                log("enter", f"[dry-run] would enter {slug}")
            else:
                try:
                    entry_id = client.enter(slug, args.handle)
                    entered.append(slug)
                    log("enter", f"entered {slug} (entry id {entry_id})")
                except ApiError as e:
                    if "already entered" in str(e):
                        # Either a previous run entered it, or this run's
                        # first attempt landed while its response was lost
                        # and the retry hit the duplicate guard. Either
                        # way the entry exists — proceed to the submit step.
                        entered.append(slug)
                        log("enter", f"already entered {slug} (409, treating as entered)")
                    else:
                        log("enter", f"FAILED to enter {slug}: {e}")
                        continue
            if slug in already_submitted and not args.dry_run:
                submitted.append(slug)
                log("submit", f"already submitted to {slug} "
                    f"(submission id {already_submitted[slug]}), skipping re-submit")
                continue
            kind, *rest = handle(b)
            if kind == "submit":
                pred, why = rest
                log("predict", f"{slug}: {pred!r} — {why}")
                if args.dry_run:
                    log("submit", f"[dry-run] would submit to {slug}")
                    submitted.append(slug)
                    continue
                try:
                    res = client.submit_prediction(slug, pred, args.handle)
                    sub_id = res.get("id") or "?"
                    submitted.append(slug)
                    log("submit", f"submitted to {slug} (submission id {sub_id}, "
                        f"status {res.get('status', '?')})")
                except ApiError as e:
                    log("submit", f"FAILED to submit to {slug}: {e}")
            else:
                skipped.append(slug)
                log("skip", f"{slug}: {rest[0]}")

        # 6. Summary.
        log("done", f"entered {len(entered)}/{len(bounties)}, "
            f"submitted {len(submitted)}, skipped {len(skipped)}")
        print(f"\nAUTONOMOUS RUN COMPLETE: entered {len(entered)}, "
              f"submitted {len(submitted)} {submitted}, skipped {len(skipped)}")
        return 0
    except Exception as e:  # noqa: BLE001 - top level: one clear failure line
        log("FAILED", str(e))
        return 1
    finally:
        log.close()


if __name__ == "__main__":
    sys.exit(main())
