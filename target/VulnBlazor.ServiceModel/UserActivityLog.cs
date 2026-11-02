using ServiceStack.DataAnnotations;

namespace ACorpBlazor.ServiceModel;

// Per-user activity ledger. Tracks the last-seen token issued at signup so
// the batch endpoint can correlate replayed envelopes back to the account.
public class UserActivityLog
{
    [PrimaryKey]
    public string UserId { get; set; } = string.Empty;

    public string LastSeenToken { get; set; } = string.Empty;
}
