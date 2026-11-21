; Inno-Setup-Installer fuer OpenCue (Windows 10 / 11, 64 Bit). Voraussetzung: dist\OpenCue\ (packaging\build.ps1).
; Bauen:  powershell -File packaging\build.ps1 -Installer      (oder ISCC.exe packaging\OpenCue.iss)
;
; Sprachen: Englisch, Deutsch, Franzoesisch, Niederlaendisch, Italienisch, Spanisch. Inno Setup zeigt zu Beginn die Sprachwahl (vorbelegt nach der Windows-Sprache); die gewaehlte Sprache gilt fuer den
;   Installer UND fuer OpenCue (wird in die Konfiguration geschrieben). Eigene Texte stehen in packaging\OpenCue.messages.iss (erzeugt von make_installer_messages.py - dort aendern, nicht von Hand).
; Ablauf: Willkommen -> Lizenz (GPL, zum Lesen) -> Programmordner -> Datenordner (Shows, Layouts, Fixtures ...) -> Optionen (Startmenue, Desktop; aufklappbar: .ocshow oeffnen, Start mit Windows,
;   Sprachmodell laden, Update-Suche) -> Uebersicht -> Installieren -> Fertig (OpenCue starten).
; Ist OpenCue schon installiert, vergleicht das Setup die Versionen und fragt zuerst: Aktualisieren (neuere Version) / Neu installieren (gleiche) / Aeltere Version installieren,
;   Deinstallieren, Abbrechen (Vorgabe = Enter und Esc). Bei Update/Neuinstallation entfallen Programm- und Datenordner (gleicher Ordner, Daten bleiben).
;
; - Version/Firma/Adresse kommen aus app\version.py (-> packaging\version.iss, wird vom Build erzeugt).
; - Die Daten der Benutzer liegen im Datenordner (Standard %LOCALAPPDATA%\OpenCue) und werden bei Update und Neuinstallation nie angefasst; beim Deinstallieren wird gefragt (still: nie geloescht).
; - Eine frische Installation schreibt %LOCALAPPDATA%\OpenCue\config\app_config.json (Sprache, Datenordner als custom_data_path, first_start_done=false: OpenCue oeffnet beim ersten Start die
;   Demo-Show; auf Wunsch update_check_enabled=false und fetch_voice_model=true: OpenCue laedt das Sprachmodell beim ersten Start). Eine vorhandene Konfiguration wird nie ueberschrieben.
; - Das Sprachmodell (Vosk, 41 MB) ist NICHT im Installer (haelt ihn klein); OpenCue laedt es bei Bedarf (Einstellungen -> Triggerwort) oder auf Wunsch gleich beim ersten Start.
; - Edge WebView2: Fehlt die Laufzeit, laedt der Installer (nur dabei, Internet erlaubt) den kleinen Microsoft-Bootstrapper und fuehrt ihn aus. Ist er offline, geht die Installation
;   trotzdem weiter und OpenCue zeigt beim Start einen verstaendlichen Hinweis. OpenCue selbst braucht kein Internet.
; - Update aus OpenCue heraus (app\updater.py): das Programm startet NACH dem Beenden "OpenCue-Setup-v<Version>.exe /SILENT /NORESTART /CLOSEAPPLICATIONS"; im stillen Modus startet das
;   Setup OpenCue am Ende wieder (keine Rueckfragen).
; - Automatisierung / Tests: /DATADIR="D:\OpenCue" (Datenordner), /CONFIGDIR="..." (Ort der app_config.json statt %LOCALAPPDATA%\OpenCue\config), /NOLAUNCH=1 (stiller Modus startet
;   OpenCue nicht), /LANG=german (Sprache; Namen: english german french dutch italian spanish), dazu die ueblichen /VERYSILENT /DIR="..." /SUPPRESSMSGBOXES /NORESTART. Test-Fassung neben einer
;   echten Installation: ISCC /DAppGuid=<andere GUID> (und /DTestAppVersion=1.0.1 fuer eine andere Versionsnummer).

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
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
WizardSizePercent=110
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
ChangesAssociations=yes
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
UsePreviousLanguage=no
SetupMutex=OpenCueSetupMutex
CloseApplications=yes
RestartApplications=no
DisableReadyPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

