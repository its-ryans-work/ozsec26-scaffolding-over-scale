using ServiceStack;

namespace ACorpBlazor.ServiceModel;

// Batch dispatch endpoint. Clients pack a single inner DTO into Payload
// (encoded with TelemetryCodec) and tag it with Action so the server can
// route it without N round-trips. Ts pins the envelope to a recent window
// to reject stale retries.
[Route("/api/batch", "POST")]
public class BatchRequest : IPost, IReturn<BatchResponse>
{
    public string Action { get; set; } = string.Empty;
    public string Payload { get; set; } = string.Empty;
}

public class BatchResponse
{
    public string Payload { get; set; } = string.Empty;
}

public class BatchEnvelope
{
    public string Ts { get; set; } = string.Empty;
    public string Data { get; set; } = string.Empty;
}
