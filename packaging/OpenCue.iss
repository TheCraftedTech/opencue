; Inno-Setup-Installer fuer OpenCue (Windows 10 / 11, 64 Bit). Voraussetzung: dist\OpenCue\ (packaging\build.ps1).
; Bauen:  powershell -File packaging\build.ps1 -Installer      (oder ISCC.exe packaging\OpenCue.iss)
;
; Ablauf: Willkommen (Logo, Name, Version; hier waehlt man die Sprache - vorbelegt nach der Windows-Sprache, Deutsch/Englisch, wirkt auf Installer UND OpenCue) -> Lizenz (GPL, zum Lesen)
;   -> Programmordner -> Datenordner (Shows, Layouts, Fixtures ...) -> Verknuepfungen (Startmenue, Desktop; die Windows-Suche richtet das Setup immer mit ein) -> Uebersicht
;   (was wird gemacht) -> Installieren -> Fertig (OpenCue starten).
; Ist OpenCue schon installiert, vergleicht das Setup die Versionen und fragt zuerst: Aktualisieren (neuere Version) / Neu installieren (gleiche) / Aeltere Version installieren,
;   Deinstallieren, Abbrechen (Vorgabe = Enter und Esc). Bei Update/Neuinstallation entfallen Programm- und Datenordner (gleicher Ordner, Daten bleiben).
;
; - Version/Firma/Adresse kommen aus app\version.py (-> packaging\version.iss, wird vom Build erzeugt).
; - Die Daten der Benutzer liegen im Datenordner (Standard %LOCALAPPDATA%\OpenCue) und werden bei Update und Neuinstallation nie angefasst; beim Deinstallieren wird gefragt.
; - Eine frische Installation schreibt %LOCALAPPDATA%\OpenCue\config\app_config.json (gewaehlte Sprache, Datenordner als custom_data_path, first_start_done=false: OpenCue oeffnet beim
;   ersten Start die Demo-Show). Eine vorhandene Konfiguration wird nie ueberschrieben.
; - Edge WebView2: Fehlt die Laufzeit, laedt der Installer (nur dabei, Internet erlaubt) den kleinen Microsoft-Bootstrapper und fuehrt ihn aus. Ist er offline, geht die Installation
;   trotzdem weiter und OpenCue zeigt beim Start einen verstaendlichen Hinweis. OpenCue selbst braucht kein Internet.
; - Update aus OpenCue heraus (app\updater.py): das Programm startet NACH dem Beenden "OpenCue-Setup-v<Version>.exe /SILENT /NORESTART /CLOSEAPPLICATIONS"; im stillen Modus startet das
;   Setup OpenCue am Ende wieder (keine Rueckfragen).
; - Automatisierung / Tests: /DATADIR="D:\OpenCue" (Datenordner), /CONFIGDIR="..." (Ort der app_config.json statt %LOCALAPPDATA%\OpenCue\config), /NOLAUNCH=1 (stiller Modus startet
;   OpenCue nicht), /LANG=german (Sprache), dazu die ueblichen /VERYSILENT /DIR="..." /SUPPRESSMSGBOXES /NORESTART. Test-Fassung neben einer echten Installation: ISCC /DAppGuid=<andere GUID>
;   (und /DTestAppVersion=1.0.1 fuer eine andere Versionsnummer).

#include "version.iss"

#ifdef TestAppVersion
  #undef AppVersion
  #define AppVersion TestAppVersion
  #undef AppVersionLabel
  #define AppVersionLabel "v" + TestAppVersion
#endif

#ifndef AppGuid
  #define AppGuid "C2C554E2-CE9C-4C3B-8742-E5E820D30FE4"      ; nie aendern (so erkennt das Setup eine vorhandene Installation); nur Tests bauen mit /DAppGuid=... eine getrennte Fassung
#endif

#ifndef DistDir
  #define DistDir "..\dist\OpenCue"
#endif

