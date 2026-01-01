FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8002

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY ["ProblemService.csproj", "./"]
RUN dotnet restore "ProblemService.csproj"
COPY . .
RUN dotnet build "ProblemService.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "ProblemService.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Create uploads directory
RUN mkdir -p /app/uploads

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ENV ASPNETCORE_URLS=http://+:8002
ENV SERVICE_PORT=8002

ENTRYPOINT ["dotnet", "ProblemService.dll"]
