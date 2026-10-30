# Films the real game for the promo in this window and keeps a log.
# Usage: powershell -File promo\run_capture.ps1 [take names]
# Watch: "--- name" when a take starts, "TAKE name: N frames, S s, F fps" when it ends. About 4 minutes for all.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$log = Join-Path $here 'work\capture.log'
New-Item -ItemType Directory -Force (Join-Path $here 'work') | Out-Null
Remove-Item (Join-Path $here 'work\capture.done') -ErrorAction SilentlyContinue
$env:PYTHONIOENCODING = 'utf-8'
Write-Host 'BOMBERSYS promo: filming the game, about 4 minutes.' -ForegroundColor Cyan
Write-Host "Log: $log"
$py = Join-Path $root 'backend\.venv\Scripts\python.exe'
cmd /c "`"$py`" -u `"$here\capture.py`" $args 2>&1" | Tee-Object -FilePath $log
"EXIT=$LASTEXITCODE" | Tee-Object -FilePath $log -Append
Set-Content -Path (Join-Path $here 'work\capture.done') -Value 'done'
Write-Host 'Done. The window closes in 8 seconds.'
Start-Sleep -Seconds 8
