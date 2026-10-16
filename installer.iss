; Bad Word Beep — Created by Intzevidis7
; GitHub: https://github.com/Intzevidis7
#define MyAppName "Bad Word Beep"
#define MyAppVersion "0.4.0"

[Setup]
AppId={{BFF6E520-69C9-4986-85EE-7D00F111C69D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Intzevidis7
AppPublisherURL=https://github.com/Intzevidis7
DefaultDirName={localappdata}\BadWordBeep
SetupIconFile=app.ico
DefaultGroupName={#MyAppName}
OutputDir=release
OutputBaseFilename=BadWordBeep-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\BadWordBeep.exe

[Files]
Source: "dist\BadWordBeep\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Bad Word Beep"; Filename: "{app}\BadWordBeep.exe"
Name: "{autodesktop}\Bad Word Beep"; Filename: "{app}\BadWordBeep.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\BadWordBeep-Models.exe"; Description: "Download Greek and English Vosk models (internet required; several GB of free disk space recommended)"; Flags: postinstall skipifsilent
Filename: "{app}\BadWordBeep.exe"; Description: "Open Bad Word Beep"; Flags: postinstall nowait skipifsilent unchecked
