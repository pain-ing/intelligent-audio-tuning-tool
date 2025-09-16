; Audio Tuner Desktop NSIS Installer (Option B: external installer from prepackaged build)
!define APP_NAME "Audio Tuner"
!define APP_ID   "AudioTuner"
!define COMPANY  "Audio Tuner Team"
!define VERSION  "1.0.0"

; Unicode + Modern UI
Unicode true
!include "MUI2.nsh"

!define MUI_ABORTWARNING
; Note: Using default NSIS icons to avoid build failure when custom icon is missing
;!define MUI_ICON "resources\\icon.ico"
;!define MUI_UNICON "resources\\icon.ico"

; Default installation folder
InstallDir "$PROGRAMFILES64\${APP_NAME}"

; Output installer
OutFile "out_build\AudioTuner-Setup-${VERSION}.exe"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

;--------------------------------
Section "Install"
  SetShellVarContext all

  ; Ensure target dir exists
  CreateDirectory "$INSTDIR"

  ; Copy prepackaged app contents (compile-time include from relative path)
  ; Note: electron-builder portable target does not place the main EXE in win-unpacked.
  ; Install resources then also install the portable EXE as our app launcher.
  SetOutPath "$INSTDIR"
  File /nonfatal /r "out_build_frontend\\win-unpacked\\*.*"
  ; Main executable is already included in win-unpacked

  ; All resources (Python, API, Worker, Frontend, FFmpeg) are already included in the packaged app

  ; Shortcuts
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe"
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"

  ; Uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Registry (for Programs and Features)
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "Publisher" "${COMPANY}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "InstallLocation" "$INSTDIR"

SectionEnd

;--------------------------------
Section "Uninstall"
  SetShellVarContext all
  ; Remove shortcuts
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"
  Delete "$DESKTOP\${APP_NAME}.lnk"

  ; Remove files
  RMDir /r "$INSTDIR"

  ; Registry
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
SectionEnd

