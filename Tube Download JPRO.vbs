Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run chr(34) & ".\.venv\Scripts\pythonw.exe" & chr(34) & " main.py", 0
Set WshShell = Nothing
