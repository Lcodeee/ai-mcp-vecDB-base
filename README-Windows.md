# AI Advanced App - Windows Setup Guide

## 🪟 מדריך הפעלה למשתמשי Windows

### 📋 דרישות מערכת

לפני שמתחילים, וודאו שיש לכם:

1. **Windows 10/11** (64-bit)
2. **Docker Desktop for Windows** - [הורדה](https://docs.docker.com/desktop/install/windows-install/)
3. **WSL2** - מופעל ומוגדר (Docker Desktop דורש זאת)
4. **Python 3.8+** - [הורדה](https://www.python.org/downloads/windows/)
5. **Git for Windows** (אופציונלי) - [הורדה](https://git-scm.com/download/win)

### 🚀 הפעלה מהירה

1. **הורידו את הפרויקט** (אם עדיין לא עשיתם):
   ```batch
   git clone https://github.com/Lcodeee/ai-mcp-vecDB-base.git
   cd ai-mcp-vecDB-base
   ```

2. **הפעילו את Docker Desktop** - וודאו שהוא פועל לפני המשך

3. **הגדירו מפתח API**:
   - לחיצה כפולה על `start-win.bat` תיצור קובץ `.env` אוטומטית
   - ערכו את הקובץ והוסיפו את מפתח ה-Gemini API שלכם

4. **הפעילו את המערכת**:
   - לחיצה כפולה על `start-win.bat`
   - או הרצה מ-Command Prompt: `start-win.bat`

### 📁 קבצים חשובים למשתמשי Windows

- `start-win.bat` - הפעלת המערכת
- `stop-win.bat` - כיבוי המערכת  
- `test_api.py` - בדיקת המערכת (דורש Python)
- `.env` - הגדרות המערכת (נוצר אוטומטית)

### 🔧 פתרון בעיות נפוצות

#### "Docker is not running"
- **פתרון**: הפעילו Docker Desktop ווודאו שהוא רץ
- בדקו שיש לכם את האייקון של Docker במגש המערכת

#### "curl command not found"  
- **פתרון**: התקינו Git for Windows (כולל curl) או השתמשו ב-PowerShell:
  ```powershell
  Invoke-WebRequest http://localhost:8000/health
  ```

#### WSL2 לא מופעל
- **פתרון**: הפעילו WSL2 דרך PowerShell (כמנהל):
  ```powershell
  wsl --install
  ```

#### Python לא מותקן
- **פתרון**: הורידו והתקינו Python מהאתר הרשמי
- וודאו שבחרתם "Add Python to PATH" בהתקנה

### 🧪 בדיקת המערכת

לאחר ההפעלה, בדקו שהמערכת עובדת:

1. **דרך הדפדפן**:
   - FastAPI Docs: http://localhost:8000/docs
   - MCP Server: http://localhost:8001/health

2. **דרך Python** (מ-Command Prompt):
   ```batch
   python test_api.py
   ```

3. **דרך PowerShell**:
   ```powershell
   Invoke-RestMethod http://localhost:8000/health
   ```

### ⚡ פקודות שימושיות

```batch
REM הפעלת המערכת
start-win.bat

REM כיבוי המערכת  
stop-win.bat

REM צפייה בלוגים
docker-compose logs -f

REM בדיקת סטטוס containers
docker ps

REM הפעלה מחדש לאחר שינויים
docker-compose restart
```

### 📊 מוניטור המערכת

**בדיקת שירותים:**
- FastAPI App: http://localhost:8000
- MCP Server: http://localhost:8001  
- PostgreSQL: localhost:5433

**לוגים:**
```batch
REM כל השירותים
docker-compose logs

REM שירות ספציפי
docker-compose logs fastapi_app
docker-compose logs mcp_server
docker-compose logs postgres
```

### 💡 טיפים למשתמשי Windows

1. **השתמשו ב-Windows Terminal** - חוויה טובה יותר מ-Command Prompt רגיל
2. **VSCode עם WSL extension** - לעריכת קבצים בנוחות
3. **Docker Desktop Dashboard** - למוניטור containers בממשק גרפי
4. **שמרו גיבויים** של קובץ `.env` שלכם

### 🔄 עדכון המערכת

```batch
REM עצירת המערכת
stop-win.bat

REM עדכון הקוד (אם יש שינויים)
git pull

REM הפעלה מחדש  
start-win.bat
```

### 📞 תמיכה ועזרה

אם נתקלתם בבעיות:
1. בדקו את הלוגים: `docker-compose logs`
2. וודאו ש-Docker Desktop פועל
3. בדקו שפורטים 8000, 8001, 5433 פנויים
4. הפעילו מחדש את Docker Desktop

---

**הערה**: מדריך זה מותאם במיוחד למשתמשי Windows. למשתמשי Linux/Mac, השתמשו בקבצי `.sh` במקום `.bat`.
