"""Keypair management: the agent's own Ethereum identity.

The keypair lives in keypair.json next to the agent (mode 0600). If no file
exists, a fresh keypair is generated at runtime — the agent is born with its
own wallet, no signup, no human step.
"""
import json
import os

from signing import new_keypair, privkey_to_address


def load_or_create_keypair(keyfile):
    """Return (priv_bytes, address). Generates + saves (mode 0600) if missing."""
    if os.path.exists(keyfile):
        kp = json.load(open(keyfile))
        priv = bytes.fromhex(kp["private_key"].removeprefix("0x"))
        addr = kp["address"]
        if privkey_to_address(priv).lower() != addr.lower():
            raise RuntimeError(f"keypair file {keyfile} is inconsistent (address mismatch)")
        return priv, addr, False
    priv, addr = new_keypair()
    with open(keyfile, "w") as f:
        json.dump({"address": addr, "private_key": "0x" + priv.hex()}, f, indent=2)
    os.chmod(keyfile, 0o600)
    return priv, addr, True
