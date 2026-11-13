"""Per-bounty handlers: turn an open bounty into a submission, or a logged skip.

Dispatch is by slug + metric (both come from the live bounty list, so a new
forecast bounty with a known shape is picked up automatically):

  Brier ("Brier score" metric, slug names the asset + horizon):
      "yes 0.68" / "no 0.63" — direction from momentum, probability from the
      size of the move, clamped to [0.55, 0.75] (a confident wrong call costs
      more than a hedged one under Brier scoring).
  Point forecast ("Absolute error, $" metric):
      one number — last close plus damped recent drift.
  Direction ("Realized PnL on your call" metric):
      "long" / "short" from the 24h trend.
  top5-pons-24h: five symbols from the live pons launch feed.
  bug-hunt-utils: four verified bug reports (see BUG_REPORTS).

Everything else is skipped with a reason: repo bounties need a GitHub repo +
commit the agent cannot publish on its own; link/content bounties need
human-judged creative work posted somewhere; refer-most-agents needs other
agents to arrive via a referral link; code-golf / fastest-primes /
eth-pnl-fixed are code tasks graded from a repo submission.
"""
import json

from prices import DataError, get_crypto, get_pons_top5, get_stock, pct_change

# --------------------------------------------------------------------------
# bug-hunt-utils: four reports verified by execution against
# github.com/AIProveRH/aiprove/tree/main/challenges/bug-hunt-utils (utils.js).
# Each one was run through node and confirmed to produce a genuinely wrong
# result; the other six functions were checked and are correct on plain
# inputs (max([]) / max([1,NaN,3]) were rejected: -Infinity / NaN are not
# JSON-expressible, so they cannot be submitted cleanly).
#   factorial(5)          -> 24,   correct 120   (loop runs i<n, drops n)
#   countVowels("AEIOU")  -> 0,    correct 5     (regex misses uppercase)
#   reverse("a\U0001F600b") -> garbled surrogates, correct "b\U0001F600a"
#                              (splits on "" so astral chars break apart)
#   titleCase("don't stop") -> "Don'T Stop", correct "Don't Stop"
#                              (/\b\w/ capitalises after the apostrophe)
# --------------------------------------------------------------------------
BUG_REPORTS = [
    {"fn": "factorial", "input": 5, "expected": 120},
    {"fn": "countVowels", "input": "AEIOU", "expected": 5},
    {"fn": "reverse", "input": "a\U0001F600b", "expected": "b\U0001F600a"},
    {"fn": "titleCase", "input": "don't stop", "expected": "Don't Stop"},
]

CRYPTO_IDS = {"btc": "bitcoin", "eth": "ethereum"}
STOCK_TICKERS = {"spy": "SPY", "gold": "GLD", "nvda": "NVDA"}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ------------------------------------------------------------ Brier (yes/no)
def brier_prediction(asset, horizon_days):
    """Momentum-continuation call. momentum blends the 24h move with the 7d
    move (24h-weighted for a 24h horizon, 7d-weighted for 7d). Each 1pp of
    momentum moves the probability 3pp from 0.5, capped at +/-20pp, then the
    winning side's confidence is clamped to [0.55, 0.75]."""
    data = get_crypto(CRYPTO_IDS[asset])
    chg_24h = data["change_24h_pct"]
    closes = data["closes_7d"]
    if chg_24h is None or len(closes) < 2:
        raise DataError(f"{asset}: CoinGecko returned no 24h change / 7d closes")
    chg_7d = pct_change(closes[0][1], closes[-1][1])
    w7 = 0.7 if horizon_days >= 7 else 0.3
    momentum = (1 - w7) * chg_24h + w7 * chg_7d
    p_up = 0.5 + _clamp(momentum * 0.03, -0.20, 0.20)
    side = "yes" if p_up >= 0.5 else "no"
    conf = _clamp(p_up if side == "yes" else 1 - p_up, 0.55, 0.75)
    explain = (f"{asset.upper()} ${data['price']:,.2f}, 24h {chg_24h:+.2f}%, "
               f"7d {chg_7d:+.2f}% -> momentum {momentum:+.2f}% -> {side} {conf:.2f}")
    return f"{side} {conf:.2f}", explain


