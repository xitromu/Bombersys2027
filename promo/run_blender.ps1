# Renders the 3D parts of the promo in this window: both heroes (about 3 minutes), then the chrome logo (about 7 minutes).
# Usage: powershell -File promo\run_blender.ps1
# Watch: "PROGRESS n/m" lines; each new frame goes to promo\work\heroes or promo\work\logo.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $here 'work\blender.log'
$blender = 'C:\Blender\blender.exe'
$env:BLENDER_USER_RESOURCES = 'C:\Blender\user'
New-Item -ItemType Directory -Force (Join-Path $here 'work') | Out-Null
Remove-Item (Join-Path $here 'work\blender.done') -ErrorAction SilentlyContinue
Set-Content -Path $log -Value "START $(Get-Date -Format HH:mm:ss)" -Encoding utf8

function Note($line) {
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Run($what, $arguments) {
    Note "=== $what  $(Get-Date -Format HH:mm:ss)"
    & $blender -b --python-exit-code 1 @arguments 2>&1 | ForEach-Object { "$_" } |
        Select-String 'DEVICE|PROGRESS|DONE|FEET|Error|Traceback|line \d' | ForEach-Object { Note $_.Line }
    if ($LASTEXITCODE -ne 0) { Note "FAILED: $what (exit $LASTEXITCODE)" }
}

$heroes = Join-Path $here 'work\heroes'
Run 'Ivan' @('-P', "$here\render_heroes.py", '--', '--tag', 'P', '--look', 'I1', '--size', '720', '--dirs', 'down', '--turn', '32', '--out', $heroes)
Run 'Igor' @('-P', "$here\render_heroes.py", '--', '--tag', 'P', '--look', 'G3', '--size', '720', '--dirs', 'down', '--turn', '-32', '--out', $heroes)
Run 'logo' @('--factory-startup', '-P', "$here\render_logo.py", '--', '--out', "$here\work\logo", '--samples', '48')
Note "FINISH $(Get-Date -Format HH:mm:ss)"
Set-Content -Path (Join-Path $here 'work\blender.done') -Value 'done'
Write-Host 'Done. The window closes in 8 seconds.'
Start-Sleep -Seconds 8
