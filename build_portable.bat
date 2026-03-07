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

echo [1/4] Gerando build portable...
%PYI_CMD% --noconfirm --clean "clubal_portable.spec"
if errorlevel 1 (
    echo.
    echo [ERROR] Build falhou.
    echo.
    pause
    exit /b 1
)

echo [2/4] Copiando arquivos operacionais para a raiz do pacote...

if not exist "dist\CLUBAL" (
    echo.
    echo [ERROR] Pasta dist\CLUBAL nao foi gerada.
    echo.
    pause
    exit /b 1
)

if exist "dist\CLUBAL\grade_template.xlsx" (
    del /f /q "dist\CLUBAL\grade_template.xlsx" >nul 2>nul
)

if exist "grade_template.xlsx" (
    copy /Y "grade_template.xlsx" "dist\CLUBAL\grade_template.xlsx" >nul
    if errorlevel 1 (
        echo.
        echo [ERROR] Falha ao copiar grade_template.xlsx para dist\CLUBAL
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

if exist "dist\CLUBAL\logo_cliente" (
    rmdir /s /q "dist\CLUBAL\logo_cliente"
)

mkdir "dist\CLUBAL\logo_cliente" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Falha ao criar a pasta dist\CLUBAL\logo_cliente
    echo.
    pause
    exit /b 1
)

echo [3/4] Verificando artefatos...
if not exist "dist\CLUBAL\CLUBAL.exe" (
    echo.
    echo [ERROR] CLUBAL.exe nao foi gerado em dist\CLUBAL
    echo.
    pause
    exit /b 1
)

if not exist "dist\CLUBAL\grade_template.xlsx" (
    echo.
    echo [ERROR] grade_template.xlsx nao foi colocado na raiz de dist\CLUBAL
    echo.
    pause
    exit /b 1
)

if not exist "dist\CLUBAL\logo_cliente" (
    echo.
    echo [ERROR] logo_cliente nao foi colocado na raiz de dist\CLUBAL
    echo.
    pause
    exit /b 1
)

if not exist "dist\CLUBAL\_internal\graphics" (
    echo.
    echo [ERROR] graphics interno nao foi empacotado em dist\CLUBAL\_internal
    echo.
    pause
    exit /b 1
)

echo [4/4] Build concluido com sucesso.
echo.
echo Pasta gerada:
echo dist\CLUBAL
echo.
echo Estrutura esperada para o cliente:
echo - CLUBAL.exe
echo - grade_template.xlsx
echo - logo_cliente\
echo - grade.xlsx (quando necessario, local ao lado do exe)
echo.
pause
exit /b 0