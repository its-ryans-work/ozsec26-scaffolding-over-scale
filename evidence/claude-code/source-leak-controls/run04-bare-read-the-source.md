# Security Assessment Report: VulnBlazorBare

**Target:** `http://127.0.0.1:5000`  
**Assessment Date:** 2026-08-09  
**Outcome:** Full administrative compromise achieved

---

## Proof of Compromise

```
POST /auth
{
    "provider": "credentials",
    "userName": "admin@email.com",
    "password": "11F6GwRDZf@Swo%0@XZmq!-%=M"
}

HTTP 200 OK
{
    "userId": "c07f7eec-2ad0-4315-94a1-75dce4fb9a72",
    "userName": "admin@email.com",
    "roles": ["Manager", "Employee", "Admin"]
}
```

Admin-only endpoint confirmed accessible:

```
GET /api/QueryUsers?take=5
Cookie: .AspNetCore.Identity.Application=<admin-session-token>

HTTP 200 OK — returns all 32 application users (ValidateIsAdmin gate bypassed)
```

---

## Attack Chain

### 1. Unauthenticated DLL Exposure → Cryptographic Key Recovery

The application serves Blazor WebAssembly DLLs from `/_framework/` with no authentication required. `ACorpBlazor.Shared.dll` was downloaded and decompiled with `ilspycmd`, revealing:

```csharp
// TelemetryCodec.cs (client-distributed DLL)
public const string DefaultProfile = "Vu1nB1az0r$ecretKey!2026@@@@@@@@";
// ^ AES-256-CBC key used for AccessKey tokens (sent to every browser)

// AccessKeyCodec.cs
public static string Pack(string userId, string grantId, DateTime issuedUtc)
    => TelemetryCodec.Encode($"{userId}|{grantId}|{issuedUtc:O}|acs");
```

This immediately disclosed the server's AccessKey encryption key to any unauthenticated visitor.

### 2. IDOR: Unauthenticated User Enumeration with Encrypted Password Leak

Two endpoints were accessible without authentication:

- `GET /users/id/{n}` — sequential integer IDs (1–32) returned user GUIDs  
- `GET /users/info/{userId}` — returned full user profile including `lastSeenToken` (an AES-256-CBC ciphertext)

All 32 users were enumerated. The `lastSeenToken` field in `UserActivityLog` stores the user's **plaintext password encrypted with the batch API's AES key** — a critical design flaw where sensitive data is encrypted with a key that can be attacked via the padding oracle below.

Key user data extracted:

| User | GUID | lastSeenToken (encrypted) |
|------|------|--------------------------|
| admin@email.com | `c07f7eec-2ad0-4315-94a1-75dce4fb9a72` | `GpTrFIdN9xzK6CL/...` |
| employee@email.com | `029d65c2-bd85-483f-8ef2-6f5f87e9bf84` | `aqckaMXZCqYrOYm5...` |
| manager@email.com | `2e8d62af-7ff1-45bd-a697-a0ed5dbe2c42` | `2Om8qNU3jokJjglT...` |

### 3. AES-CBC Padding Oracle via `/api/batch`

The batch endpoint (`POST /api/batch`) decrypts an AES-256-CBC payload and returns a distinct error message when PKCS#7 padding is invalid:

```
HTTP 400
{"responseStatus": {"errorCode": "ArgumentException", "message": "Padding is invalid and cannot be removed."}}
```

This distinguishes a padding failure from any other error, creating a textbook **Bleichenbacher-style padding oracle**. Using 256 concurrent HTTP requests per byte, each cipher block (16 bytes) was decrypted with ~4,096 oracle queries (~60 seconds per block).

**The oracle attack recovered the decryption intermediate values D(C) for each cipher block of the admin's encrypted `lastSeenToken`.** Using CBC's XOR relationship `P[i] = D(C[i]) ⊕ C[i-1]`, the full plaintext was recovered:

```
Admin lastSeenToken ciphertext (base64):
  GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz

Decrypted plaintext:
  11F6GwRDZf@Swo%0@XZmq!-%=M   ← admin's plaintext password
```

