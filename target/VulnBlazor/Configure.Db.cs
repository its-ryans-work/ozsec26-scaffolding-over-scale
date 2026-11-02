using Microsoft.EntityFrameworkCore;
using ServiceStack.Data;
using ServiceStack.OrmLite;
using ACorpBlazor.Data;
using Microsoft.EntityFrameworkCore.Diagnostics;

[assembly: HostingStartup(typeof(ACorpBlazor.ConfigureDb))]

namespace ACorpBlazor;

public class ConfigureDb : IHostingStartup
{
    public void Configure(IWebHostBuilder builder) => builder
        .ConfigureServices((context, services) => {
            var connectionString = context.Configuration.GetConnectionString("DefaultConnection")
                                   ?? "DataSource=App_Data/app.db;Cache=Shared";
            
            services.AddOrmLite(options => options.UseSqlite(connectionString));

            // $ dotnet ef migrations add CreateIdentitySchema
            // $ dotnet ef database update
            services.AddDbContext<ApplicationDbContext>(options => {
                // The EF migrations live in this host project, whose assembly is named
                // VulnBlazor. nameof(ACorpBlazor) resolves to "ACorpBlazor", which is the
                // ServiceModel assembly (it overrides AssemblyName) and holds no migrations
                // -- so EF found none and the Identity schema was never created.
                options.UseSqlite(connectionString,
                    b => b.MigrationsAssembly(typeof(ConfigureDb).Assembly.GetName().Name));
                options.ConfigureWarnings(w => w.Ignore(RelationalEventId.PendingModelChangesWarning));
            });
            
            // Enable built-in Database Admin UI at /admin-ui/database
            services.AddPlugin(new AdminDatabaseFeature());
        });
}