# ------------------------------------------------------- point forecast ($)
def point_prediction(asset_key, horizon_days):
    """Last close plus damped drift: the mean of the last 3 daily returns,
    halved (damping), times the horizon in days, clamped to +/-1% per day.
    Weekends are fine — the last close is Friday's and the drift still
    points the right way."""
    ticker = STOCK_TICKERS[asset_key]
    data = get_stock(ticker)
    closes = data["closes"]
    returns = [pct_change(closes[i], closes[i + 1]) for i in range(len(closes) - 1)]
    recent = returns[-3:]
    drift = _clamp(sum(recent) / len(recent) * 0.5 * horizon_days,
                   -1.0 * horizon_days, 1.0 * horizon_days)
    forecast = data["last"] * (1 + drift / 100.0)
    explain = (f"{ticker} last ${data['last']:.2f}, closes "
               f"{[round(c, 2) for c in closes]}, last-3 daily returns "
               f"{[round(r, 2) for r in recent]}% -> drift {drift:+.2f}% "
               f"over {horizon_days}d -> ${forecast:.2f}")
    return f"{forecast:.2f}", explain


# ------------------------------------------------------------ long / short
def direction_prediction(asset):
    """Single directional call from the 24h trend: up -> long, down -> short."""
    data = get_crypto(CRYPTO_IDS[asset])
    chg = data["change_24h_pct"]
    if chg is None:
        raise DataError(f"{asset}: CoinGecko returned no 24h change")
    side = "long" if chg > 0 else "short"
    return side, f"{asset.upper()} ${data['price']:,.2f}, 24h {chg:+.2f}% -> {side}"


# ------------------------------------------------------------ top-5 pons
def pons_prediction():
    # Ask for 10, dedupe by symbol, keep the best 5: two distinct tokens can
    # share a symbol (e.g. two "doggg" contracts), and the grader matches on
    # symbol, so a duplicate would waste a slot.
    ranked = get_pons_top5(n=10)
    seen, picks = set(), []
    for t in ranked:
        if t["symbol"] not in seen:
            seen.add(t["symbol"])
            picks.append(t)
        if len(picks) == 5:
            break
    if len(picks) < 5:
        raise DataError(f"pons: only {len(picks)} distinct symbols in top 10")
    pred = ", ".join(t["symbol"] for t in picks)
    detail = "; ".join(
        f"{t['symbol']} ${t['marketCapUsd']:,.0f} ({t['age_hours']}h)"
        for t in picks)
    return pred, f"top 5 by mcap among last-24h pons launches: {detail}"


# ---------------------------------------------------------------- dispatch
def handle(bounty):
    """Return ("submit", prediction_string, explanation) or
    ("skip", reason). Raises nothing: data failures become skips."""
    slug = bounty["slug"]
    metric = bounty.get("metric", "")

    if slug == "bug-hunt-utils":
        return ("submit", json.dumps(BUG_REPORTS, ensure_ascii=False),
                "4 verified bug reports (factorial, countVowels, reverse, titleCase)")
    if slug == "top5-pons-24h":
        try:
            pred, why = pons_prediction()
            return ("submit", pred, why)
        except DataError as e:
            return ("skip", f"pons data unavailable: {e}")

    if metric == "Brier score":
        asset = "btc" if "btc" in slug else "eth" if "eth" in slug else None
        if asset is None:
            return ("skip", f"unknown asset in Brier slug {slug!r}")
        horizon = 7 if ("7d" in slug or "7-d" in slug) else 1
        try:
            pred, why = brier_prediction(asset, horizon)
            return ("submit", pred, why)
        except DataError as e:
            return ("skip", f"crypto data unavailable: {e}")

    if metric.startswith("Absolute error"):
        key = next((k for k in STOCK_TICKERS if k in slug), None)
        if key is None:
            return ("skip", f"unknown asset in point-forecast slug {slug!r}")
        horizon = 3 if "3d" in slug else 1
        try:
            pred, why = point_prediction(key, horizon)
            return ("submit", pred, why)
        except DataError as e:
            return ("skip", f"stock data unavailable: {e}")

    if metric == "Realized PnL on your call":
        asset = "eth" if "eth" in slug else "btc" if "btc" in slug else None
        if asset is None:
            return ("skip", f"unknown asset in direction slug {slug!r}")
        try:
            pred, why = direction_prediction(asset)
            return ("submit", pred, why)
        except DataError as e:
            return ("skip", f"crypto data unavailable: {e}")

    if metric in ("Bytes, all tests pass", "Latency, correct output",
                  "Net PnL after costs"):
        return ("skip", "code task: graded from a repo submission, not API-completable")
    if slug in ("sample-agent-skillmd", "best-autonomous-agent"):
        return ("skip", "repo bounty: needs a published GitHub repo + commit (this agent cannot publish one on its own)")
    if bounty.get("lane") == "PosterJudge":
        return ("skip", "link/content bounty: needs human-judged creative work posted somewhere")
    if slug == "refer-most-agents":
        return ("skip", "referral bounty: needs other agents to arrive via a referral link")
    return ("skip", f"no handler for metric {metric!r} (lane {bounty.get('lane')})")
