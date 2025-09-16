$ErrorActionPreference = 'SilentlyContinue'
$ok = $false
for ($i = 0; $i -lt 50 -and -not $ok; $i++) {
  try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/' -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ok = $true }
  } catch {
    # ignore
  }
  Start-Sleep -Milliseconds 500
}
if ($ok) { Write-Output 'API_OK'; exit 0 } else { Write-Output 'API_TIMEOUT'; exit 1 }

