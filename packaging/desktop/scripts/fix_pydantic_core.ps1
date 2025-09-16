$ErrorActionPreference = 'Stop'
$wheelDir = "d:\\Mituanapp2\\packaging\\desktop\\vendor\\wheels"
$wheel = Join-Path $wheelDir "pydantic_core-2.33.2-cp311-cp311-win_amd64.whl"
$dest = Join-Path $wheelDir "pyd_core_311"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Expand-Archive -Path $wheel -DestinationPath $dest -Force
$srcCore = Join-Path $dest "pydantic_core"
$targetCore = "d:\\Mituanapp2\\packaging\\desktop\\vendor\\python\\site\\pydantic_core"
Copy-Item -Recurse -Force (Join-Path $srcCore "*") $targetCore
$oldPyd = Join-Path $targetCore "_pydantic_core.cp313-win_amd64.pyd"
if (Test-Path $oldPyd) { Remove-Item $oldPyd -Force }
Write-Output " fixed pydantic_core for cp311"