#include "OpenCue.messages.iss"

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
; Dateizuordnung (Option "Erweitert"): Doppelklick auf eine .ocshow-Datei (Export-Paket einer Show) oeffnet sie in OpenCue (nur fuer den Benutzer; wird beim Deinstallieren entfernt)
Root: HKA; Subkey: "Software\Classes\.ocshow"; ValueType: string; ValueName: ""; ValueData: "OpenCue.Show"; Flags: uninsdeletevalue uninsdeletekeyifempty; Check: WantAssoc
Root: HKA; Subkey: "Software\Classes\OpenCue.Show"; ValueType: string; ValueName: ""; ValueData: "OpenCue show"; Flags: uninsdeletekey; Check: WantAssoc
Root: HKA; Subkey: "Software\Classes\OpenCue.Show\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Check: WantAssoc
Root: HKA; Subkey: "Software\Classes\OpenCue.Show\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Check: WantAssoc
; Start mit Windows (Option "Erweitert"; derselbe Eintrag wie Einstellungen -> Allgemein -> Start mit Windows, app\autostart.py)
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Check: WantAutostartWindow
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"" --no-ui"; Flags: uninsdeletevalue; Check: WantAutostartServer

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:RunStart}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Flags: nowait runasoriginaluser; Check: RelaunchAfterSilent

[Code]
const
  WebView2ClientGuid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2BootstrapperUrl = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';
  HexDigits = '0123456789abcdef';
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#AppGuid}}_is1';
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';
  ThisVersion = '{#AppVersion}';
  ThisLabel = '{#AppVersionLabel}';

var
  DownloadPage: TDownloadWizardPage;
  DataPage: TInputDirWizardPage;
  OptionsPage: TWizardPage;
  CbStartMenu, CbDesktop, CbAssoc, CbAutostart, CbHeadless, CbVoice, CbUpdates: TNewCheckBox;
  OptNote: TNewStaticText;
  AdvButton: TNewButton;
  AdvShown: Boolean;
  Existing: Boolean;                // OpenCue ist schon installiert
  ExistingVersion, ExistingUninstall: String;
  Mode: Integer;                    // 0 neu, 1 Update (Setup neuer), 2 Neuinstallation (gleiche Version), 3 aeltere Version
  WebView2Downloaded: Boolean;

// ------------------------------------------------------------------------------------------------ Texte (packaging\OpenCue.messages.iss)
function M(const Key: String): String;
begin
  Result := CustomMessage(Key);
end;

function M1(const Key, A: String): String;
begin
  Result := FmtMessage(CustomMessage(Key), [A]);
end;

function M2(const Key, A, B: String): String;
begin
  Result := FmtMessage(CustomMessage(Key), [A, B]);
end;

// Sprachkuerzel von OpenCue (static/locales) passend zur gewaehlten Setup-Sprache
function LangCode(): String;
var
  L: String;
begin
  L := ActiveLanguage();
  if L = 'german' then Result := 'de'
  else if L = 'french' then Result := 'fr'
  else if L = 'dutch' then Result := 'nl'
  else if L = 'italian' then Result := 'it'
  else if L = 'spanish' then Result := 'es'
  else Result := 'en';
end;

function LangName(): String;
var
  L: String;
begin
  L := ActiveLanguage();
  if L = 'german' then Result := 'Deutsch'
  else if L = 'french' then Result := 'Fran' + #231 + 'ais'
  else if L = 'dutch' then Result := 'Nederlands'
  else if L = 'italian' then Result := 'Italiano'
  else if L = 'spanish' then Result := 'Espa' + #241 + 'ol'
  else Result := 'English';
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

function WantAssoc(): Boolean;
begin
  Result := WizardSilent or CbAssoc.Checked;                    // still (Update aus OpenCue): wie bisher einrichten
end;

function WantAutostartWindow(): Boolean;
begin
  Result := (not WizardSilent) and CbAutostart.Checked and (not CbHeadless.Checked);
end;

