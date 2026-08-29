; ==========================================
; Inno Setup script — PDF-бот Аганим v3.1
; Стандартный Windows-установщик
; ==========================================

#define MyAppName "PDF-бот Аганим"
#ifndef MyAppVersion
  #define MyAppVersion "3.1"
#endif
#define MyAppPublisher "Аганим"
#define MyAppExeName "pdf_bot.exe"
#define MyDashExeName "dashboard.exe"

[Setup]
; Уникальный AppID — НЕ МЕНЯТЬ между версиями (для автообновлений)
AppId={{B5F3A8C2-7E4D-4F9B-A1C3-9E7F8A6B5C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=install_build
OutputBaseFilename=PDF-bot-Aganim-setup-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Значок установщика (используем значок бота)
; SetupIconFile=bot.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "autostart"; Description: "Запускать бот при включении ПК"; GroupDescription: "Дополнительно:"

[Files]
; Основные файлы программы
Source: "dist\pdf_bot.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\dashboard.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dashboard_v30.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "key.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "apps_script.gs"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Ярлыки в меню Пуск
Name: "{group}\PDF-бот Аганим"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Dashboard Аганим"; Filename: "{app}\{#MyDashExeName}"
Name: "{group}\Удалить PDF-бот Аганим"; Filename: "{uninstallexe}"
; Ярлыки на рабочем столе (если выбрано)
Name: "{autodesktop}\PDF-бот Аганим"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\Dashboard Аганим"; Filename: "{app}\{#MyDashExeName}"; Tasks: desktopicon

[Registry]
; Автозапуск через реестр (если выбран)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "PDFBotAganim"; ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Запуск бота после установки (по желанию пользователя)
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить PDF-бот Аганим"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Останавливаем процессы перед удалением
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM pdf_bot.exe /IM dashboard.exe"; \
    Flags: runhidden; RunOnceId: "KillProcesses"

[UninstallDelete]
; Удаляем логи и конфиги
Type: files; Name: "{app}\errors.log"
Type: files; Name: "{app}\config.json"
Type: dirifempty; Name: "{app}"

[Code]
// Перед установкой — останавливаем запущенные процессы
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Убиваем процессы бота и дашборда если запущены
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /IM pdf_bot.exe /IM dashboard.exe',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

// После установки — удаляем старую версию из %LOCALAPPDATA% (миграция)
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  OldDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Старый путь установки v3.0 и ранее
    OldDir := ExpandConstant('{localappdata}\Programs\PDF-bot-Aganim');
    if DirExists(OldDir) then
    begin
      // Переносим config.json если есть
      if FileExists(OldDir + '\config.json') then
        FileCopy(OldDir + '\config.json', ExpandConstant('{app}\config.json'), False);
      // Удаляем старую папку
      DelTree(OldDir, True, True, True);
      // Удаляем старые ярлыки
      DeleteFile(ExpandConstant('{userdesktop}\PDF-bot Aganim.lnk'));
      DeleteFile(ExpandConstant('{userdesktop}\Dashboard Aganim.lnk'));
    end;
  end;
end;
