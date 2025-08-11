@echo off
REM AI Advanced App - Windows Stop Script
REM =====================================

echo.
echo ========================================
echo  AI Advanced App - Stopping System
echo ========================================
echo.

REM Check if Docker is running
echo [INFO] Checking if Docker is running...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not installed!
    echo [ERROR] Cannot stop containers without Docker.
    pause
    exit /b 1
)

echo [SUCCESS] Docker is running
echo.

REM Stop and remove containers
echo [INFO] Stopping all containers...
docker-compose down

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo  SUCCESS! System has been stopped
    echo ========================================
    echo.
    echo   All containers have been stopped and removed.
    echo   Data is preserved in Docker volumes.
    echo.
    echo ========================================
    echo  Quick Commands:
    echo ========================================
    echo.
    echo   Start system:  start-win.bat
    echo   View logs:     docker-compose logs
    echo   Remove data:   docker-compose down -v
    echo.
    echo ========================================
) else (
    echo.
    echo [ERROR] Failed to stop some containers!
    echo [ERROR] Check Docker status: docker ps
    echo.
)

echo.
echo [INFO] Press any key to exit...
pause >nul
