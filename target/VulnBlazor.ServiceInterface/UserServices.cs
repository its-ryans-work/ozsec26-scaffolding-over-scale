using ServiceStack;
using ServiceStack.DataAnnotations;
using ServiceStack.OrmLite;
using ACorpBlazor.ServiceModel;

namespace ACorpBlazor.ServiceInterface;

public class UserServices : Service
{
    public async Task<GetUserIdResponse> Any(GetUserId request)
    {
        var offset = Math.Max(0, request.Id - 1);
        var id = await Db.ColumnAsync<string>(
            Db.From<UserRow>().Select(x => x.Id).OrderBy(x => x.Id).Limit(skip: offset, rows: 1));
        return new GetUserIdResponse { UserId = id.FirstOrDefault() };
    }

    public async Task<GetUserInfoResponse> Any(GetUserInfo request)
    {
        var row = await Db.SingleByIdAsync<UserRow>(request.UserId)
            ?? throw HttpError.NotFound("User not found");

        var token = await Db.ScalarAsync<string?>(
            Db.From<UserActivityLog>()
                .Where(x => x.UserId == request.UserId)
                .Select(x => x.LastSeenToken));

        return new GetUserInfoResponse
        {
            UserId = row.Id,
            UserName = row.UserName,
            Email = row.Email,
            EmailConfirmed = row.EmailConfirmed,
            LastSeenToken = token,
            PasswordHash = row.PasswordHash,
            FirstName = row.FirstName,
            LastName = row.LastName,
            DisplayName = row.DisplayName,
            ProfileUrl = row.ProfileUrl,
        };
    }
}

[Alias("AspNetUsers")]
internal class UserRow
{
    [PrimaryKey]
    public string Id { get; set; } = string.Empty;
    public string? UserName { get; set; }
    public string? Email { get; set; }
    public bool EmailConfirmed { get; set; }
    public string? PasswordHash { get; set; }
    public string? FirstName { get; set; }
    public string? LastName { get; set; }
    public string? DisplayName { get; set; }
    public string? ProfileUrl { get; set; }
}
