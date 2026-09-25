FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copiar la solución y los proyectos
COPY . .
 
# Publicar la API en modo Release
RUN dotnet publish src/RuleForge.Api/RuleForge.Api.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app/publish .

# Configurar ASP.NET Core para escuchar en el puerto 8080
ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080

ENTRYPOINT ["dotnet", "RuleForge.Api.dll"]
