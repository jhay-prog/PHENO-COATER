Option Explicit

Dim shell, fileSystem, projectFolder, venvFolder, pythonPath, pythonwPath
Dim requirementsPath, setupMarker, entryPoint, setupExitCode, markerFile
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

projectFolder = fileSystem.GetParentFolderName(WScript.ScriptFullName)
venvFolder = fileSystem.BuildPath(projectFolder, ".venv")
pythonPath = fileSystem.BuildPath(venvFolder, "Scripts\python.exe")
pythonwPath = fileSystem.BuildPath(venvFolder, "Scripts\pythonw.exe")
requirementsPath = fileSystem.BuildPath(projectFolder, "requirements.txt")
setupMarker = fileSystem.BuildPath(venvFolder, ".requirements-installed")
entryPoint = fileSystem.BuildPath(projectFolder, "main.py")

If Not fileSystem.FileExists(entryPoint) Or Not fileSystem.FileExists(requirementsPath) Then
    MsgBox "The project files are missing. Download and extract the entire PhenoCoater repository, then run this launcher from the extracted folder.", vbExclamation, "PhenoCoater"
    WScript.Quit 1
End If

If Not fileSystem.FileExists(pythonPath) Then
    On Error Resume Next
    setupExitCode = shell.Run("py -3 -m venv """ & venvFolder & """", 1, True)
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        MsgBox "Python 3 was not found. Install Python 3 with the Python Launcher, then run this file again.", vbExclamation, "PhenoCoater"
        WScript.Quit 1
    End If
    On Error GoTo 0

    If setupExitCode <> 0 Then
        MsgBox "Could not create the Python virtual environment. Check that Python 3 is installed, then try again.", vbExclamation, "PhenoCoater"
        WScript.Quit setupExitCode
    End If
End If

If Not fileSystem.FileExists(pythonwPath) Then
    MsgBox "The Python virtual environment is incomplete. Delete the .venv folder and run this launcher again.", vbExclamation, "PhenoCoater"
    WScript.Quit 1
End If

If Not fileSystem.FileExists(setupMarker) Then
    setupExitCode = shell.Run("""" & pythonPath & """ -m pip install -r """ & requirementsPath & """", 1, True)
    If setupExitCode <> 0 Then
        MsgBox "Could not install the PhenoCoater packages. Check your internet connection and try running this launcher again.", vbExclamation, "PhenoCoater"
        WScript.Quit setupExitCode
    End If

    Set markerFile = fileSystem.CreateTextFile(setupMarker, True)
    markerFile.Close
End If

shell.CurrentDirectory = projectFolder
shell.Run """" & pythonwPath & """ """ & entryPoint & """", 0, False