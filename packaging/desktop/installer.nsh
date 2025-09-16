; NSIS 安装器自定义脚本

; 安装前检查
!macro preInit
  ; 检查是否已安装
  ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\{appId}" "UninstallString"
  StrCmp $R0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
    "Audio Tuner 已经安装。$\n$\n点击 `确定` 卸载之前的版本，或点击 `取消` 退出安装。" \
    IDOK uninst
  Abort
  
  uninst:
    ClearErrors
    ExecWait '$R0 _?=$INSTDIR'
    
    IfErrors no_remove_uninstaller done
    no_remove_uninstaller:
  
  done:
!macroend

; 安装后操作
!macro customInstall
  ; 创建数据目录
  CreateDirectory "$APPDATA\AudioTuner"
  CreateDirectory "$APPDATA\AudioTuner\cache"
  CreateDirectory "$APPDATA\AudioTuner\objects"
  CreateDirectory "$APPDATA\AudioTuner\queue"
  
  ; 设置权限
  AccessControl::GrantOnFile "$APPDATA\AudioTuner" "(S-1-5-32-545)" "FullAccess"
!macroend

; 卸载前操作
!macro customUnInstall
  ; 询问是否保留用户数据
  MessageBox MB_YESNO|MB_ICONQUESTION \
    "是否保留用户数据和设置？$\n$\n选择 `是` 保留数据，选择 `否` 完全删除。" \
    IDYES keep_data
  
  ; 删除用户数据
  RMDir /r "$APPDATA\AudioTuner"
  
  keep_data:
!macroend

; 自定义页面
!macro customWelcomePage
  !insertmacro MUI_PAGE_WELCOME
!macroend

; 许可协议页面
!macro customLicensePage
  !insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!macroend

; 组件选择页面
!macro customComponentsPage
  !insertmacro MUI_PAGE_COMPONENTS
!macroend

; 安装目录页面
!macro customDirectoryPage
  !insertmacro MUI_PAGE_DIRECTORY
!macroend

; 安装进度页面
!macro customInstallPage
  !insertmacro MUI_PAGE_INSTFILES
!macroend

; 完成页面
!macro customFinishPage
  !define MUI_FINISHPAGE_RUN "$INSTDIR\Audio Tuner.exe"
  !define MUI_FINISHPAGE_RUN_TEXT "启动 Audio Tuner"
  !insertmacro MUI_PAGE_FINISH
!macroend
