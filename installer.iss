; ============================================================================
;  Spektranaliz EEG Pro - Inno Setup o'rnatuvchi (setup.exe) skripti
;  Mualliflik: Murodov Elchin O'ktamovich
;
;  Bu skript dist/Spektranaliz EEG Pro/ papkasidagi yig'ilgan dasturni yagona
;  "Spektranaliz-EEG-Pro-Setup.exe" o'rnatuvchi faylga joylaydi.
;
;  Kompilyatsiya:
;    1) Inno Setup o'rnating: https://jrsoftware.org/isdl.php
;    2) Ushbu faylni Inno Setup Compiler'da oching va "Compile" bosing,
;       yoki buyruq qatorida:  ISCC.exe installer.iss
; ============================================================================

#define MyAppName "Spektranaliz EEG Pro"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Murodov Elchin O'ktamovich"
#define MyAppExeName "Spektranaliz EEG Pro.exe"
#define MyBuildDir "dist\Spektranaliz EEG Pro"

[Setup]
AppId={{A7E1D4C2-9B6F-4E3A-8D21-EEG2025SPEKTRPRO}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Spektranaliz-EEG-Pro-Setup
OutputDir=installer
SetupIconFile=spektranaliz-eeg-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "uzbek"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Ish stolida yorliq yaratish"; GroupDescription: "Qo'shimcha yorliqlar:"; Flags: checkedonce

[Files]
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "spektranaliz-eeg-icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\spektranaliz-eeg-icon.ico"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} dasturini o'chirish"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\spektranaliz-eeg-icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} dasturini ishga tushirish"; Flags: nowait postinstall skipifsilent
