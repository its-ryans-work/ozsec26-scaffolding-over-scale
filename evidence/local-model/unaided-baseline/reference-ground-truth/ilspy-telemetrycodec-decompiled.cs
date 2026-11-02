using System;
using System.Security.Cryptography;
using System.Text;

namespace ACorpBlazor.ServiceModel;

public static class TelemetryCodec
{
	public const string DefaultProfile = "Vu1nB1az0r$ecretKey!2026@@@@@@@@";

	private static byte[] ProfileBytes => Encoding.UTF8.GetBytes("Vu1nB1az0r$ecretKey!2026@@@@@@@@");

	public static string Encode(string plaintext)
	{
		using Aes aes = Aes.Create();
		aes.Key = ProfileBytes;
		aes.Mode = CipherMode.CBC;
		aes.Padding = PaddingMode.PKCS7;
		aes.GenerateIV();
		using ICryptoTransform cryptoTransform = aes.CreateEncryptor();
		byte[] bytes = Encoding.UTF8.GetBytes(plaintext);
		byte[] array = cryptoTransform.TransformFinalBlock(bytes, 0, bytes.Length);
		byte[] array2 = new byte[aes.IV.Length + array.Length];
		Buffer.BlockCopy(aes.IV, 0, array2, 0, aes.IV.Length);
		Buffer.BlockCopy(array, 0, array2, aes.IV.Length, array.Length);
		return Convert.ToBase64String(array2);
	}

	public static string Decode(string ciphertext)
	{
		byte[] array = Convert.FromBase64String(ciphertext);
		if (array.Length < 17)
		{
			throw new CryptographicException("Payload too short");
		}
		byte[] array2 = new byte[16];
		byte[] array3 = new byte[array.Length - 16];
		Buffer.BlockCopy(array, 0, array2, 0, 16);
		Buffer.BlockCopy(array, 16, array3, 0, array3.Length);
		using Aes aes = Aes.Create();
		aes.Key = ProfileBytes;
		aes.IV = array2;
		aes.Mode = CipherMode.CBC;
		aes.Padding = PaddingMode.PKCS7;
		using ICryptoTransform cryptoTransform = aes.CreateDecryptor();
		byte[] array4 = cryptoTransform.TransformFinalBlock(array3, 0, array3.Length);
		return Encoding.UTF8.GetString(array4);
	}
}
You are not using the latest version of the tool, please update.
Latest version is '10.1.1.8388' (yours is '10.0.1.8346')
