using ServiceStack.Auth;
using ACorpBlazor.Data;

[assembly: HostingStartup(typeof(ACorpBlazor.ConfigureAuth))]

namespace ACorpBlazor;

public class ConfigureAuth : IHostingStartup
{
    public void Configure(IWebHostBuilder builder) => builder
        .ConfigureServices(services =>
        {
            services.AddPlugin(new AuthFeature(IdentityAuth.For<ApplicationUser>(options => {
                options.SessionFactory = () => new CustomUserSession();
                options.CredentialsAuth();
                options.AdminUsersFeature();
            })));
        });
}