function WantAutostartServer(): Boolean;
begin
  Result := (not WizardSilent) and CbAutostart.Checked and CbHeadless.Checked;
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
  Form := CreateCustomForm(544, 314, False, True);       // Groesse in 96-dpi-Einheiten: wird von Inno selbst skaliert
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
    Title.Font.Style := [fsBold];
    Title.Font.Size := Title.Font.Size + 3;
    Title.AutoSize := True;
    Title.Caption := M('AlreadyTitle');
    Title.Left := X;
    Title.Top := ScaleY(22);

    Versions := TNewStaticText.Create(Form);
    Versions.Parent := Form;
    Versions.SetBounds(X, ScaleY(62), W, ScaleY(44));
    Versions.AutoSize := False;
    Versions.WordWrap := True;
    Versions.Caption := M('InstalledVersion') + '  v' + ExistingVersion + #13#10 + M('ThisSetup') + '  ' + ThisLabel;

    Status := TNewStaticText.Create(Form);
    Status.Parent := Form;
    Status.SetBounds(X, ScaleY(112), W, ScaleY(46));
    Status.AutoSize := False;
    Status.WordWrap := True;
    case Mode of
      1: Status.Caption := M('ExistNewer');
      2: Status.Caption := M('ExistSame');
    else
      Status.Caption := M('ExistOlder');
    end;

    BtnMain := TNewButton.Create(Form);
    BtnMain.Parent := Form;
    case Mode of
      1: BtnMain.Caption := M1('BtnUpdateTo', ThisLabel);
      2: BtnMain.Caption := M('BtnReinstall');
    else
      BtnMain.Caption := M1('BtnOlder', ThisLabel);
    end;
    BtnMain.ModalResult := mrYes;
    BtnMain.SetBounds(X, ScaleY(172), W, ScaleY(30));

    BtnUninstall := TNewButton.Create(Form);
    BtnUninstall.Parent := Form;
    BtnUninstall.Caption := M('BtnUninstall');
    BtnUninstall.ModalResult := mrNo;
    BtnUninstall.SetBounds(X, ScaleY(210), W, ScaleY(30));

    BtnCancel := TNewButton.Create(Form);
    BtnCancel.Parent := Form;
    BtnCancel.Caption := SetupMessage(msgButtonCancel);
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

// ------------------------------------------------------------------------------------------------ Beschriftungen
function ModeTitle(): String;
begin
  case Mode of
    1: Result := M('TitleUpdate');
    2: Result := M('TitleReinstall');
    3: Result := M('TitleOlder');
  else
    Result := M1('TitleWelcome', ThisLabel);
  end;
end;

var
  LayY, LayW: Integer;

procedure PlaceBox(Box: TNewCheckBox; Indent: Integer; Show: Boolean);
begin
  Box.Visible := Show;
  if Show then begin
    Box.SetBounds(ScaleX(Indent), ScaleY(LayY), LayW - ScaleX(Indent), ScaleY(20));
    LayY := LayY + 24;
  end;
end;

procedure LayoutOptions();
var
  Fresh: Boolean;
begin
  LayW := OptionsPage.SurfaceWidth;
  Fresh := not FileExists(ConfigFile());
  LayY := 0;
  PlaceBox(CbStartMenu, 0, True);
  PlaceBox(CbDesktop, 0, True);
  LayY := LayY + 6;
  AdvButton.SetBounds(0, ScaleY(LayY), ScaleX(240), ScaleY(24));
  if AdvShown then
    AdvButton.Caption := '- ' + M('AdvHide')
  else
    AdvButton.Caption := '+ ' + M('AdvShow');
  LayY := LayY + 32;
  PlaceBox(CbAssoc, 0, AdvShown);
  PlaceBox(CbAutostart, 0, AdvShown);
  PlaceBox(CbHeadless, 22, AdvShown);
  PlaceBox(CbVoice, 0, AdvShown and Fresh);
  PlaceBox(CbUpdates, 0, AdvShown and Fresh);
  LayY := LayY + 8;
  OptNote.SetBounds(0, ScaleY(LayY), LayW, ScaleY(34));
  CbHeadless.Enabled := CbAutostart.Checked;
end;

procedure AdvClick(Sender: TObject);
begin
  AdvShown := not AdvShown;
  LayoutOptions();
end;

procedure AutostartClick(Sender: TObject);
begin
  CbHeadless.Enabled := CbAutostart.Checked;
  if not CbAutostart.Checked then
    CbHeadless.Checked := False;
end;