[Setup]
AppId={{{#AppGuid}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersionLabel}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppCopyright={#AppCopyright}
VersionInfoVersion={#AppVersionNumeric}
VersionInfoDescription={#AppDescription}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersionNumeric}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersionLabel}
SetupIconFile=OpenCue.ico
WizardImageFile=installer-img\wizard-100.bmp,installer-img\wizard-150.bmp,installer-img\wizard-200.bmp
WizardSmallImageFile=installer-img\small-100.bmp,installer-img\small-150.bmp,installer-img\small-200.bmp
InfoBeforeFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename={#AppName}-Setup-{#AppVersionLabel}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
ShowLanguageDialog=no
LanguageDetectionMethod=uilanguage
SetupMutex=OpenCueSetupMutex
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "installer-img\wizard-100.bmp"; Flags: dontcopy

[InstallDelete]
; Aufraeumen: die Startmenue-Verknuepfungen der ersten Setup-Fassung lagen in einem Unterordner "OpenCue" - jetzt liegt die Verknuepfung direkt im Startmenue
Type: filesandordirs; Name: "{autoprograms}\{#AppName}"

[Icons]
; direkt im Startmenue (nicht in einem Unterordner): die Windows-Suche findet "OpenCue" sofort
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Check: WantStartMenu
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Check: WantDesktop

[Registry]
; "App Paths": macht OpenCue.exe fuer Win+R, die Suche und die Eingabeaufforderung auffindbar - immer, nicht abwaehlbar (wird beim Deinstallieren entfernt)
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{#AppName}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Flags: nowait runasoriginaluser; Check: RelaunchAfterSilent

[Code]
const
  WebView2ClientGuid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2BootstrapperUrl = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';
  HexDigits = '0123456789abcdef';
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#AppGuid}}_is1';
  ThisVersion = '{#AppVersion}';
  ThisLabel = '{#AppVersionLabel}';

var
  DownloadPage: TDownloadWizardPage;
  DataPage: TInputDirWizardPage;
  ShortcutsPage: TWizardPage;
  CbStartMenu, CbDesktop: TNewCheckBox;
  ShortcutsNote: TNewStaticText;
  LangLabel: TNewStaticText;
  LangCombo: TNewComboBox;
  German: Boolean;                  // gewaehlte Sprache (Installer UND OpenCue)
  Existing: Boolean;                // OpenCue ist schon installiert
  ExistingVersion, ExistingUninstall: String;
  Mode: Integer;                    // 0 neu, 1 Update (Setup neuer), 2 Neuinstallation (gleiche Version), 3 aeltere Version
  WebView2Downloaded: Boolean;
  RunListMoved: Boolean;

// ------------------------------------------------------------------------------------------------ Sprache
function GermanUI(): Boolean;
begin
  Result := (GetUILanguage and $3FF) = $07;       // Primaersprache Deutsch (LANG_GERMAN)
end;

function T(const English, German_: String): String;
begin
  if German then
    Result := German_
  else
    Result := English;
end;

// ------------------------------------------------------------------------------------------------ Versionen
function VersionPart(var S: String): Integer;
var
  N: String;
begin
  N := '';
  while (Length(S) > 0) and (S[1] >= '0') and (S[1] <= '9') do begin
    N := N + S[1];
    Delete(S, 1, 1);
  end;
  if (Length(S) > 0) and (S[1] = '.') then
    Delete(S, 1, 1);
  Result := StrToIntDef(N, 0);
end;

// 1 = A ist neuer als B, 0 = gleich, -1 = A ist aelter. Eine Vorabversion (1.1.0-beta) ist aelter als die Endfassung 1.1.0.
function CompareVersions(A, B: String): Integer;
var
  I, X, Y: Integer;
  PreA, PreB: Boolean;
begin
  if (Length(A) > 0) and ((A[1] = 'v') or (A[1] = 'V')) then
    Delete(A, 1, 1);
  if (Length(B) > 0) and ((B[1] = 'v') or (B[1] = 'V')) then
    Delete(B, 1, 1);
  PreA := Pos('-', A) > 0;
  PreB := Pos('-', B) > 0;
  Result := 0;
  for I := 1 to 3 do begin
    X := VersionPart(A);
    Y := VersionPart(B);
    if X > Y then begin
      Result := 1;
      Exit;
    end;
    if X < Y then begin
      Result := -1;
      Exit;
    end;
  end;
  if PreA and (not PreB) then
    Result := -1
  else if PreB and (not PreA) then
    Result := 1;
end;

function InstalledInfo(var Version, Uninstall: String): Boolean;
begin
  Version := '';
  Uninstall := '';
  Result := RegQueryStringValue(HKCU, UninstallKey, 'UninstallString', Uninstall) or RegQueryStringValue(HKLM, UninstallKey, 'UninstallString', Uninstall) or
            RegQueryStringValue(HKLM32, UninstallKey, 'UninstallString', Uninstall);
  if Result then begin
    if not RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', Version) then
      if not RegQueryStringValue(HKLM, UninstallKey, 'DisplayVersion', Version) then
        RegQueryStringValue(HKLM32, UninstallKey, 'DisplayVersion', Version);
  end;
end;

// ------------------------------------------------------------------------------------------------ Pfade und Konfiguration
function ConfigDir(): String;
begin
  Result := ExpandConstant('{param:CONFIGDIR|{localappdata}\OpenCue\config}');
end;

function ConfigFile(): String;
begin
  Result := AddBackslash(ConfigDir()) + 'app_config.json';
end;

function DefaultDataDir(): String;
begin
  Result := ExpandConstant('{localappdata}\OpenCue');
end;

function RelaunchAfterSilent(): Boolean;
begin
  // Update aus OpenCue heraus (stiller Modus): OpenCue am Ende wieder starten
  Result := WizardSilent and (ExpandConstant('{param:NOLAUNCH|0}') <> '1');
end;

function WantStartMenu(): Boolean;
begin
  Result := WizardSilent or CbStartMenu.Checked;
end;

function WantDesktop(): Boolean;
begin
  Result := WizardSilent or CbDesktop.Checked;
end;

function WebView2Installed(): Boolean;
var
  Version: String;
begin
  Result := False;
  // laut Microsoft: Wert "pv" unter EdgeUpdate\Clients (HKLM32 = WOW6432Node auf 64-Bit-Windows, sonst HKCU fuer Installationen nur fuer den Benutzer)
  if RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WebView2ClientGuid, 'pv', Version) then
    Result := (Version <> '') and (Version <> '0.0.0.0');
  if (not Result) and RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\' + WebView2ClientGuid, 'pv', Version) then
    Result := (Version <> '') and (Version <> '0.0.0.0');
end;

// ------------------------------------------------------------------------------------------------ Dialog "schon installiert" (quadratisch wie die Willkommensseite)
function AskExisting(): Integer;
// Rueckgabe: 0 = Abbrechen (Vorgabe, Enter und Esc), 1 = Installieren (Update / Neuinstallation / aeltere Version), 2 = Deinstallieren
var
  Form: TSetupForm;
  Picture: TBitmapImage;
  Title, Versions, Status: TNewStaticText;
  BtnMain, BtnUninstall, BtnCancel: TNewButton;
  X, W: Integer;
begin
  Result := 0;
  Form := CreateCustomForm(544, 314, False, True)       // Groesse in 96-dpi-Einheiten: wird von Inno selbst skaliert;
  try
    Form.Caption := 'OpenCue ' + ThisLabel;
    ExtractTemporaryFile('wizard-100.bmp');
    Picture := TBitmapImage.Create(Form);
    Picture.Parent := Form;
    Picture.SetBounds(0, 0, ScaleX(164), ScaleY(314));
    Picture.Stretch := True;
    Picture.Bitmap.LoadFromFile(ExpandConstant('{tmp}\wizard-100.bmp'));

    X := ScaleX(164 + 22);
    W := Form.ClientWidth - X - ScaleX(22);

    Title := TNewStaticText.Create(Form);
    Title.Parent := Form;
    Title.SetBounds(X, ScaleY(22), W, ScaleY(24));
    Title.Font.Style := [fsBold];
    Title.Font.Size := Title.Font.Size + 3;
    Title.AutoSize := False;
    Title.Caption := T('OpenCue is already installed', 'OpenCue ist bereits installiert');

    Versions := TNewStaticText.Create(Form);
    Versions.Parent := Form;
    Versions.SetBounds(X, ScaleY(62), W, ScaleY(44));
    Versions.AutoSize := False;
    Versions.WordWrap := True;
    Versions.Caption := T('Installed version:  ', 'Installierte Version:  ') + 'v' + ExistingVersion + #13#10 + T('This setup:  ', 'Dieses Setup:  ') + ThisLabel;

    Status := TNewStaticText.Create(Form);
    Status.Parent := Form;
    Status.SetBounds(X, ScaleY(112), W, ScaleY(46));
    Status.AutoSize := False;
    Status.WordWrap := True;
    case Mode of
      1: Status.Caption := T('A newer version is available in this setup. Your data is kept.', 'Dieses Setup enthält eine neuere Version. Ihre Daten bleiben erhalten.');
      2: Status.Caption := T('This version is already installed. Your data is kept.', 'Diese Version ist bereits installiert. Ihre Daten bleiben erhalten.');
    else
      Status.Caption := T('A newer version is installed than this setup.', 'Installiert ist eine neuere Version als in diesem Setup.');
    end;

    BtnMain := TNewButton.Create(Form);
    BtnMain.Parent := Form;
    case Mode of
      1: BtnMain.Caption := T('Update OpenCue to ', 'OpenCue aktualisieren auf ') + ThisLabel;
      2: BtnMain.Caption := T('Reinstall OpenCue', 'OpenCue neu installieren');
    else
      BtnMain.Caption := T('Install older version ', 'Ältere Version installieren ') + ThisLabel;
    end;
    BtnMain.ModalResult := mrYes;
    BtnMain.SetBounds(X, ScaleY(172), W, ScaleY(30));

    BtnUninstall := TNewButton.Create(Form);
    BtnUninstall.Parent := Form;
    BtnUninstall.Caption := T('Uninstall OpenCue', 'OpenCue deinstallieren');
    BtnUninstall.ModalResult := mrNo;
    BtnUninstall.SetBounds(X, ScaleY(210), W, ScaleY(30));

    BtnCancel := TNewButton.Create(Form);
    BtnCancel.Parent := Form;
    BtnCancel.Caption := T('Cancel', 'Abbrechen');
    BtnCancel.ModalResult := mrCancel;
    BtnCancel.Default := True;                  // Enter = Abbrechen
    BtnCancel.Cancel := True;                   // Esc = Abbrechen
    BtnCancel.SetBounds(X, ScaleY(248), W, ScaleY(30));

    Form.ActiveControl := BtnCancel;
    case Form.ShowModal() of
      mrYes: Result := 1;
      mrNo: Result := 2;
    end;
  finally
    Form.Free();
  end;
end;

function InitializeSetup(): Boolean;
var
  Params: String;
  Choice, ResultCode: Integer;
begin
  Result := True;
  German := GermanUI();
  if CompareText(ExpandConstant('{language}'), 'german') = 0 then
    German := True
  else if CompareText(ExpandConstant('{language}'), 'english') = 0 then
    German := (ExpandConstant('{param:LANG|}') = 'german') or ((ExpandConstant('{param:LANG|}') = '') and GermanUI());
  Existing := InstalledInfo(ExistingVersion, ExistingUninstall);
  Mode := 0;
  if Existing then begin
    case CompareVersions(ThisVersion, ExistingVersion) of
      1: Mode := 1;
      0: Mode := 2;
    else
      Mode := 3;
    end;
  end;
  Params := Uppercase(GetCmdTail);
  if (Pos('/SILENT', Params) > 0) or (Pos('/VERYSILENT', Params) > 0) then
    Exit;                                       // stiller Modus (Update aus OpenCue, Tests): keine Rueckfrage
  if not Existing then
    Exit;                                       // erste Installation: normal durchklicken
  Choice := AskExisting();
  if Choice = 1 then
    Result := True                              // weiter mit der Installation
  else begin
    if (Choice = 2) and (ExistingUninstall <> '') then
      Exec(RemoveQuotes(ExistingUninstall), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);       // normale (sichtbare) Deinstallation: fragt nach den Daten
    Result := False;                            // Abbrechen (Vorgabe) oder Deinstallation gestartet: dieses Setup endet
  end;
end;

// ------------------------------------------------------------------------------------------------ Beschriftungen (beide Sprachen, umschaltbar auf der Willkommensseite)
function ModeTitle(): String;
begin
  case Mode of
    1: Result := T('Update OpenCue', 'OpenCue aktualisieren');
    2: Result := T('Reinstall OpenCue', 'OpenCue neu installieren');
    3: Result := T('Install an older OpenCue version', 'Ältere OpenCue-Version installieren');
  else
    Result := T('Welcome to OpenCue ', 'Willkommen bei OpenCue ') + ThisLabel;
  end;
end;

procedure ApplyTexts(PageID: Integer);
var
  Text: String;
begin
  WizardForm.BackButton.Caption := T('< &Back', '< &Zurück');
  WizardForm.CancelButton.Caption := T('Cancel', 'Abbrechen');
  if PageID = wpReady then begin
    if Mode = 1 then
      WizardForm.NextButton.Caption := T('&Update', '&Aktualisieren')
    else
      WizardForm.NextButton.Caption := T('&Install', '&Installieren');
  end else if PageID = wpFinished then
    WizardForm.NextButton.Caption := T('&Finish', '&Fertig')
  else
    WizardForm.NextButton.Caption := T('&Next >', '&Weiter >');

  LangLabel.Caption := 'Language / Sprache';
  if PageID = wpWelcome then begin
    WizardForm.WelcomeLabel1.Caption := ModeTitle();
    case Mode of
      1: Text := T('Update from v', 'Update von v') + ExistingVersion + T(' to ', ' auf ') + ThisLabel + '.' + #13#10#13#10 + T('Your data is kept.', 'Ihre Daten bleiben erhalten.');
      2: Text := T('Reinstall ', 'Neuinstallation von ') + ThisLabel + '.' + #13#10#13#10 + T('Your data is kept.', 'Ihre Daten bleiben erhalten.');
      3: Text := T('The installed version v', 'Installiert ist die neuere Version v') + ExistingVersion + T(' is newer than this setup.', '.');
    else
      Text := T('DMX lighting control console.', 'DMX-Lichtsteuerpult.') + #13#10#13#10 + T('Click Next to continue.', 'Klicken Sie auf Weiter, um fortzufahren.');
    end;
    WizardForm.WelcomeLabel2.Caption := Text;
  end else if PageID = wpInfoBefore then begin
    WizardForm.PageNameLabel.Caption := T('License', 'Lizenz');
    WizardForm.PageDescriptionLabel.Caption := 'GNU General Public License v3';
    WizardForm.InfoBeforeClickLabel.Caption := T('Click Next to continue.', 'Klicken Sie auf Weiter, um fortzufahren.');
  end else if PageID = wpSelectDir then begin
    WizardForm.PageNameLabel.Caption := T('Program folder', 'Programmordner');
    WizardForm.PageDescriptionLabel.Caption := T('Where should OpenCue be installed?', 'Wo soll OpenCue installiert werden?');
    WizardForm.SelectDirLabel.Caption := T('OpenCue will be installed in this folder.', 'OpenCue wird in diesem Ordner installiert.');
    WizardForm.SelectDirBrowseLabel.Caption := T('Click Next to continue, or Browse to choose another folder.', 'Weiter zum Fortfahren, Durchsuchen für einen anderen Ordner.');
    WizardForm.DirBrowseButton.Caption := T('&Browse...', '&Durchsuchen...');
  end else if PageID = DataPage.ID then begin
    DataPage.Caption := T('Data folder', 'Datenordner');
    DataPage.Description := T('Where should OpenCue keep your data?', 'Wo soll OpenCue Ihre Daten speichern?');
    DataPage.SubCaptionLabel.Caption := T('Shows, layouts, fixtures and settings are stored here.', 'Shows, Layouts, Scheinwerfer und Einstellungen werden hier gespeichert.');
  end else if PageID = ShortcutsPage.ID then begin
    ShortcutsPage.Caption := T('Shortcuts', 'Verknüpfungen');
    ShortcutsPage.Description := T('Where should OpenCue appear?', 'Wo soll OpenCue erscheinen?');
    CbStartMenu.Caption := T('Start menu shortcut', 'Startmenü-Verknüpfung');
    CbDesktop.Caption := T('Desktop shortcut', 'Desktop-Verknüpfung');
    ShortcutsNote.Caption := T('OpenCue is always available in the Windows search.', 'OpenCue ist immer über die Windows-Suche auffindbar.');
  end else if PageID = wpReady then begin
    WizardForm.PageNameLabel.Caption := T('Ready', 'Bereit');
    WizardForm.PageDescriptionLabel.Caption := T('Summary', 'Übersicht');
    if Mode = 1 then
      WizardForm.ReadyLabel.Caption := T('Click Update to begin.', 'Klicken Sie auf Aktualisieren, um zu beginnen.')
    else
      WizardForm.ReadyLabel.Caption := T('Click Install to begin.', 'Klicken Sie auf Installieren, um zu beginnen.');
  end else if PageID = wpInstalling then begin
    WizardForm.PageNameLabel.Caption := T('Installing', 'Installation');
    WizardForm.PageDescriptionLabel.Caption := T('Please wait...', 'Bitte warten...');
  end else if PageID = wpFinished then begin
    if Mode = 1 then
      WizardForm.FinishedHeadingLabel.Caption := T('OpenCue was updated', 'OpenCue wurde aktualisiert')
    else
      WizardForm.FinishedHeadingLabel.Caption := T('OpenCue is installed', 'OpenCue wurde installiert');
    WizardForm.FinishedLabel.Caption := T('Click Finish to close the setup.', 'Klicken Sie auf Fertig, um das Setup zu beenden.');
    if WizardForm.RunList.Items.Count > 0 then
      WizardForm.RunList.ItemCaption[0] := T('Start OpenCue', 'OpenCue starten');
    if not RunListMoved then begin
      // die Checkbox sass minimal zu weit links (angeschnitten): ein Stueck nach rechts
      WizardForm.RunList.Left := WizardForm.RunList.Left + ScaleX(12);
      WizardForm.RunList.Width := WizardForm.RunList.Width - ScaleX(12);
      RunListMoved := True;
    end;
  end;
end;

procedure LangChanged(Sender: TObject);
begin
  German := LangCombo.ItemIndex = 1;
  ApplyTexts(wpWelcome);       // die Sprachwahl gibt es nur auf der Willkommensseite
end;

procedure InitializeWizard;
var
  Top: Integer;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
  DownloadPage.ShowBaseNameInsteadOfUrl := True;

  // Datenordner: nur bei Neuinstallation (siehe ShouldSkipPage); steht der Ordner schon in der Konfiguration, wird sie nicht angefasst
  DataPage := CreateInputDirPage(wpSelectDir, '', '', '', False, '');
  DataPage.Add('');
  DataPage.Values[0] := DefaultDataDir();

  // Verknuepfungen: zwei Haken (die Windows-Suche richtet das Setup immer ein)
  ShortcutsPage := CreateCustomPage(DataPage.ID, '', '');
  CbStartMenu := TNewCheckBox.Create(ShortcutsPage);
  CbStartMenu.Parent := ShortcutsPage.Surface;
  CbStartMenu.SetBounds(0, ScaleY(8), ShortcutsPage.SurfaceWidth, ScaleY(22));
  CbStartMenu.Checked := True;
  CbDesktop := TNewCheckBox.Create(ShortcutsPage);
  CbDesktop.Parent := ShortcutsPage.Surface;
  CbDesktop.SetBounds(0, ScaleY(40), ShortcutsPage.SurfaceWidth, ScaleY(22));
  CbDesktop.Checked := True;
  ShortcutsNote := TNewStaticText.Create(ShortcutsPage);
  ShortcutsNote.Parent := ShortcutsPage.Surface;
  ShortcutsNote.SetBounds(0, ScaleY(84), ShortcutsPage.SurfaceWidth, ScaleY(48));
  ShortcutsNote.AutoSize := False;
  ShortcutsNote.WordWrap := True;

  // Sprache direkt auf der Willkommensseite
  Top := WizardForm.WelcomePage.Height - ScaleY(70);
  LangLabel := TNewStaticText.Create(WizardForm);
  LangLabel.Parent := WizardForm.WelcomePage;
  LangLabel.Left := WizardForm.WelcomeLabel2.Left;
  LangLabel.Top := Top;
  LangCombo := TNewComboBox.Create(WizardForm);
  LangCombo.Parent := WizardForm.WelcomePage;
  LangCombo.Style := csDropDownList;
  LangCombo.Left := WizardForm.WelcomeLabel2.Left;
  LangCombo.Top := Top + ScaleY(20);
  LangCombo.Width := ScaleX(200);
  LangCombo.Items.Add('English');
  LangCombo.Items.Add('Deutsch');
  if German then
    LangCombo.ItemIndex := 1
  else
    LangCombo.ItemIndex := 0;
  LangCombo.OnChange := @LangChanged;
  ApplyTexts(wpWelcome);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  ApplyTexts(CurPageID);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = DataPage.ID then
    Result := WizardSilent or FileExists(ConfigFile());
  if PageID = wpSelectDir then
    Result := Existing;                         // Update/Neuinstallation: der vorhandene Programmordner wird weiterverwendet
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Folder: String;
begin
  Result := True;
  if CurPageID = DataPage.ID then begin
    Folder := Trim(DataPage.Values[0]);
    // vollstaendiger Pfad: "X:\..." oder "\\Server\..."
    if (Length(Folder) < 3) or not (((Folder[2] = ':') and (Folder[3] = '\')) or (Copy(Folder, 1, 2) = '\\')) then begin
      MsgBox(T('Please enter a full folder path, for example D:\OpenCue', 'Bitte einen vollständigen Ordnerpfad eingeben, zum Beispiel D:\OpenCue'), mbError, MB_OK);
      Result := False;
    end;
    Exit;
  end;
  WebView2Downloaded := False;
  if (CurPageID = wpReady) and (not WebView2Installed()) then begin
    DownloadPage.Clear;
    DownloadPage.Add(WebView2BootstrapperUrl, 'MicrosoftEdgeWebview2Setup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        WebView2Downloaded := True;
      except
        if DownloadPage.AbortedByUser then begin
          Result := False;
        end else begin
          // offline o. ae.: weiter installieren, OpenCue weist beim Start darauf hin
          SuppressibleMsgBox(T('The Microsoft Edge WebView2 Runtime could not be downloaded.' + #13#10 + 'OpenCue will be installed anyway. If its window does not open, install the runtime from' + #13#10 + 'https://developer.microsoft.com/microsoft-edge/webview2/',
            'Die Microsoft Edge WebView2-Laufzeit konnte nicht heruntergeladen werden.' + #13#10 + 'OpenCue wird trotzdem installiert. Öffnet sich das Fenster nicht, installieren Sie die Laufzeit von' + #13#10 + 'https://developer.microsoft.com/microsoft-edge/webview2/'), mbInformation, MB_OK, IDOK);
        end;
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;

// Uebersicht auf der Seite "Bereit zur Installation": was wird erledigt
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  Lines, Folder: String;
begin
  case Mode of
    1: Lines := T('Update OpenCue from v', 'OpenCue aktualisieren von v') + ExistingVersion + T(' to ', ' auf ') + ThisLabel;
    2: Lines := T('Reinstall OpenCue ', 'OpenCue neu installieren: ') + ThisLabel;
    3: Lines := T('Install the older version ', 'Ältere Version installieren: ') + ThisLabel;
  else
    Lines := T('Install OpenCue ', 'OpenCue installieren: ') + ThisLabel;
  end;
  Lines := Lines + NewLine + NewLine + T('Program folder:', 'Programmordner:') + NewLine + Space + WizardDirValue;
  Folder := ExpandConstant('{param:DATADIR|}');
  if Folder = '' then
    Folder := Trim(DataPage.Values[0]);
  if FileExists(ConfigFile()) then
    Lines := Lines + NewLine + NewLine + T('Data folder and settings:', 'Datenordner und Einstellungen:') + NewLine + Space + T('unchanged (existing configuration is kept)', 'unverändert (die vorhandene Konfiguration bleibt)')
  else begin
    Lines := Lines + NewLine + NewLine + T('Data folder:', 'Datenordner:') + NewLine + Space + Folder;
    Lines := Lines + NewLine + NewLine + T('Language of OpenCue:', 'Sprache von OpenCue:') + NewLine + Space + LangCombo.Text;
  end;
  Lines := Lines + NewLine + NewLine + T('Shortcuts:', 'Verknüpfungen:');
  if CbStartMenu.Checked then
    Lines := Lines + NewLine + Space + T('Start menu', 'Startmenü');
  if CbDesktop.Checked then
    Lines := Lines + NewLine + Space + T('Desktop', 'Desktop');
  Lines := Lines + NewLine + Space + T('Windows search (automatic)', 'Windows-Suche (automatisch)');
  if not WebView2Installed() then
    Lines := Lines + NewLine + NewLine + T('The Microsoft Edge WebView2 Runtime is missing and will be downloaded (internet needed once).', 'Die Microsoft Edge WebView2-Laufzeit fehlt und wird heruntergeladen (einmalig Internet nötig).');
  Result := Lines;
end;

// ------------------------------------------------------------------------------------------------ Konfiguration schreiben
function Hex4(N: Integer): String;
begin
  Result := HexDigits[(N div 4096) mod 16 + 1] + HexDigits[(N div 256) mod 16 + 1] + HexDigits[(N div 16) mod 16 + 1] + HexDigits[N mod 16 + 1];
end;

function JsonEscape(const S: String): String;
var
  I: Integer;
  C: Char;
begin
  Result := '';
  for I := 1 to Length(S) do begin
    C := S[I];
    if C = '\' then
      Result := Result + '\\'
    else if C = '"' then
      Result := Result + '\"'
    else if Ord(C) > 126 then
      Result := Result + '\u' + Hex4(Ord(C))     // nur ASCII in der Datei: keine Zeichensatzprobleme
    else if Ord(C) < 32 then
      Result := Result + ' '
    else
      Result := Result + C;
  end;
end;

procedure WriteAppConfig();
var
  Folder, Language, Json: String;
begin
  if FileExists(ConfigFile()) then
    Exit;                                       // vorhandene Konfiguration (Update/Neuinstallation) nie ueberschreiben
  Folder := ExpandConstant('{param:DATADIR|}');
  if (Folder = '') and (not WizardSilent) then
    Folder := Trim(DataPage.Values[0]);
  if SameText(RemoveBackslash(Folder), RemoveBackslash(DefaultDataDir())) then
    Folder := '';                               // Standardordner: nichts eintragen
  if German then
    Language := 'de'
  else
    Language := 'en';
  Json := '{' + #13#10 +
          '  "language": "' + Language + '",' + #13#10;
  if Folder <> '' then
    Json := Json + '  "custom_data_path": "' + JsonEscape(RemoveBackslash(Folder)) + '",' + #13#10;
  Json := Json + '  "first_start_done": false' + #13#10 + '}' + #13#10;
  ForceDirectories(ConfigDir());
  SaveStringToFile(ConfigFile(), Json, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then begin
    if WebView2Downloaded then
      Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode);
    WriteAppConfig();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Nur bei der normalen (sichtbaren) Deinstallation fragen. Im stillen Modus wuerde MsgBox "Ja" liefern: die Daten des Benutzers bleiben dort IMMER erhalten.
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then begin
    if MsgBox(T('Also delete your OpenCue data (shows, layouts, fixtures, effects, settings)?', 'Auch Ihre OpenCue-Daten löschen (Shows, Layouts, Scheinwerfer, Effekte, Einstellungen)?') + #13#10 + DefaultDataDir() + #13#10#13#10 +
              T('Choose No to keep it.', 'Mit Nein bleiben sie erhalten.'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(DefaultDataDir(), True, True, True);
  end;
end;

function InitializeUninstall(): Boolean;
begin
  German := GermanUI();
  Result := True;
end;
