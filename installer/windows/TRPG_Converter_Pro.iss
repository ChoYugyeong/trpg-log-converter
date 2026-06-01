; ==========================================================================
;  TRPG Log Converter Pro - Inno Setup Script
;
;  Compile with Inno Setup 6 (https://jrsoftware.org/isdl.php):
;      ISCC.exe installer\windows\TRPG_Converter_Pro.iss
;
;  Produces dist\installer\TRPG_Converter_Pro_Setup_<version>.exe.
;
;  Why Inno Setup over MSI: Inno is single-file, no admin install service
;  required, scriptable, free, and used by widely-distributed apps (Audacity,
;  Notepad++, OBS).
; ==========================================================================

#define AppName "TRPG Log Converter Pro"
#define AppShortName "TRPG_Converter_Pro"
#define AppPublisher "TRPG Tools"
#define AppURL "https://github.com/ChoYugyeong/trpg-log-converter-pro"

; Version is injected by the build script via ISCC /D switch.
; Default to "0.0.0" so a manual ISCC invocation still works.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{B9D3F6C4-7E2E-4F7E-9BCD-6E0E8E4F2B9A}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; Install to Program Files\TRPG_Converter_Pro. {autopf} resolves to
; Program Files (64-bit) when the bootstrapper is 64-bit (default).
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
UninstallDisplayIcon={app}\{#AppShortName}.exe

; 64-bit installer
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Output
OutputDir=..\..\dist\installer
OutputBaseFilename=TRPG_Converter_Pro_Setup_{#AppVersion}
SetupIconFile=..\..\resources\icon.ico

; Use LZMA/Ultra for ~30% smaller installer.
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; UI polish
WizardStyle=modern
WizardSizePercent=110

; Allow installing without admin (per-user) by default. Users with admin
; rights can opt into a machine-wide install via the install wizard.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Minimum supported Windows: Windows 10 (build 17763 = 1809). Matches PySide6 6.6+.
MinVersion=10.0.17763

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Source: PyInstaller --onedir output (dist\TRPG_Converter_Pro\).
; recursesubdirs picks up _internal/, resources/, config.yaml, the exe, etc.
Source: "..\..\dist\TRPG_Converter_Pro\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; Bundled assets that may live outside dist/ (license, README for support).
Source: "..\..\LICENSE";        DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppShortName}.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppShortName}.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; \
    Filename: "{app}\{#AppShortName}.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppShortName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; gui_settings.json은 %APPDATA% 에 별도로 저장돼 있어 install dir 삭제 시 함께
; 사라지지 않는다(의도된 동작). 사용자가 같은 PC 에 재설치하면 설정 유지.
;
; 다만 install dir 안에 캐시 / build 부산물이 생길 수 있으므로 정리.
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\logs"

[Code]
// Show a confirmation that user data outside install dir won't be deleted.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MsgBox(
      'TRPG Log Converter Pro 가 제거되었습니다.' #13#10#13#10
      '사용자 설정/로그/이력은 %APPDATA%\TRPG_Converter_Pro 에 보존됩니다.' #13#10
      '완전히 제거하려면 해당 폴더를 직접 삭제하세요.',
      mbInformation, MB_OK);
  end;
end;
