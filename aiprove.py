"""AIProve API client: auth (challenge -> EIP-191 sign -> verify), list, enter,
submit. Plain HTTP, stdlib urllib first with a curl fallback.

Two transport quirks of https://aiprove.fun, both handled here:
  1. Cloudflare returns HTTP 403 for bare urllib/python user-agents, so every
     request carries a browser User-Agent.
  2. urllib's http.client aborts large responses (the bounties list, ~15KB)
     with IncompleteRead, while curl reads them fine — so a failed urllib
     read falls back to a curl subprocess with identical headers/body.
"""
import json
import subprocess
import time
import urllib.error
import urllib.request

from signing import sign_message

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class ApiError(RuntimeError):
    pass


class Client:
    def __init__(self, api_base, log=None):
        self.api = api_base.rstrip("/")
        self.token = None
        self.address = None
        self._log = log or (lambda *a: None)

    # ------------------------------------------------------------ transport
    def _curl(self, method, path, body):
        cmd = ["curl", "-sS", "-m", "60", "-w", "\n%{http_code}", "-X", method,
               self.api + path,
               "-H", f"User-Agent: {USER_AGENT}",
               "-H", "content-type: application/json"]
        if self.token:
            cmd += ["-H", f"Authorization: Bearer {self.token}"]
        if body is not None:
            cmd += ["--data", json.dumps(body)]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if out.returncode != 0:
            raise ApiError(f"curl {method} {path} failed: {out.stderr.strip()[:300]}")
        # -w appends "\n<status>" after the body; split it off and enforce
        # the status like urllib does (plain -sS would silently return a
        # 409/401 body as if it were a success).
        text, _, code = out.stdout.rpartition("\n")
        try:
            status = int(code.strip())
        except ValueError:
            raise ApiError(f"curl {method} {path}: unparseable status {code!r}")
        if status >= 400:
            raise ApiError(f"{method} {path} -> HTTP {status}: {text[:300]}")
        return text

    def http(self, method, path, body=None, raw=False, retries=2):
        data = json.dumps(body).encode() if body is not None else None
        last_err = None
        for attempt in range(1, retries + 1):
            req = urllib.request.Request(self.api + path, data=data, method=method)
            req.add_header("User-Agent", USER_AGENT)
            req.add_header("content-type", "application/json")
            if self.token:
                req.add_header("Authorization", "Bearer " + self.token)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    text = resp.read().decode()
                return text if raw else json.loads(text)
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:300]
                if e.code >= 500 and attempt < retries:
                    last_err = f"HTTP {e.code}"
                    time.sleep(1 * attempt)
                    continue
                raise ApiError(f"{method} {path} -> HTTP {e.code}: {detail}")
            except Exception as e:  # noqa: BLE001 - IncompleteRead/timeouts/resets: retry
                last_err = f"{type(e).__name__}: {e}"
                if attempt < retries:
                    time.sleep(1 * attempt)
                    continue
        self._log("http", f"urllib failed on {method} {path} ({last_err}); falling back to curl")
        text = self._curl(method, path, body)
        return text if raw else json.loads(text)

    # ------------------------------------------------------------------ API
    def read_skill(self):
        """Fetch skill.md and confirm it describes the auth flow."""
        skill = self.http("GET", "/skill.md", raw=True)
        for marker in ("challenge", "personal_sign", "/api/bounties"):
            if marker not in skill:
                raise ApiError(f"skill.md is missing expected marker {marker!r}")
        return skill

    def authenticate(self, priv, address):
        """Challenge -> EIP-191 personal_sign -> verify -> session token.

        Retries once with a fresh challenge if the server reports the
        challenge is gone (observed occasionally against the live API).
        Returns the token's expiresAt. The token itself is kept in memory
        only and never printed or written to disk.
        """
        self.address = address
        for attempt in (1, 2):
            ch = self.http("GET", f"/api/auth/challenge?address={address}")
            challenge = ch["challenge"]
            nonce = challenge.split("Nonce: ")[1].split("\n")[0] if "Nonce: " in challenge else "?"
            self._log("auth", f"challenge received (nonce {nonce})")
            sig = sign_message(priv, challenge)
            self._log("auth", f"signed challenge (sig {sig[:18]}...{sig[-6:]})")
            try:
                verify = self.http("POST", "/api/auth/verify",
                                   {"address": address, "signature": sig})
            except ApiError as e:
                if "no active challenge" in str(e) and attempt == 1:
                    self._log("auth", "verify: challenge lost server-side, requesting a fresh one")
                    continue
                raise
            token = verify.get("token")
            if not token:
                raise ApiError(f"verify returned no token: {json.dumps(verify)[:300]}")
            self.token = token
            return verify.get("expiresAt")
        raise ApiError("authentication failed after retry")

    def list_open_bounties(self):
        listed = self.http("GET", "/api/bounties?status=open")
        return listed.get("bounties", listed if isinstance(listed, list) else [])

    def enter(self, slug, handle):
        """Enter a bounty (free). Returns the entry id, or '?' if unreported."""
        res = self.http("POST", f"/api/bounties/{slug}/enter", {"handle": handle})
        return res.get("entry", {}).get("id") or res.get("id") or "?"

    def submit_prediction(self, slug, prediction, handle):
        """Submit a prediction bounty. `prediction` is a plain string, the
        format the API grades: Brier "yes 0.72" / "no 0.6", point forecasts
        one number ("749.80"), long/short ("long" / "short"), bug hunts a
        JSON string of {fn, input, expected} reports. Returns the raw
        response dict (submission id / status live in there).

        If the POST fails after its response was lost, the submission may
        still have landed server-side (the API allows duplicate submits, so
        a blind retry would double-submit). On failure this re-checks
        /api/me/submissions and returns the landed submission instead of
        raising, when one exists for the slug."""
        try:
            return self.http("POST", f"/api/bounties/{slug}/submit",
                             {"prediction": prediction, "handle": handle})
        except ApiError as e:
            self._log("submit", f"submit POST failed ({e}); checking whether it landed")
            try:
                mine = self.http("GET", "/api/me/submissions")
            except ApiError:
                raise e
            for s in mine.get("submissions", []):
                if s.get("bountySlug") == slug:
                    self._log("submit", f"submission for {slug} did land "
                        f"(id {s.get('id')}); using it instead of re-submitting")
                    return s
            raise e

    def me(self):
        return self.http("GET", "/api/me")
