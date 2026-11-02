using ServiceStack;

namespace ACorpBlazor.ServiceModel;

// Passwordless access links. A grant is minted server-side when a user requests a
// sign-in link, packaged with the telemetry profile so the recipient can be identified
// without an active session, and mailed out as an opaque key.
//
// The key is only half of a grant: minting also records the grant id in the issuance
// store, and redemption checks the store. A well-formed key on its own is not a grant.
public static class AccessKeyCodec
{
    public const string Purpose = "acs";

    // Superseded access-key profile, retained so links minted before the 2026 profile
    // rotation can still be read. Not used for new grants.
    public const string LegacyAccessKeyProfile = "4c0rpAcs$LegacyKey!2025#@@@@@@@@";

    // Grants are sealed with the same profile as the telemetry channel so a single
    // rotation covers both.
    public static string Pack(string userId, string grantId, DateTime issuedUtc) =>
        TelemetryCodec.Encode($"{userId}|{grantId}|{issuedUtc:O}|{Purpose}");

    public static bool TryUnpack(string accessKey, out string userId, out string grantId,
        out DateTime issuedUtc)
    {
        userId = grantId = string.Empty;
        issuedUtc = default;
        try
        {
            var parts = TelemetryCodec.Decode(accessKey).Split('|');
            if (parts.Length != 4 || parts[3] != Purpose)
                return false;
            userId = parts[0];
            grantId = parts[1];
            return DateTime.TryParse(parts[2], null,
                System.Globalization.DateTimeStyles.RoundtripKind, out issuedUtc);
        }
        catch
        {
            return false;
        }
    }
}

// Exchanges a passwordless access key for the login identity it was issued to.
[Route("/users/login/accesskey", "GET")]
public class GetUserLoginByAccessKey : IGet, IReturn<GetUserLoginByAccessKeyResponse>
{
    public string AccessKey { get; set; } = string.Empty;
}

public class GetUserLoginByAccessKeyResponse
{
    public string? UserId { get; set; }
    public string? UserName { get; set; }
    public string? DisplayName { get; set; }
    // Echoed back so the caller can correlate the redemption with the issued grant.
    public string? GrantId { get; set; }
    public bool Redeemed { get; set; }
    public ResponseStatus? ResponseStatus { get; set; }
}

// Sets a new password for the user a passwordless access key was issued to.
[Route("/users/password/accesskey", "POST")]
public class SetPasswordByAccessKey : IPost, IReturn<SetPasswordByAccessKeyResponse>
{
    public string AccessKey { get; set; } = string.Empty;
    public string NewPassword { get; set; } = string.Empty;
}

public class SetPasswordByAccessKeyResponse
{
    public string? UserId { get; set; }
    public string? GrantId { get; set; }
    public bool Updated { get; set; }
    public ResponseStatus? ResponseStatus { get; set; }
}
