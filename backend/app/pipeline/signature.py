"""Ed25519 signed-QR payloads issued by (simulated) issuing authorities.

QR content = base64url( JSON {"iss": <issuer name>, "kid": <key id>, "claims": {...}, "sig": <base64url sig>} )
The signature covers the canonical JSON of {"iss", "kid", "claims"} (sorted keys, compact separators),
so neither the claims nor the issuer/key binding can be altered without invalidating it.

Public keys live in backend/config/authority_keys/<kid>.pub (PEM, SubjectPublicKeyInfo) with an
optional registry backend/config/authority_keys/issuers.json {kid: {issuer, sourceId, docTypes}}.
Private keys exist ONLY under samples/tools/keys/ and are used by the synthetic data generator.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

KEYS_DIR = Path(__file__).resolve().parents[2] / "config" / "authority_keys"
_KID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(text: str) -> bytes:
    text = text.strip()
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_claims(private_key: Ed25519PrivateKey, iss: str, kid: str, claims: dict) -> str:
    """Create the QR payload string for `claims` (used by the sample generator / simulated issuers)."""
    body = {"iss": iss, "kid": kid, "claims": claims}
    sig = private_key.sign(canonical_json(body))
    return b64u_encode(canonical_json({**body, "sig": b64u_encode(sig)}))


@lru_cache(maxsize=1)
def _issuer_registry() -> dict:
    reg = KEYS_DIR / "issuers.json"
    if reg.exists():
        try:
            return json.loads(reg.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


@lru_cache(maxsize=64)
def load_public_key(kid: str) -> Ed25519PublicKey | None:
    if not _KID_RE.match(kid or ""):
        return None
    path = KEYS_DIR / f"{kid}.pub"
    if not path.exists():
        return None
    key = serialization.load_pem_public_key(path.read_bytes())
    return key if isinstance(key, Ed25519PublicKey) else None


def clear_key_cache() -> None:
    load_public_key.cache_clear()
    _issuer_registry.cache_clear()


def known_keys() -> list[dict]:
    """Public key directory (served by the mock authorities at /mock/keys)."""
    out = []
    reg = _issuer_registry()
    for p in sorted(KEYS_DIR.glob("*.pub")):
        kid = p.stem
        out.append({"kid": kid, "alg": "Ed25519", "publicKeyPem": p.read_text(encoding="ascii"), **reg.get(kid, {})})
    return out


def parse_payload(payload: str) -> dict | None:
    """Decode a QR string into the envelope dict, or None if it is not a VeriSense signed payload."""
    try:
        raw = b64u_decode(payload)
        env = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(env, dict) or not {"iss", "kid", "claims", "sig"} <= env.keys():
        return None
    if not isinstance(env["claims"], dict):
        return None
    return env


def verify_signed_payload(payload: str) -> dict:
    """Verify a QR payload. Returns {valid, issuer, keyId, claims, reason}."""
    env = parse_payload(payload)
    if env is None:
        return {"valid": False, "issuer": None, "keyId": None, "claims": None,
                "reason": "QR content is not a signed issuer payload (unrecognised format)"}
    iss, kid, claims = env["iss"], env["kid"], env["claims"]
    result = {"valid": False, "issuer": iss, "keyId": kid, "claims": claims, "reason": ""}
    key = load_public_key(str(kid))
    if key is None:
        result["reason"] = f"Unknown signing key '{kid}' - issuer not in trusted key directory"
        return result
    registered = _issuer_registry().get(kid, {}).get("issuer")
    if registered and registered != iss:
        result["reason"] = f"Issuer name in QR ('{iss}') does not match the owner of key '{kid}' ('{registered}')"
        return result
    try:
        sig = b64u_decode(str(env["sig"]))
        key.verify(sig, canonical_json({"iss": iss, "kid": kid, "claims": claims}))
    except (InvalidSignature, binascii.Error, ValueError):
        result["reason"] = "Signature verification FAILED - QR claims were altered or not signed by the stated issuer"
        return result
    result["valid"] = True
    result["reason"] = f"Ed25519 signature valid (key {kid})"
    if registered:
        result["sourceId"] = _issuer_registry().get(kid, {}).get("sourceId")
    return result
