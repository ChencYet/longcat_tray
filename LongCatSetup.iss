; LongCat Setup Script
; 需要 Inno Setup 6.x 编译

[Setup]
AppId={{B8A3C9F1-2E4D-4A5B-8C7D-9E0F1A2B3C4D}
AppName=LongCat Usage Monitor
AppVersion=1.0.0
AppPublisher=ChencYet
AppPublisherURL=https://github.com/ChencYet/longcat_tray
AppSupportURL=https://github.com/ChencYet/longcat_tray/issues
AppUpdatesURL=https://github.com/ChencYet/longcat_tray/releases
DefaultDirName={autopf}\LongCatUsage
DefaultGroupName=LongCat Usage Monitor
AllowNoIcons=yes
LicenseFile=
OutputDir=..\installer
OutputBaseFilename=LongCatSetup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\LongCatUsage.exe
UninstallDisplayName=LongCat Usage Monitor
DisableProgramGroupPage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\LongCatUsage.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.example.json"; DestDir: "{app}"; Flags: ignoreversion; DestName: "config.example.json"

[Icons]
Name: "{group}\LongCat Usage Monitor"; Filename: "{app}\LongCatUsage.exe"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LongCat Usage Monitor"; Filename: "{app}\LongCatUsage.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LongCatUsage.exe"; Description: "{cm:LaunchProgram,LongCat Usage Monitor}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  ;;
end;
