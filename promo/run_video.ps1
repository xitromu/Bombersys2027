# Builds the BOMBERSYS promo video in this window and keeps a log.
# Usage: powershell -File promo\run_video.ps1
# Watch: "VO ..." lines (the announcer's timing), then "PROGRESS n/m (percent)", then "DONE path size".
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $here 'work\make_video.log'
Remove-Item (Join-Path $here 'work\make_video.done') -ErrorAction SilentlyContinue
$env:PYTHONIOENCODING = 'utf-8'
Write-Host 'BOMBERSYS promo: about 5 minutes.' -ForegroundColor Cyan
Write-Host "Log: $log"
cmd /c "python -I -u `"$here\make_video.py`" 2>&1" | Tee-Object -FilePath $log
"EXIT=$LASTEXITCODE" | Tee-Object -FilePath $log -Append
Set-Content -Path (Join-Path $here 'work\make_video.done') -Value 'done'
Write-Host 'Done. The window closes in 8 seconds.'
Start-Sleep -Seconds 8
