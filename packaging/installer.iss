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
#define MyIconFile "..\assets\app-icon.ico"

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
SetupIconFile={#MyIconFile}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#ifdef IncludeWebView2Runtime
Source: "..\packaging\redist\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; DestDir: "{tmp}"; Check: NeedsWebView2; Flags: deleteafterinstall
#endif

[InstallDelete]
Type: files; Name: "{autodesktop}\{#MyAppName}.lnk"
Type: files; Name: "{autoprograms}\{#MyAppName}.lnk"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\app-icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\assets\app-icon.ico"; Tasks: desktopicon

[Run]
#ifdef IncludeWebView2Runtime
Filename: "{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Parameters: "/silent /install"; StatusMsg: "正在安装 Microsoft Edge WebView2 Runtime..."; Check: NeedsWebView2; Flags: waituntilterminated
#else
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "正在安装 Microsoft Edge WebView2 Runtime..."; Check: NeedsWebView2; Flags: waituntilterminated
#endif
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function WebView2RuntimeExists(): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
end;

function NeedsWebView2(): Boolean;
begin
  Result := not WebView2RuntimeExists();
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  DownloadPage: Integer;
begin
  Result := '';
  if not NeedsWebView2() then
    Exit;

  #ifdef IncludeWebView2Runtime
  MsgBox(
    '当前电脑未检测到 Microsoft Edge WebView2 Runtime。' + #13#10 + #13#10 +
    '安装程序已内置 WebView2 Runtime 安装器，接下来会自动安装。',
    mbInformation,
    MB_OK
  );
  Exit;
  #endif

  DownloadPage := MsgBox(
    '当前电脑未检测到 Microsoft Edge WebView2 Runtime。' + #13#10 + #13#10 +
    '本软件的桌面窗口需要 WebView2 才能显示界面。安装程序可以联网下载并静默安装 WebView2。' + #13#10 + #13#10 +
    '是否现在下载安装？',
    mbConfirmation,
    MB_YESNO
  );

  if DownloadPage = IDYES then
  begin
    try
      DownloadTemporaryFile(
        'https://go.microsoft.com/fwlink/p/?LinkId=2124703',
        'MicrosoftEdgeWebview2Setup.exe',
        '',
        @OnDownloadProgress
      );
    except
      Result :=
        'WebView2 Runtime 下载失败。请联网后重试，或手动安装：' + #13#10 +
        'https://developer.microsoft.com/microsoft-edge/webview2/';
    end;
  end
  else
  begin
    Result :=
      '安装已取消。请先安装 Microsoft Edge WebView2 Runtime 后再安装本软件。' + #13#10 +
      '下载地址：https://developer.microsoft.com/microsoft-edge/webview2/';
  end;
end;
