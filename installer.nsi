; =============================================================================
;  YO Log PRO v19 - NSIS Installer Script
;  Ardei Constantin-Catalin (YO8ACR)
;  Compatible: Windows 7 SP1 / 8 / 10 / 11 (x64)
; =============================================================================

Unicode True

!include "MUI2.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; -- General info --------------------------------------------------------------
!define APP_NAME        "YO Log PRO"
!define APP_VERSION     "19.0"
!define APP_FULL_NAME   "YO Log PRO v19"
!define APP_EXE         "YO_Log_PRO_v19.exe"
!define APP_PUBLISHER   "Ardei Constantin-Catalin (YO8ACR)"
!define APP_URL         "https://github.com/acc1311/YOLogPRO"
!define APP_CONTACT     "yo8acr@gmail.com"
!define INSTALL_DIR     "$PROGRAMFILES64\YO Log PRO"
!define DATA_DIR        "$APPDATA\YOLogPRO"
!define REG_KEY         "Software\Microsoft\Windows\CurrentVersion\Uninstall\YOLogPRO"

Name            "${APP_FULL_NAME}"
OutFile         "YO_Log_PRO_v19_Setup.exe"
InstallDir      "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_KEY}" "InstallLocation"
RequestExecutionLevel admin
BrandingText    "YO Log PRO v${APP_VERSION} - YO8ACR"

; -- LZMA compression ---------------------------------------------------------
SetCompressor /SOLID lzma
SetCompressorDictSize 64

; -- MUI2 Interface -----------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON                    "icon.ico"
!define MUI_UNICON                  "icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT

!define MUI_WELCOMEPAGE_TITLE       "Welcome to ${APP_FULL_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT        "This wizard will install ${APP_FULL_NAME} on your computer.$\r$\n$\r$\nProfessional amateur radio logging software by YO8ACR.$\r$\n$\r$\n- Compatible with Windows 7 SP1, 8, 10, 11 (64-bit)$\r$\n- ANCOM Local Callbook: 4,964 callsigns offline$\r$\n- CAT Radio Control (Yaesu/Icom/Kenwood/Elecraft)$\r$\n- Export: Cabrillo, ADIF, CSV, EDI$\r$\n$\r$\nClick Next to continue."

!define MUI_FINISHPAGE_TITLE        "Installation Complete!"
!define MUI_FINISHPAGE_TEXT         "${APP_FULL_NAME} has been installed.$\r$\n$\r$\nDesktop shortcut and Start Menu entry created.$\r$\n$\r$\n73 de YO8ACR!"
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch ${APP_FULL_NAME} now"

; -- Installer pages ----------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; -- Uninstaller pages --------------------------------------------------------
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; -- Language (English) -------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"

; =============================================================================
;  INSTALL SECTION
; =============================================================================

Section "YO Log PRO v19" SecMain

    SectionIn RO  ; Read Only - cannot be deselected

    SetOutPath "$INSTDIR"

    ; -- Main EXE -------------------------------------------------------------
    File "dist\YO_Log_PRO_v19.exe"

    ; -- Icon -----------------------------------------------------------------
    File /nonfatal "icon.ico"

    ; -- Desktop shortcut -----------------------------------------------------
    CreateShortcut "$DESKTOP\${APP_FULL_NAME}.lnk" \
                   "$INSTDIR\${APP_EXE}" "" \
                   "$INSTDIR\icon.ico" 0 \
                   SW_SHOWNORMAL "" \
                   "YO Log PRO v19 - Amateur Radio Logger"

    ; -- Start Menu shortcut --------------------------------------------------
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_FULL_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" \
                    "$INSTDIR\icon.ico" 0 SW_SHOWNORMAL "" \
                    "YO Log PRO v19 - Amateur Radio Logger"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                    "$INSTDIR\Uninstall.exe"

    ; -- Registry - Add/Remove Programs ---------------------------------------
    WriteRegStr   HKLM "${REG_KEY}" "DisplayName"      "${APP_FULL_NAME}"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"   "${APP_VERSION}"
    WriteRegStr   HKLM "${REG_KEY}" "Publisher"        "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${REG_KEY}" "URLInfoAbout"     "${APP_URL}"
    WriteRegStr   HKLM "${REG_KEY}" "Contact"          "${APP_CONTACT}"
    WriteRegStr   HKLM "${REG_KEY}" "InstallLocation"  "$INSTDIR"
    WriteRegStr   HKLM "${REG_KEY}" "UninstallString"  "$INSTDIR\Uninstall.exe"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"      "$INSTDIR\icon.ico"
    WriteRegDWORD HKLM "${REG_KEY}" "NoModify"         1
    WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"         1
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${REG_KEY}" "EstimatedSize" "$0"

    ; -- Write uninstaller ----------------------------------------------------
    WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

; =============================================================================
;  UNINSTALL SECTION
; =============================================================================

Section "Uninstall"

    ; -- Delete installed files -----------------------------------------------
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\icon.ico"
    Delete "$INSTDIR\Uninstall.exe"

    ; -- Delete shortcuts ------------------------------------------------------
    Delete "$DESKTOP\${APP_FULL_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_FULL_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"

    ; -- Delete registry keys -------------------------------------------------
    DeleteRegKey HKLM "${REG_KEY}"

    ; -- Delete install dir (only if empty) -----------------------------------
    RMDir  /r "$INSTDIR\docs"
    RMDir  "$INSTDIR"

    ; -- User data: ask before deleting ---------------------------------------
    ${If} ${FileExists} "${DATA_DIR}\*.*"
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "Delete user data (logs, config)?$\r$\nFolder: ${DATA_DIR}$\r$\nSelect NO to keep your logs." \
            IDYES delete_data IDNO skip_data
        delete_data:
            RMDir /r "${DATA_DIR}"
        skip_data:
    ${EndIf}

SectionEnd

; =============================================================================
;  FUNCTIONS
; =============================================================================

Function .onInit
    ; -- 64-bit check ---------------------------------------------------------
    ${IfNot} ${RunningX64}
        MessageBox MB_OK|MB_ICONSTOP \
            "${APP_FULL_NAME} requires a 64-bit version of Windows.$\r$\nInstallation will be cancelled."
        Abort
    ${EndIf}

    ; -- Check for existing installation --------------------------------------
    ReadRegStr $R0 HKLM "${REG_KEY}" "UninstallString"
    ${If} $R0 != ""
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "${APP_FULL_NAME} is already installed.$\r$\nDo you want to uninstall the previous version first?" \
            IDYES uninst IDNO done
        uninst:
            ExecWait '$R0 /S'
        done:
    ${EndIf}
FunctionEnd

