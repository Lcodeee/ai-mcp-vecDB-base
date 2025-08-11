@echo off
REM AI Advanced App - Windows Startup Script
REM ========================================

echo.
echo ========================================
echo  AI Advanced App - Starting System
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [INFO] .env file not found. Creating from template...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [SUCCESS] .env file created from .env.example
        echo [WARNING] Please edit .env file and add your Gemini API key before continuing!
        echo [INFO] Open .env file in notepad: notepad .env
        echo.
        pause
    ) else (
        echo [ERROR] .env.example file not found!
        echo [ERROR] Please create .env file manually with the following content:
        echo.
        echo GEMINI_API_KEY=your_actual_api_key_here
        echo POSTGRES_DB=vectordb
        echo POSTGRES_USER=postgres
        echo POSTGRES_PASSWORD=postgres123
        echo.
        pause
        exit /b 1
    )
)

REM Check if Docker is running
echo [INFO] Checking if Docker is running...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not installed!
    echo [ERROR] Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [SUCCESS] Docker is running
echo.

REM Stop any existing containers
echo [INFO] Stopping any existing containers...
docker-compose down >nul 2>&1

REM Build and start services
echo [INFO] Building and starting AI Advanced App...
echo [INFO] This may take a few minutes on first run...
echo.

docker-compose up --build -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services!
    echo [ERROR] Check Docker logs for details: docker-compose logs
    pause
    exit /b 1
)

echo.
echo [INFO] Services are starting. Waiting for the system to become healthy...
echo [INFO] This may take a minute...

REM Wait for services to be healthy
set /a timeout=60
set /a counter=0

:wait_loop
if %counter% geq %timeout% (
    echo [ERROR] Timeout waiting for services to start!
    echo [ERROR] Check logs: docker-compose logs
    pause
    exit /b 1
)

REM Check PostgreSQL health
docker-compose exec -T postgres pg_isready -U postgres >nul 2>&1
if %errorlevel% neq 0 (
    echo .
    timeout /t 1 /nobreak >nul
    set /a counter=%counter%+1
    goto wait_loop
)

REM Check MCP Server health  
curl -s http://localhost:8001/health >nul 2>&1
if %errorlevel% neq 0 (
    echo .
    timeout /t 1 /nobreak >nul
    set /a counter=%counter%+1
    goto wait_loop
)

REM Check FastAPI health
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo .
    timeout /t 1 /nobreak >nul
    set /a counter=%counter%+1
    goto wait_loop
)

echo.
echo ========================================
echo  SUCCESS! System is up and running!
echo ========================================
echo.
echo   - FastAPI App: http://localhost:8000
echo   - MCP Server:  http://localhost:8001
echo   - PostgreSQL:  localhost:5433
echo.
echo ========================================
echo  Quick Commands:
echo ========================================
echo.
echo   View logs:     docker-compose logs -f
echo   Stop system:   stop-win.bat
echo   Run tests:     python test_api.py
echo.
echo ========================================

REM Optional: Open browser to FastAPI docs
set /p openBrowser="Open FastAPI documentation in browser? (y/n): "
if /i "%openBrowser%"=="y" (
    start http://localhost:8000/docs
)

echo.
echo [INFO] Press any key to exit...
pause >nul
