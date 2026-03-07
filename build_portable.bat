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

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist\CLUBAL" (
    rmdir /s /q "dist\CLUBAL"
)

echo [1/3] Gerando build portable...
%PYI_CMD% --noconfirm --clean "clubal_portable.spec"
if errorlevel 1 (
    echo.
    echo [ERROR] Build falhou.
    echo.
    pause
    exit /b 1
)

echo [2/3] Verificando artefatos...
if not exist "dist\CLUBAL\CLUBAL.exe" (
    echo.
    echo [ERROR] CLUBAL.exe nao foi gerado em dist\CLUBAL
    echo.
    pause
    exit /b 1
)

echo [3/3] Build concluido com sucesso.
echo.
echo Pasta gerada:
echo dist\CLUBAL
echo.
echo Proximo uso:
echo - manter grade.xlsx local ao lado do app quando necessario
echo - grade_template.xlsx segue como modelo
echo - graphics ja vai junto no build
echo.
pause
exit /b 0