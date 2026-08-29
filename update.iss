; ==========================================
; Inno Setup — Апдейтер PDF-бот Аганим v3.1
; Запускается поверх установленной версии.
; Сам находит папку установки (по AppID в реестре).
; ==========================================

#define MyAppName "PDF-бот Аганим"
#ifndef MyAppVersion
  #define MyAppVersion "3.1"
#endif
#define MyAppExeName "pdf_bot.exe"
#define MyDashExeName "dashboard.exe"

[Setup]
; Тот же AppID — для автоопределения папки
AppId={{B5F3A8C2-7E4D-4F9B-A1C3-9E7F8A6B5C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} — Обновление до {#MyAppVersion}
DefaultDirName={pf}\{#MyAppName}
OutputDir=install_build
OutputBaseFilename=PDF-bot-Aganim-update-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
; НЕ создавать деинсталлятор (это апдейтер, не полная установка)
Uninstallable=no
CreateAppDir=no
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableStartupPrompt=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; Только обновляемые файлы (перезапишут старые в папке установки)
Source: "dist\pdf_bot.exe"; DestDir: "{code:GetInstallDir}"; Flags: ignoreversion overwritereadonly
Source: "dist\dashboard.exe"; DestDir: "{code:GetInstallDir}"; Flags: ignoreversion overwritereadonly
Source: "dashboard_v30.py"; DestDir: "{code:GetInstallDir}"; Flags: ignoreversion overwritereadonly

[Code]
var
  InstallDir: String;

// Определяем папку установки по AppID в реестре
function GetInstallDir(Param: String): String;
var
  RegPath: String;
begin
  if InstallDir <> '' then
  begin
    Result := InstallDir;
    Exit;
  end;

  RegPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1';
  // Пробуем HKLM (админ установка)
  if not RegQueryStringValue(HKLM, RegPath, 'InstallLocation', InstallDir) then
    // Пробуем HKCU
    if not RegQueryStringValue(HKCU, RegPath, 'InstallLocation', InstallDir) then
      InstallDir := '';

  if InstallDir = '' then
  begin
    // Если не нашли в реестре — fallback на стандартный путь
    InstallDir := ExpandConstant('{pf}\{#MyAppName}');
    MsgBox('Не удалось автоматически определить папку установки.' #13#10 +
           'Будет использован путь по умолчанию:' #13#10 +
           InstallDir + #13#10 #13#10 +
           'Если программа установлена в другое место — закройте этот апдейтер ' +
           'и обновите файлы вручную.', mbInformation, MB_OK);
  end;

  Result := InstallDir;
end;

// Перед обновлением — останавливаем процессы
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /IM pdf_bot.exe /IM dashboard.exe',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

// После копирования — запускаем бот обратно
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if FileExists(InstallDir + '\pdf_bot.exe') then
      Exec(InstallDir + '\pdf_bot.exe', '', '', SW_SHOWNORMAL,
           ewNoWait, ResultCode);
  end;
end;
