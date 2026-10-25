Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "Sections.nsh"
Name "PC Sentinelle et John 34.0.3"
OutFile "Delivery34_0_3\PC_Sentinelle_John_Setup_34_0_3.exe"
InstallDir "$LOCALAPPDATA\Programs\PCSentinelleSuite-34.0.2"
InstallDirRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID zlib
CRCCheck force
Icon "SuitePayload\John\assets\john_v25.ico"
VIProductVersion "34.0.3.0"
VIAddVersionKey /LANG=1036 "ProductName" "PC Sentinelle et John"
VIAddVersionKey /LANG=1036 "FileDescription" "Installation autonome PC Sentinelle et John avec connexion IA"
VIAddVersionKey /LANG=1036 "FileVersion" "34.0.3"
VIAddVersionKey /LANG=1036 "LegalCopyright" "Projet Sentinelle"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "Cet assistant installe PC Sentinelle et John, avec leurs moteurs inclus.$\r$\n$\r$\nLa connexion IA utilise votre clé API personnelle. Aucun mot de passe ChatGPT n'est demandé.$\r$\n$\r$\nLes crédits API sont distincts de l'abonnement ChatGPT. Les outils locaux restent accessibles sans IA."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\John.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Afficher John et sa configuration IA"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Cette version nécessite Windows 10 ou 11 en 64 bits."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "Windows 10 ou 11 est nécessaire."
    Abort
  ${EndIf}
  SetShellVarContext current
FunctionEnd

Section "PC Sentinelle + John (moteurs inclus)" Main
  SectionIn RO
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "prepare_update.ps1"
  IfFileExists "$INSTDIR\John\runtime\python.exe" 0 prepared
  nsExec::ExecToStack /TIMEOUT=60000 '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\prepare_update.ps1" -InstallDir "$INSTDIR" -LogFile "$PLUGINSDIR\preflight.log"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    DetailPrint "$1"
    MessageBox MB_ICONSTOP "La mise à jour est arrêtée avant la copie. Fermez John et les outils PC puis réessayez.$\r$\nCode : $0" /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  prepared:
  SetOutPath "$INSTDIR"
  File /r "SuitePayload\*"
  WriteUninstaller "$INSTDIR\Desinstaller.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "DisplayName" "PC Sentinelle et John 34.0.3"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "DisplayVersion" "34.0.3"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "UninstallString" '$\"$INSTDIR\Desinstaller.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "DisplayIcon" "$INSTDIR\PC\PC_Sentinelle_V32.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402" "NoRepair" 1
  SetOutPath "$INSTDIR\John"
  nsExec::ExecToStack /TIMEOUT=90000 '"$INSTDIR\John\runtime\python.exe" -I "$INSTDIR\John\verify_install.py"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    DetailPrint "$1"
    MessageBox MB_ICONSTOP "Le contrôle de l'installation a échoué (code $0).$\r$\nRapport : $LOCALAPPDATA\PCSentinelleSuite\Logs\installation-check.txt" /SD IDOK
    SetErrorLevel 3
    Abort
  ${EndIf}
  CreateDirectory "$SMPROGRAMS\PC Sentinelle et John"
  SetOutPath "$INSTDIR\PC"
  CreateShortCut "$DESKTOP\PC Sentinelle.lnk" "$INSTDIR\PC\PC_Sentinelle_V32.exe"
  SetOutPath "$INSTDIR\John"
  CreateShortCut "$DESKTOP\John Sentinelle.lnk" "$INSTDIR\John.exe" "" "$INSTDIR\John\assets\john_v25.ico"
  CreateShortCut "$SMPROGRAMS\PC Sentinelle et John\PC Sentinelle.lnk" "$INSTDIR\PC\PC_Sentinelle_V32.exe"
  CreateShortCut "$SMPROGRAMS\PC Sentinelle et John\John.lnk" "$INSTDIR\John.exe" "" "$INSTDIR\John\assets\john_v25.ico"
  CreateShortCut "$SMPROGRAMS\PC Sentinelle et John\Désinstaller.lnk" "$INSTDIR\Desinstaller.exe"
  Delete "$DESKTOP\PC Sentinelle 34.0.2.lnk"
  Delete "$DESKTOP\John 34.0.2.lnk"
  Delete "$DESKTOP\Dossier John 34.0.2.lnk"
  RMDir /r "$SMPROGRAMS\PC Sentinelle et John 34.0.2"
SectionEnd

Section "Démarrer John avec ma session Windows" Startup
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "JohnPCSentinelle3402" '$\"$INSTDIR\John.exe$\"'
SectionEnd

Function .onInstSuccess
  ${IfNot} ${SectionIsSelected} ${Startup}
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "JohnPCSentinelle3402"
  ${EndIf}
FunctionEnd

Section "Uninstall"
  SetShellVarContext current
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "prepare_update.ps1"
  IfFileExists "$INSTDIR\John\runtime\python.exe" 0 unprepared
  nsExec::ExecToStack /TIMEOUT=60000 '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\prepare_update.ps1" -InstallDir "$INSTDIR" -LogFile "$PLUGINSDIR\preflight-uninstall.log"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Fermez John et PC Sentinelle puis relancez la désinstallation." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  unprepared:
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "JohnPCSentinelle3402"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PCSentinelleSuite3402"
  Delete "$DESKTOP\PC Sentinelle.lnk"
  Delete "$DESKTOP\John Sentinelle.lnk"
  RMDir /r "$SMPROGRAMS\PC Sentinelle et John"
  !include "uninstall_files.nsh"
  Delete "$INSTDIR\Desinstaller.exe"
  RMDir "$INSTDIR"
SectionEnd
