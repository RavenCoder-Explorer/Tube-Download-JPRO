$wsDir = "E:\Promgrams\Tube Download JPRO"
$exePath = "$wsDir\dist\TubeDownloadJPRO\TubeDownloadJPRO.exe"
$iconPath = "$wsDir\assets\app_icon.ico"

# Ensure app_icon.ico exists
if (-not (Test-Path $iconPath)) {
    Copy-Item "$wsDir\assets\icon.ico" $iconPath -Force
}

# If compiled exe exists, point shortcuts to it; otherwise pythonw
$targetPath = if (Test-Path $exePath) { $exePath } else { "$wsDir\.venv\Scripts\pythonw.exe" }
$targetArgs = if (Test-Path $exePath) { "" } else { "main.py" }

$WshShell = New-Object -comObject WScript.Shell

# 1. Shortcut in the application folder
$Shortcut = $WshShell.CreateShortcut("$wsDir\Tube Download JPRO.lnk")
$Shortcut.TargetPath = $targetPath
$Shortcut.Arguments = $targetArgs
$Shortcut.WorkingDirectory = if (Test-Path $exePath) { "$wsDir\dist\TubeDownloadJPRO" } else { "$wsDir" }
$Shortcut.IconLocation = "$iconPath,0"
$Shortcut.Description = "Tube Download JPRO"
$Shortcut.Save()

# 2. Shortcut on the Windows Desktop
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WshShell.CreateShortcut("$Desktop\Tube Download JPRO.lnk")
$DesktopShortcut.TargetPath = $targetPath
$DesktopShortcut.Arguments = $targetArgs
$DesktopShortcut.WorkingDirectory = if (Test-Path $exePath) { "$wsDir\dist\TubeDownloadJPRO" } else { "$wsDir" }
$DesktopShortcut.IconLocation = "$iconPath,0"
$DesktopShortcut.Description = "Tube Download JPRO"
$DesktopShortcut.Save()

# 3. Notify Windows Shell to refresh icon cache immediately
$code = @'
using System;
using System.Runtime.InteropServices;
public class ShellHelper {
    [DllImport("shell32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
'@
Add-Type -TypeDefinition $code -Language CSharp -ErrorAction SilentlyContinue
[ShellHelper]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)

Write-Host "Desktop and Folder application shortcuts linked to standalone executable with new 3D icon!"

