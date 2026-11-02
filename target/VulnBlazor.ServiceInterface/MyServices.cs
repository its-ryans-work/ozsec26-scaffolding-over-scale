using ServiceStack;
using ACorpBlazor.ServiceModel;

namespace ACorpBlazor.ServiceInterface;

public class MyServices : Service
{
    public object Any(Hello request)
    {
        return new HelloResponse { Result = $"Hello, {request.Name}!" };
    }
}