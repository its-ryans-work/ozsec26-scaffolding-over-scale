using System.Net;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using ServiceStack.Blazor;
using ACorpBlazor.Data;
using ACorpBlazor.Components;
using ACorpBlazor.Components.Account;
using ACorpBlazor.ServiceInterface;

var builder = WebApplication.CreateBuilder(args);

var services = builder.Services;
var config = builder.Configuration;

// Add services to the container.
services.AddRazorComponents()
    .AddInteractiveServerComponents();

services.AddCascadingAuthenticationState();
services.AddScoped<IdentityUserAccessor>();
services.AddScoped<IdentityRedirectManager>();
services.AddScoped<AuthenticationStateProvider, IdentityRevalidatingAuthenticationStateProvider>();

services.AddAuthentication(options =>
    {
        options.DefaultScheme = IdentityConstants.ApplicationScheme;
        options.DefaultSignInScheme = IdentityConstants.ExternalScheme;
    })
    .AddIdentityCookies(options => options.DisableRedirectsForApis());
services.AddDataProtection()
    .PersistKeysToFileSystem(new DirectoryInfo("App_Data"));

services.AddDatabaseDeveloperPageExceptionFilter();

services.AddIdentityCore<ApplicationUser>(options => options.SignIn.RequireConfirmedAccount = true)
    .AddRoles<IdentityRole>()
    .AddEntityFrameworkStores<ApplicationDbContext>()
    .AddSignInManager()
    .AddDefaultTokenProviders();

services.AddSingleton<IEmailSender<ApplicationUser>, IdentityNoOpEmailSender>();
// Uncomment to send emails with SMTP, configure SMTP with "SmtpConfig" in appsettings.json
// services.AddSingleton<IEmailSender<ApplicationUser>, EmailSender>();
// services.AddScoped<IUserClaimsPrincipalFactory<ApplicationUser>, AdditionalUserClaimsPrincipalFactory>();
services.AddScoped<IUserClaimsPrincipalFactory<ApplicationUser>, AdditionalUserClaimsPrincipalFactory>();

var baseUrl = builder.Configuration["ApiBaseUrl"] ??
    (builder.Environment.IsDevelopment() ? "https://localhost:5001" : "http://" + IPAddress.Loopback);
services.AddScoped(c => new HttpClient { BaseAddress = new Uri(baseUrl) });
services.AddBlazorServerIdentityApiClient(baseUrl);
services.AddLocalStorage();

// Register all services
services.AddServiceStack(typeof(MyServices).Assembly);

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseMigrationsEndPoint();
}
else
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();

// Synthetic boot manifest for the WebAssembly client. .NET 10's standalone
// Blazor WASM build no longer emits a separate blazor.boot.json on disk,
// but downstream tooling (and older trainer playbooks) still expect this
// URL to return a JSON list of the .NET assemblies shipped to the browser.
// This middleware MUST run before UseBlazorFrameworkFiles() because that
// terminal middleware claims the entire /_framework/* path space and
// short-circuits the pipeline before routed endpoints can fire.
app.Use(async (context, next) =>
{
    if (Microsoft.AspNetCore.Http.HttpMethods.IsGet(context.Request.Method) &&
        context.Request.Path == "/_framework/blazor.boot.json")
    {
        static string Sri(string path)
        {
            var hash = System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(path));
            return "sha256-" + Convert.ToBase64String(hash);
        }

        var env = context.RequestServices.GetRequiredService<IWebHostEnvironment>();
        var assembly = new Dictionary<string, string>();
        // Folder name on disk stays "VulnBlazor.Client" — only the compiled
        // AssemblyName flips to "ACorpBlazor.Client" via the Client csproj.
        var clientFramework = Path.Combine(env.ContentRootPath, "..", "VulnBlazor.Client",
            "bin", "Debug", "net10.0", "wwwroot", "_framework");
        if (Directory.Exists(clientFramework))
        {
            foreach (var f in Directory.EnumerateFiles(clientFramework, "*.dll"))
            {
                assembly[Path.GetFileName(f)] = Sri(f);
            }
        }
        context.Response.ContentType = "application/json";
        await context.Response.WriteAsJsonAsync(new
        {
            mainAssemblyName = "ACorpBlazor.Client",
            resources = new { assembly }
        });
        return;
    }
    await next();
});

// NOTE: UseBlazorFrameworkFiles() is intentionally NOT called. In .NET 10
// it's a terminal middleware that claims /_framework/* and bombs the
// pipeline with "request reached the end of the pipeline" on every miss
// — including the fingerprinted blazor.web.<hash>.js the server-rendered
// Blazor pages need. MapStaticAssets serves both the server-side
// blazor.web.js and the Client WASM .dll files for us.
app.UseStaticFiles();
app.MapStaticAssets();
app.UseAntiforgery();

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

// Add additional endpoints required by the Identity /Account Razor components.
app.MapAdditionalIdentityEndpoints();

app.UseServiceStack(new AppHost(), options => {
    options.MapEndpoints();
});

BlazorConfig.Set(new()
{
    Services = app.Services,
    JSParseObject = JS.ParseObject,
    IsDevelopment = app.Environment.IsDevelopment(),
    EnableLogging = app.Environment.IsDevelopment(),
    EnableVerboseLogging = app.Environment.IsDevelopment(),
});

app.Run();
