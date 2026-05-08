#define MyAppName "高校行政AI回复助手"
#ifndef MyAppVersion
#define MyAppVersion "0.1.0"
#endif
#ifndef MyAppPublisher
#define MyAppPublisher "School Admin AI Assistant"
#endif
#ifndef MyOutputBaseFilename
#define MyOutputBaseFilename "SchoolAdminAIAssistant-Setup"
#endif
#define MyAppExeName "SchoolAdminAIAssistant.exe"
#define BuildDir "..\dist\SchoolAdminAIAssistant"

[Setup]
AppId={{A1BA8594-BBB8-42E7-9C4F-FDD42E1DD44A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
DefaultDirName=D:\SchoolAdminAIAssistant
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\installer-output
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
