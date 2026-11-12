; Inno Setup script for Snag on Windows. build-windows.sh passes AppVersion, SourceDir (the PyInstaller
; output folder) and IconFile. Installs per user, so no admin prompt.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{943FC3AB-93E7-47E4-896B-F41DA66FCE45}
AppName=Snag
AppVersion={#AppVersion}
AppVerName=Snag {#AppVersion}
AppPublisher=kinshuk8
AppPublisherURL=https://github.com/kinshuk8/yt-downloader
AppSupportURL=https://github.com/kinshuk8/yt-downloader/issues
DefaultDirName={localappdata}\Programs\Snag
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=Snag-Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\Snag.exe
UninstallDisplayName=Snag
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2

[Icons]
Name: "{autoprograms}\Snag"; Filename: "{app}\Snag.exe"
Name: "{autodesktop}\Snag"; Filename: "{app}\Snag.exe"; Tasks: desktopicon

[Run]
; Snag's window is drawn by Microsoft's WebView2 runtime. It ships with Windows 11 and most Windows 10 PCs;
; install it silently if this PC doesn't have it yet.
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft WebView2…"; Check: NeedsWebView2; Flags: waituntilterminated
Filename: "{app}\Snag.exe"; Description: "Open Snag"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; yt-dlp updates the app downloaded for itself (downloaded videos are never touched).
Type: filesandordirs; Name: "{localappdata}\Snag"

[Code]
const
  WebView2Key = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2(Root: Integer; Key: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(Root, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

function NeedsWebView2: Boolean;
begin
  Result := not (HasWebView2(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}')
    or HasWebView2(HKLM, WebView2Key) or HasWebView2(HKCU, WebView2Key));
end;