procedure ApplyTexts(PageID: Integer);
begin
  if PageID = wpWelcome then begin
    WizardForm.WelcomeLabel1.Caption := ModeTitle();
    case Mode of
      1: WizardForm.WelcomeLabel2.Caption := M2('WelcomeUpdate', ExistingVersion, ThisLabel);
      2: WizardForm.WelcomeLabel2.Caption := M1('WelcomeReinstall', ThisLabel);
      3: WizardForm.WelcomeLabel2.Caption := M1('WelcomeOlder', ExistingVersion);
    else
      WizardForm.WelcomeLabel2.Caption := M('WelcomeText');
    end;
  end else if PageID = DataPage.ID then begin
    DataPage.Caption := M('DataTitle');
    DataPage.Description := M('DataDesc');
    DataPage.SubCaptionLabel.Caption := M('DataSub');
  end else if PageID = OptionsPage.ID then begin
    OptionsPage.Caption := M('OptTitle');
    OptionsPage.Description := M('OptDesc');
    CbStartMenu.Caption := M('CbStart');
    CbDesktop.Caption := M('CbDesktop');
    CbAssoc.Caption := M('CbAssoc');
    CbAutostart.Caption := M('CbAutostart');
    CbHeadless.Caption := M('CbHeadless');
    CbVoice.Caption := M('CbVoice');
    CbUpdates.Caption := M('CbUpdates');
    OptNote.Caption := M('OptSearch');
    LayoutOptions();
  end else if PageID = wpReady then begin
    if Mode = 1 then begin
      WizardForm.NextButton.Caption := M('BtnUpdate');
      WizardForm.ReadyLabel.Caption := M('ReadyUpdate');
    end;
  end else if PageID = wpFinished then begin
    if Mode = 1 then
      WizardForm.FinishedHeadingLabel.Caption := M('FinUpdated')
    else
      WizardForm.FinishedHeadingLabel.Caption := M('FinInstalled');
  end;
end;

procedure InitializeWizard;
var
  RunValue: String;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
  DownloadPage.ShowBaseNameInsteadOfUrl := True;

  // Datenordner: nur bei Neuinstallation (siehe ShouldSkipPage); steht der Ordner schon in der Konfiguration, wird sie nicht angefasst
  DataPage := CreateInputDirPage(wpSelectDir, '', '', '', False, '');
  DataPage.Add('');
  DataPage.Values[0] := DefaultDataDir();

  // Optionen: oben die Verknuepfungen (die Windows-Suche richtet das Setup immer ein), darunter aufklappbar die erweiterten Optionen
  OptionsPage := CreateCustomPage(DataPage.ID, '', '');
  CbStartMenu := TNewCheckBox.Create(OptionsPage);
  CbStartMenu.Parent := OptionsPage.Surface;
  CbStartMenu.Checked := True;
  CbDesktop := TNewCheckBox.Create(OptionsPage);
  CbDesktop.Parent := OptionsPage.Surface;
  CbDesktop.Checked := True;
  AdvButton := TNewButton.Create(OptionsPage);
  AdvButton.Parent := OptionsPage.Surface;
  AdvButton.OnClick := @AdvClick;
  CbAssoc := TNewCheckBox.Create(OptionsPage);
  CbAssoc.Parent := OptionsPage.Surface;
  CbAssoc.Checked := True;
  CbAutostart := TNewCheckBox.Create(OptionsPage);
  CbAutostart.Parent := OptionsPage.Surface;
  CbAutostart.OnClick := @AutostartClick;
  CbHeadless := TNewCheckBox.Create(OptionsPage);
  CbHeadless.Parent := OptionsPage.Surface;
  CbVoice := TNewCheckBox.Create(OptionsPage);
  CbVoice.Parent := OptionsPage.Surface;
  CbUpdates := TNewCheckBox.Create(OptionsPage);
  CbUpdates.Parent := OptionsPage.Surface;
  CbUpdates.Checked := True;
  OptNote := TNewStaticText.Create(OptionsPage);
  OptNote.Parent := OptionsPage.Surface;
  OptNote.AutoSize := False;
  OptNote.WordWrap := True;
  // vorbelegen nach dem, was schon eingerichtet ist (Update: nichts verstellen)
  if RegQueryStringValue(HKCU, RunKey, 'OpenCue', RunValue) then begin
    CbAutostart.Checked := True;
    CbHeadless.Checked := Pos('--no-ui', RunValue) > 0;
  end;
  AdvShown := False;
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
      MsgBox(M('DataBad'), mbError, MB_OK);
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
          SuppressibleMsgBox(M('WebView2Fail'), mbInformation, MB_OK, IDOK);
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
  Fresh: Boolean;
