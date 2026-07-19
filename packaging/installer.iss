#define MyAppName "台股研究室"
#define MyAppExeName "TWStockAnalysis.exe"
#define MyAppVersion GetEnv("TWSTOCK_VERSION")

[Setup]
AppId={{D1247831-4187-4F15-93D6-62D0D8C3A419}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=胖貓貓工作室
LicenseFile=..\LICENSE
DefaultDirName={localappdata}\Programs\TWStockAnalysis
DefaultGroupName={#MyAppName}
OutputDir=..\release
OutputBaseFilename=TWStockAnalysis-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑"; GroupDescription: "其他工作："

[Files]
Source: "..\dist\TWStockAnalysis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "啟動 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataPath := ExpandConstant('{localappdata}\FatCatGameStudio\TWStockAnalysis');
    if DirExists(DataPath) and
       (MsgBox('是否同時刪除本機 cache、log 與 PDF？選「否」會保留使用者資料。',
        mbConfirmation, MB_YESNO) = IDYES) then
      DelTree(DataPath, True, True, True);
  end;
end;
