# Multi-stage build for .NET 9.0
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8001
ENV ASPNETCORE_URLS=http://+:8001

# Create non-root user
RUN addgroup --system --gid 1001 dotnet
RUN adduser --system --uid 1001 --ingroup dotnet dotnet

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy csproj files and restore dependencies
COPY ["src/Domain/Domain.csproj", "src/Domain/"]
COPY ["src/Application/Application.csproj", "src/Application/"]
COPY ["src/Infrastructure/Infrastructure.csproj", "src/Infrastructure/"]
COPY ["src/Presentation/Presentation.csproj", "src/Presentation/"]
COPY ["MathematicsSolver.sln", "./"]

RUN dotnet restore "MathematicsSolver.sln"

# Copy source code
COPY . .

# Build the application
WORKDIR "/src/src/Presentation"
RUN dotnet build "Presentation.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "Presentation.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app

# Copy published application
COPY --from=publish /app/publish .

# Create logs and uploads directories
RUN mkdir -p /app/logs /app/uploads && chown -R dotnet:dotnet /app/logs /app/uploads

# Switch to non-root user
USER dotnet

ENTRYPOINT ["dotnet", "Presentation.dll"]