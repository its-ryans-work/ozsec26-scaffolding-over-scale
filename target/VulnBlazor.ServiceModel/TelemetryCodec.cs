using System.Security.Cryptography;
using System.Text;

namespace ACorpBlazor.ServiceModel;

// Round-trip codec used by the batch telemetry endpoint to package
// activity-log entries during transport. Symmetric so both sides can read
// payloads against the same profile.
public static class TelemetryCodec
{
    public const string DefaultProfile = "Vu1nB1az0r$ecretKey!2026@@@@@@@@";

    private static byte[] ProfileBytes => Encoding.UTF8.GetBytes(DefaultProfile);

    public static string Encode(string plaintext)
    {
        using var aes = Aes.Create();
        aes.Key = ProfileBytes;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;
        aes.GenerateIV();

        using var encryptor = aes.CreateEncryptor();
        var plainBytes = Encoding.UTF8.GetBytes(plaintext);
        var cipherBytes = encryptor.TransformFinalBlock(plainBytes, 0, plainBytes.Length);

        var output = new byte[aes.IV.Length + cipherBytes.Length];
        Buffer.BlockCopy(aes.IV, 0, output, 0, aes.IV.Length);
        Buffer.BlockCopy(cipherBytes, 0, output, aes.IV.Length, cipherBytes.Length);
        return Convert.ToBase64String(output);
    }

    public static string Decode(string ciphertext)
    {
        var allBytes = Convert.FromBase64String(ciphertext);
        if (allBytes.Length < 17)
            throw new CryptographicException("Payload too short");

        var iv = new byte[16];
        var cipherBytes = new byte[allBytes.Length - 16];
        Buffer.BlockCopy(allBytes, 0, iv, 0, 16);
        Buffer.BlockCopy(allBytes, 16, cipherBytes, 0, cipherBytes.Length);

        using var aes = Aes.Create();
        aes.Key = ProfileBytes;
        aes.IV = iv;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;

        using var decryptor = aes.CreateDecryptor();
        var plainBytes = decryptor.TransformFinalBlock(cipherBytes, 0, cipherBytes.Length);
        return Encoding.UTF8.GetString(plainBytes);
    }
}
