#!/bin/sh
set -eu

sdk=${DOTNET:-dotnet}
case "$sdk" in
    /*) ;;
    */*) sdk="$PWD/$sdk" ;;
esac

scratch=$(mktemp -d "${TMPDIR:-/tmp}/nuget-comparison.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
trap 'exit 1' HUP INT TERM
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
export DOTNET_CLI_HOME="$scratch/cli-home" NUGET_PACKAGES="$scratch/packages"

printf 'SDK .NET %s\n' "$("$sdk" --version)"
for demo in 'Serilog 4.0.0 Serilog' \
    'Microsoft.Extensions.Options 8.0.0 Microsoft.Extensions.Primitives' \
    'Microsoft.Extensions.Logging 8.0.0 Microsoft.Extensions.DependencyInjection.Abstractions'
do
    set -- $demo
    id=$1
    version=$2
    leaf=$3
    project="$scratch/$id"
    mkdir -p "$project"
    cat > "$project/Case.csproj" <<XML
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="$id" Version="[$version]" />
  </ItemGroup>
</Project>
XML
    (
        cd "$project"
        printf '\n## %s %s\n' "$id" "$version"
        printf '$ dotnet restore Case.csproj --source https://api.nuget.org/v3/index.json\n'
        "$sdk" restore Case.csproj --source https://api.nuget.org/v3/index.json
        printf '$ dotnet list Case.csproj package --include-transitive\n'
        "$sdk" list Case.csproj package --include-transitive
        printf '$ dotnet nuget why Case.csproj %s\n' "$leaf"
        "$sdk" nuget why Case.csproj "$leaf"
    )
done
