# Backend Dockerfile for local development
FROM mcr.microsoft.com/dotnet/sdk:10.0-preview AS build
WORKDIR /src

# Copy solution and project files
COPY SuperSuat.sln ./
COPY src/SuperSuat.Domain/SuperSuat.Domain.csproj src/SuperSuat.Domain/
COPY src/SuperSuat.Application/SuperSuat.Application.csproj src/SuperSuat.Application/
COPY src/SuperSuat.Infrastructure/SuperSuat.Infrastructure.csproj src/SuperSuat.Infrastructure/
COPY src/SuperSuat.Api/SuperSuat.Api.csproj src/SuperSuat.Api/
COPY src/SuperSuat.LocalApi/SuperSuat.LocalApi.csproj src/SuperSuat.LocalApi/

# Restore dependencies
RUN dotnet restore

# Copy source code
COPY . .

# Build
RUN dotnet build -c Release --no-restore

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0-preview AS runtime
WORKDIR /app

# Copy built files
COPY --from=build /src/src/SuperSuat.LocalApi/bin/Release/net10.0/ .

ENV ASPNETCORE_URLS=http://+:5000
ENV ASPNETCORE_ENVIRONMENT=Development

EXPOSE 5000

ENTRYPOINT ["dotnet", "SuperSuat.LocalApi.dll"]
