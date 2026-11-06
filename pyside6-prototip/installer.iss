; qaZNot VisCreate kurucusu (Inno Setup 6). Derleme: ISCC.exe installer.iss  (önce dist_qt\qaZNot onedir derlemesi gerekir)
#define AppVer "0.3_061126_var1"
#define AppNum "0.3.0"
#define AppName "qaZNot VisCreate"

[Setup]
AppId={{6E2B3F7A-4C1D-4B8E-9A55-QAZNOT000001}
AppName={#AppName}
AppVersion={#AppVer}
AppVerName={#AppName} {#AppVer}
AppPublisher=qaZNot
DefaultDirName={autopf}\qaZNot
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
OutputDir=..\dist_kurulum
OutputBaseFilename=qaZNot-Kurulum-{#AppVer}
SetupIconFile=setup_icon.ico
WizardImageFile=wizard_big.bmp
WizardSmallImageFile=wizard_small.bmp
UninstallDisplayIcon={app}\qaZNot.exe
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
VersionInfoVersion={#AppNum}.0
VersionInfoProductName={#AppName}
ChangesAssociations=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"
Name: "assoc"; Description: ".qaz belgelerini {#AppName} ile aç (çift tıklama)"

[Files]
Source: "..\dist_qt\qaZNot\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\qaZNot.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\qaZNot.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.qaz"; ValueType: string; ValueData: "qaZNot.Document"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\qaZNot.Document"; ValueType: string; ValueData: "{#AppName} belgesi"; Flags: uninsdeletekey; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\qaZNot.Document\DefaultIcon"; ValueType: string; ValueData: "{app}\qaZNot.exe,0"; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\qaZNot.Document\shell\open\command"; ValueType: string; ValueData: """{app}\qaZNot.exe"" ""%1"""; Tasks: assoc

[Run]
Filename: "{app}\qaZNot.exe"; Description: "{#AppName}'u başlat"; Flags: nowait postinstall skipifsilent
