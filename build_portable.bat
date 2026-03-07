@echo off
setlocal

cd /d "%~dp0"

echo.
echo ========================================
echo   CLUBAL - Portable Build
echo ========================================
echo.

set "PYI_CMD="

py -m PyInstaller --version >nul 2>nul
if not errorlevel 1 (
    set "PYI_CMD=py -m PyInstaller"
)

if not defined PYI_CMD (
    python -m PyInstaller --version >nul 2>nul
    if not errorlevel 1 (
        set "PYI_CMD=python -m PyInstaller"
    )
)

if not defined PYI_CMD (
    where pyinstaller >nul 2>nul
    if not errorlevel 1 (
        set "PYI_CMD=pyinstaller"
    )
)

if not defined PYI_CMD (
    echo [ERROR] PyInstaller nao encontrado neste Windows/Python.
    echo.
    echo Tente instalar assim:
    echo   py -m pip install pyinstaller
    echo.
    echo Se o comando "py" nao existir, tente:
    echo   python -m pip install pyinstaller
    echo.
    pause
    exit /b 1
)

set "DESKTOP_DIR="

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do (
    set "DESKTOP_DIR=%%I"
)

if not defined DESKTOP_DIR (
    set "DESKTOP_DIR=%USERPROFILE%\Desktop"
)

set "OUT_ROOT=%DESKTOP_DIR%\CLUBAL_PORTABLE"
set "WORK_ROOT=%DESKTOP_DIR%\CLUBAL_BUILD_TEMP"
set "OUT_DIR=%OUT_ROOT%\CLUBAL"
set "WORK_BUILD=%WORK_ROOT%\build"

if not exist "%DESKTOP_DIR%" (
    set "OUT_ROOT=%CD%\dist"
    set "WORK_ROOT=%CD%\build"
    set "OUT_DIR=%OUT_ROOT%\CLUBAL"
    set "WORK_BUILD=%WORK_ROOT%"
)

echo [INFO] Portable output: %OUT_DIR%
echo [INFO] Build temp: %WORK_BUILD%
echo.

if exist "%WORK_ROOT%" (
    rmdir /s /q "%WORK_ROOT%"
)

if exist "%OUT_DIR%" (
    rmdir /s /q "%OUT_DIR%"
)

if not exist "%OUT_ROOT%" (
    mkdir "%OUT_ROOT%" >nul 2>nul
)

if not exist "%WORK_ROOT%" (
    mkdir "%WORK_ROOT%" >nul 2>nul
)

echo [1/4] Gerando build portable...
%PYI_CMD% --noconfirm --clean --distpath "%OUT_ROOT%" --workpath "%WORK_BUILD%" "clubal_portable.spec"
if errorlevel 1 (
    echo.
    echo [ERROR] Build falhou.
    echo.
    pause
    exit /b 1
)

echo [2/4] Copiando arquivos operacionais para a raiz do pacote...

if not exist "%OUT_DIR%" (
    echo.
    echo [ERROR] Pasta final nao foi gerada:
    echo %OUT_DIR%
    echo.
    pause
    exit /b 1
)

if exist "%OUT_DIR%\grade_template.xlsx" (
    del /f /q "%OUT_DIR%\grade_template.xlsx" >nul 2>nul
)

if exist "grade_template.xlsx" (
    copy /Y "grade_template.xlsx" "%OUT_DIR%\grade_template.xlsx" >nul
    if errorlevel 1 (
        echo.
        echo [ERROR] Falha ao copiar grade_template.xlsx para a raiz do pacote
        echo.
        pause
        exit /b 1
    )
) else (
    echo.
    echo [ERROR] Arquivo grade_template.xlsx nao encontrado na raiz do projeto.
    echo.
    pause
    exit /b 1
)

if exist "%OUT_DIR%\logo_cliente" (
    rmdir /s /q "%OUT_DIR%\logo_cliente"
)

mkdir "%OUT_DIR%\logo_cliente" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Falha ao criar a pasta logo_cliente na raiz do pacote
    echo.
    pause
    exit /b 1
)

echo [3/4] Verificando artefatos...
if not exist "%OUT_DIR%\CLUBAL.exe" (
    echo.
    echo [ERROR] CLUBAL.exe nao foi gerado:
    echo %OUT_DIR%\CLUBAL.exe
    echo.
    pause
    exit /b 1
)

if not exist "%OUT_DIR%\grade_template.xlsx" (
    echo.
    echo [ERROR] grade_template.xlsx nao foi colocado na raiz do pacote
    echo.
    pause
    exit /b 1
)

if not exist "%OUT_DIR%\logo_cliente" (
    echo.
    echo [ERROR] logo_cliente nao foi colocada na raiz do pacote
    echo.
    pause
    exit /b 1
)

if not exist "%OUT_DIR%\_internal\graphics" (
    echo.
    echo [ERROR] graphics interno nao foi empacotado em:
    echo %OUT_DIR%\_internal\graphics
    echo.
    pause
    exit /b 1
)

echo [4/4] Build concluido com sucesso.
echo.
echo Pasta gerada:
echo %OUT_DIR%
echo.
echo Estrutura esperada para o cliente:
echo - CLUBAL.exe
echo - grade_template.xlsx
echo - logo_cliente\
echo - grade.xlsx (quando necessario, local ao lado do exe)
echo.
pause
exit /b 0