begin
  Fresh := not FileExists(ConfigFile());
  case Mode of
    1: Lines := M2('MemoUpdate', ExistingVersion, ThisLabel);
    2: Lines := M1('MemoReinstall', ThisLabel);
    3: Lines := M1('MemoOlder', ThisLabel);
  else
    Lines := M1('MemoInstall', ThisLabel);
  end;
  Lines := Lines + NewLine + NewLine + M('MemoProgram') + NewLine + Space + WizardDirValue;
  Folder := ExpandConstant('{param:DATADIR|}');
  if Folder = '' then
    Folder := Trim(DataPage.Values[0]);
  if not Fresh then
    Lines := Lines + NewLine + NewLine + M('MemoDataKept') + NewLine + Space + M('MemoUnchanged')
  else begin
    Lines := Lines + NewLine + NewLine + M('MemoData') + NewLine + Space + Folder;
    Lines := Lines + NewLine + NewLine + M('MemoLang') + NewLine + Space + LangName();
  end;
  Lines := Lines + NewLine + NewLine + M('MemoShortcuts');
  if CbStartMenu.Checked then
    Lines := Lines + NewLine + Space + M('MemoStartMenu');
  if CbDesktop.Checked then
    Lines := Lines + NewLine + Space + M('MemoDesktop');
  Lines := Lines + NewLine + Space + M('MemoSearch');
  Lines := Lines + NewLine + NewLine + M('MemoOptions');
  if CbAssoc.Checked then
    Lines := Lines + NewLine + Space + M('MemoAssoc');
  if CbAutostart.Checked then begin
    if CbHeadless.Checked then
      Lines := Lines + NewLine + Space + M('MemoHeadless')
    else
      Lines := Lines + NewLine + Space + M('MemoAutostart');
  end;
  if Fresh and CbVoice.Checked then
    Lines := Lines + NewLine + Space + M('MemoVoice');
  if Fresh and (not CbUpdates.Checked) then
    Lines := Lines + NewLine + Space + M('MemoNoUpdates');
  if not WebView2Installed() then
    Lines := Lines + NewLine + NewLine + M('MemoWebView2');
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
  Folder, Json: String;
begin
  if FileExists(ConfigFile()) then
    Exit;                                       // vorhandene Konfiguration (Update/Neuinstallation) nie ueberschreiben
  Folder := ExpandConstant('{param:DATADIR|}');
  if (Folder = '') and (not WizardSilent) then
    Folder := Trim(DataPage.Values[0]);
  if SameText(RemoveBackslash(Folder), RemoveBackslash(DefaultDataDir())) then
    Folder := '';                               // Standardordner: nichts eintragen
  Json := '{' + #13#10 +
          '  "language": "' + LangCode() + '",' + #13#10;
  if Folder <> '' then
    Json := Json + '  "custom_data_path": "' + JsonEscape(RemoveBackslash(Folder)) + '",' + #13#10;
  if (not WizardSilent) and (not CbUpdates.Checked) then
    Json := Json + '  "update_check_enabled": false,' + #13#10;
  if (not WizardSilent) and CbVoice.Checked then
    Json := Json + '  "fetch_voice_model": true,' + #13#10;
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
    if (not WizardSilent) and (not CbAutostart.Checked) then
      RegDeleteValue(HKCU, RunKey, 'OpenCue');   // "Start mit Windows" abgewaehlt: ein frueher eingerichteter Eintrag verschwindet
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Nur bei der normalen (sichtbaren) Deinstallation fragen. Im stillen Modus wuerde MsgBox "Ja" liefern: die Daten des Benutzers bleiben dort IMMER erhalten.
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then begin
    if MsgBox(M1('UninstDelete', DefaultDataDir()), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(DefaultDataDir(), True, True, True);
  end;
end;
