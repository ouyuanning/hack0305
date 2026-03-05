@echo off
REM Windows: 自动检测 python 命令
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%..\.."

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python3
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=python
    ) else (
        echo 未找到 python 或 python3，请先安装 Python 3
        exit /b 1
    )
)

echo 使用: %PYTHON%
%PYTHON% "%SCRIPT_DIR%setup_dependencies.py"
