"""Pure-stdlib Ethereum signing: Keccak-256 + secp256k1 ECDSA (RFC 6979).

No third-party deps: no ethers, no eth_account, no cast needed at runtime.
EIP-191 personal_sign: sign keccak("\x19Ethereum Signed Message:\n<len>" + msg).
"""
import hashlib
import hmac as hmac_mod
import secrets

# ---------------------------------------------------------------- Keccak-256
# Keccak-f[1600], rate 1088, suffix 0x01 (original Keccak padding, NOT SHA3).
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
       0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
       0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
       0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
       0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
       0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
       0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
       0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_R = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
      [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_MASK = (1 << 64) - 1


def _rol(x, n):
    return ((x << n) | (x >> (64 - n))) & _MASK if n else x & _MASK


def _keccak_f(state):
    for rnd in range(24):
        # Theta
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
             for x in range(5)]
        d = [c[(x + 4) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]
        # Rho + Pi
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(state[x + 5 * y], _R[x][y])
        # Chi
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
        # Iota
        state[0] ^= _RC[rnd]


def keccak256(data: bytes) -> bytes:
    rate = 136  # bytes (1088 bits)
    state = [0] * 25
    # Absorb full blocks
    off = 0
    while off + rate <= len(data):
        block = data[off:off + rate]
        for i in range(rate // 8):
            state[i] ^= int.from_bytes(block[i * 8:(i + 1) * 8], "little")
        _keccak_f(state)
        off += rate
    # Final block with Keccak pad10*1, suffix 0x01
    tail = bytearray(data[off:])
    tail.append(0x01)
    tail.extend(b"\x00" * (rate - len(tail)))
    tail[rate - 1] |= 0x80
    for i in range(rate // 8):
        state[i] ^= int.from_bytes(bytes(tail[i * 8:(i + 1) * 8]), "little")
    _keccak_f(state)
    out = b"".join(state[i].to_bytes(8, "little") for i in range(4))
    return out[:32]


# ---------------------------------------------------------------- secp256k1
_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _ec_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1) * pow(2 * y1, -1, _P) % _P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, _P) % _P
    x3 = (lam * lam - x1 - x2) % _P
    return (x3, (lam * (x1 - x3) - y1) % _P)


def _ec_mul(k, point=(_GX, _GY)):
    res = None
    add = point
    while k:
        if k & 1:
            res = _ec_add(res, add)
        add = _ec_add(add, add)
        k >>= 1
    return res


def privkey_to_address(priv: bytes) -> str:
    x, y = _ec_mul(int.from_bytes(priv, "big"))
    return "0x" + keccak256(x.to_bytes(32, "big") + y.to_bytes(32, "big"))[-20:].hex()


def _rfc6979_k(priv: bytes, msg_hash: bytes) -> int:
    bx = int.from_bytes(priv, "big").to_bytes(32, "big")
    bh = int.from_bytes(msg_hash, "big")
    bh = (bh % _N).to_bytes(32, "big")
    v = b"\x01" * 32
    k = b"\x00" * 32
    k = hmac_mod.new(k, v + b"\x00" + bx + bh, hashlib.sha256).digest()
    v = hmac_mod.new(k, v, hashlib.sha256).digest()
    k = hmac_mod.new(k, v + b"\x01" + bx + bh, hashlib.sha256).digest()
    v = hmac_mod.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac_mod.new(k, v, hashlib.sha256).digest()
        cand = int.from_bytes(v, "big")
        if 1 <= cand < _N:
            return cand
        k = hmac_mod.new(k, v + b"\x00", hashlib.sha256).digest()
        v = hmac_mod.new(k, v, hashlib.sha256).digest()


def sign_message(priv: bytes, message: str) -> str:
    """EIP-191 personal_sign. Returns 0x-prefixed 65-byte r||s||v (v 27/28)."""
    msg = message.encode()
    prefixed = b"\x19Ethereum Signed Message:\n" + str(len(msg)).encode() + msg
    h = keccak256(prefixed)
    z = int.from_bytes(h, "big") % _N
    d = int.from_bytes(priv, "big")
    while True:
        k = _rfc6979_k(priv, h)
        r_point = _ec_mul(k)
        r = r_point[0] % _N
        if r == 0:
            continue
        s = (pow(k, -1, _N) * (z + r * d)) % _N
        if s == 0:
            continue
        # Low-S normalization (canonical): flip s and v if s > n/2.
        # v toggles between 27 and 28 (NOT v ^= 1: 27^1=26, 28^1=29, both invalid).
        v = 27 + (r_point[1] & 1)
        if s > _N // 2:
            s = _N - s
            v = 28 if v == 27 else 27
        return "0x" + r.to_bytes(32, "big").hex() + s.to_bytes(32, "big").hex() + bytes([v]).hex()


def new_keypair():
    priv = secrets.token_bytes(32)
    return priv, privkey_to_address(priv)
