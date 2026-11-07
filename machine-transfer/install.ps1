$ErrorActionPreference = 'Stop'

$source = $PSScriptRoot
$claude = Join-Path $env:USERPROFILE '.claude'
$skills = Join-Path $claude 'skills'
$memory = Join-Path $claude 'projects\D--JEFF-JeffCompany-Blender\memory'

New-Item -ItemType Directory -Force $skills, $memory | Out-Null
Copy-Item (Join-Path $source 'skills\*') $skills -Recurse -Force
Copy-Item (Join-Path $source 'memory\*') $memory -Recurse -Force

Write-Host "Installed skills to $skills"
Write-Host "Installed memory to $memory"
Write-Host 'Restart Claude to load them.'
