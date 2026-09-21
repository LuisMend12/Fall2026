# Creates a Desktop shortcut for Study Ledger.
# Run once, then right-click the app (while running, or the shortcut itself
# on newer Windows builds) and choose "Pin to taskbar".
$WshShell = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Study Ledger.lnk"
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "C:\Python314\pythonw.exe"
$shortcut.Arguments = '"' + (Join-Path $PSScriptRoot "frontend\study_tracker.py") + '"'
$shortcut.WorkingDirectory = Join-Path $PSScriptRoot "frontend"
$shortcut.IconLocation = "C:\Python314\pythonw.exe,0"
$shortcut.Description = "Study Ledger - study time tracker"
$shortcut.Save()
Write-Host "Shortcut created at $shortcutPath"
