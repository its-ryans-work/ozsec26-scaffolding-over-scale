using ServiceStack;
using ServiceStack.Logging;
using ServiceStack.Text;
using ACorpBlazor.ServiceModel;

namespace ACorpBlazor.ServiceInterface;

public class BatchApiService : Service
{
    private static readonly ILog Log = LogManager.GetLogger(typeof(BatchApiService));
    private static readonly TimeSpan EnvelopeWindow = TimeSpan.FromMinutes(5);

    // Every failure in the payload path returns this one string.
    //
    // Distinct errors here are a decryption oracle, not a usability nicety.
    // The payload is AES-CBC with PKCS7, so the padding check runs before the
    // plaintext is looked at. Any response that lets a caller tell "the padding
    // was wrong" apart from "it decrypted but the contents were wrong" leaks one
    // bit per request -- enough to recover plaintext a byte at a time, and to
    // forge ciphertext that decrypts to chosen plaintext (CBC-R), all without
    // ever holding the key.
    //
    // That means it is NOT enough to hide the CryptographicException. A distinct
    // "invalid timestamp", "invalid envelope", a leaked SerializationException,
    // or even "unknown action" each confirm that padding was valid, which is the
    // same bit by another name. They all collapse to one response. Detail goes
    // to the server log, never to the caller.
    private const string Rejected = "Payload rejected";

    public async Task<BatchResponse> Post(BatchRequest request)
    {
        BatchEnvelope envelope;
        try
        {
            var innerJson = TelemetryCodec.Decode(request.Payload);

            envelope = innerJson.FromJson<BatchEnvelope>()
                       ?? throw new FormatException("envelope did not deserialise");

            if (!DateTime.TryParse(envelope.Ts, null,
                    System.Globalization.DateTimeStyles.RoundtripKind, out var ts))
                throw new FormatException("unparseable timestamp");

            if ((DateTime.UtcNow - ts.ToUniversalTime()).Duration() > EnvelopeWindow)
                throw new FormatException("envelope outside accepted window");
        }
        catch (Exception ex)
        {
            // Logged, not returned. The caller gets one indistinguishable answer.
            Log.Warn($"batch payload rejected: {ex.GetType().Name}: {ex.Message}");
            throw HttpError.BadRequest(Rejected);
        }

        try
        {
            object response = request.Action switch
            {
                nameof(GetUserId) => await Gateway.SendAsync(
                    envelope.Data.FromJson<GetUserId>()
                    ?? throw new FormatException("bad GetUserId data")),
                nameof(GetUserInfo) => await Gateway.SendAsync(
                    envelope.Data.FromJson<GetUserInfo>()
                    ?? throw new FormatException("bad GetUserInfo data")),
                // Also uniform: reaching this branch at all proves the payload
                // decrypted and validated, so a distinct message would restore
                // the oracle for anyone sending an unknown action.
                _ => throw new FormatException($"unknown action {request.Action}"),
            };

            return new BatchResponse
            {
                Payload = TelemetryCodec.Encode(response.ToJson()),
            };
        }
        catch (FormatException ex)
        {
            Log.Warn($"batch payload rejected: {ex.Message}");
            throw HttpError.BadRequest(Rejected);
        }
    }
}