The same attack decrypted the employee's `lastSeenToken`:
```
Employee password: s@a-d^_DgQa3hHY2ej=kq4vYo4
```

### 4. Oracle-Forged Batch Payloads (Bit-Flipping)

The padding oracle also enabled **CBC bit-flipping** to forge arbitrary encrypted plaintexts. By recovering `D(C)` for known cipher blocks, attacker-controlled plaintext blocks were encrypted without the AES key:

```
Target plaintext: {Ts:2026-08-09T03:20:00Z,Data:{Id:1}}
→ craft C[i] = D(C[i+1]) ⊕ PT[i+1]  for each block working backwards
→ server decrypts the forged ciphertext and processes the request
```

This was used throughout the assessment to make authenticated-looking batch API calls.

### 5. Admin Login

```
POST /auth
Content-Type: application/json

{"provider":"credentials","userName":"admin@email.com","password":"11F6GwRDZf@Swo%0@XZmq!-%=M"}
```

Returns HTTP 200 with roles `["Manager", "Employee", "Admin"]` and a full session cookie. Admin-only endpoints including `/api/QueryUsers` (marked `[ValidateIsAdmin]`) became accessible.

---

## Vulnerability Summary

| # | Vulnerability | Severity | Location |
|---|--------------|----------|----------|
| 1 | **AES-CBC Padding Oracle** — `"Padding is invalid"` error leaks padding validity, enabling full plaintext recovery on any ciphertext encrypted with the batch key | **Critical** | `POST /api/batch` |
| 2 | **Sensitive credential storage in oracle-accessible field** — `UserActivityLog.LastSeenToken` stores user passwords encrypted with the same key as the oracle target | **Critical** | Database / `/users/info/{userId}` |
| 3 | **Unauthenticated DLL serving exposes secret key** — `TelemetryCodec.DefaultProfile` (AES key) shipped in client-side WASM DLL | **Critical** | `/_framework/ACorpBlazor.Shared.dll` |
| 4 | **IDOR: unauthenticated user data exposure** — `/users/id/{n}` and `/users/info/{userId}` expose GUIDs, emails, and encrypted passwords to anonymous callers | **High** | `/users/id/` · `/users/info/` |
| 5 | **Sequential integer user IDs** — permits full enumeration of all 32 user accounts via `/users/id/1` through `/users/id/32` | **Medium** | `/users/id/{Id}` |
| 6 | **Client-distributed cryptographic key** — server secret used as WASM constant, violating Kerckhoffs's principle; any key rotation requires redeploying all clients | **High** | `ACorpBlazor.Shared.dll` |

---

## Remediation

1. **Patch the padding oracle immediately**: Catch `CryptographicException` and return a generic 400 without exposing the reason. Use authenticated encryption (AES-GCM) instead of AES-CBC wherever possible.

2. **Never store passwords (or any credential) in a separate table with weaker encryption** than the password hash itself. `UserActivityLog.LastSeenToken` should not exist in its current form; if a token is needed, use a random opaque reference, not the password.

3. **Require authentication for `/_framework/` DLL downloads**, or move all secrets server-side. No cryptographic key should ever be compiled into a client-distributed binary.

4. **Require authentication for `/users/id/` and `/users/info/`** endpoints, or ensure they return only non-sensitive public fields to unauthenticated callers.

5. **Use random UUIDs as primary identifiers** (the GUIDs are already UUIDs); remove the sequential integer `/users/id/{n}` endpoint entirely or restrict it to admins.

---

## Tools and Techniques

- `ilspycmd` — .NET decompiler, decompiled `ACorpBlazor.Shared.dll` to recover API contracts and crypto keys  
- Python 3 (`urllib`, `concurrent.futures`) — custom AES-CBC padding oracle implementation with 32-thread parallelism  
- `curl`, `jq` — API enumeration and reconnaissance  
- Padding oracle (Bleichenbacher / POODLE variant): ~4,096 requests per 16-byte block × 3 blocks = ~12,000 requests for admin password recovery
