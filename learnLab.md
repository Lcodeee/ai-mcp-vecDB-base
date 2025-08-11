# 🎓 LearnLab: בניית מערכת AI עם Vector Database וMCP Server

## 📋 מטרת המדריך

מדריך זה ילמד אותך איך לבנות מערכת מתקדמת עם 3 containers שעובדים יחד:
- **PostgreSQL + pgvector** - מסד נתונים וקטורי
- **MCP Server** - שרת עם כלים מותאמים אישית
- **FastAPI App** - API שמתחבר לכל השירותים

## 🏗️ ארכיטקטורת המערכת

```
┌─────────────────┐    HTTP     ┌─────────────────┐    SQL      ┌─────────────────┐
│   Postman/User  │ ────────▶   │   FastAPI App   │ ─────────▶  │   PostgreSQL    │
│                 │             │   (Port 8000)   │             │   + pgvector    │
└─────────────────┘             └─────────────────┘             │   (Port 5433)   │
                                          │                     └─────────────────┘
                                          │ HTTP                          ▲
                                          ▼                               │
                                ┌─────────────────┐              SQL     │
                                │   MCP Server    │ ──────────────────────┘
                                │   (Port 8001)   │
                                └─────────────────┘
                                          │
                                          ▼ API Calls
                                ┌─────────────────┐
                                │   Gemini AI     │
                                │   (External)    │
                                └─────────────────┘
```

---

## 📁 שלב 1: מבנה התיקיות הבסיסי

### יצירת התיקיות

```bash
mkdir ai-mcp-vecDB-base
cd ai-mcp-vecDB-base
mkdir fastapi_app mcp_server postgres
```

**הסבר:**
- `fastapi_app/` - אפליקציית ה-API הראשית
- `mcp_server/` - שרת ה-MCP עם כלים מותאמים
- `postgres/` - קבצי הגדרה למסד הנתונים

---

## 🐳 שלב 2: Docker Compose - התזמור הראשי

### קובץ: `docker-compose.yml`

**מטרה:** מגדיר איך כל ה-containers עובדים יחד

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}  
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5433:5432"  # פורט חיצוני:פורט פנימי
    volumes:
      - postgres_data:/var/lib/postgresql/data  # שמירת נתונים
      - ./postgres/init.pgsql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - ai_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 5

  mcp_server:
    build:
      context: ./mcp_server
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy  # מחכה שPostgreSQL יהיה מוכן
    restart: unless-stopped

  fastapi_app:
    build:
      context: ./fastapi_app
      dockerfile: Dockerfile
    environment:
      MCP_SERVER_URL: http://mcp_server:8001
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - mcp_server  # מחכה לMCP Server
    restart: unless-stopped

volumes:
  postgres_data:  # אחסון קבוע לנתונים

networks:
  ai_network:  # רשת פרטית לתקשורת בין containers
    driver: bridge
```

**מרכיבים חשובים:**
- **Environment Variables:** משתנים שנקראים מקובץ `.env`
- **Health Checks:** בדיקות שהשירות עובד לפני הפעלת השירותים התלויים בו
- **Volumes:** שמירת נתונים גם אחרי כיבוי הcontainer
- **Networks:** רשת פרטית לתקשורת מהירה בין השירותים

---

## 🔐 שלב 3: קובץ הגדרות הסביבה

### קובץ: `.env.example`

**מטרה:** תבנית למשתני סביבה

```env
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration  
POSTGRES_DB=vectordb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

**הסבר:**
- משתני הסביבה נשמרים בקובץ נפרד לאבטחה
- `.env.example` הוא תבנית - המשתמש יוצר `.env` אמיתי
- Docker Compose קורא אוטומטית מקובץ `.env`

---

## 🗃️ שלב 4: מסד הנתונים עם pgvector

### קובץ: `postgres/init.pgsql`

**מטרה:** הגדרת מסד הנתונים עם יכולות חיפוש וקטורי

```sql
-- PostgreSQL Database Initialization with pgvector
-- File extension .pgsql ensures VS Code recognizes this as PostgreSQL syntax
--
-- Copyright 2025 Lcodeee
-- Licensed under the Apache License, Version 2.0

-- Initialize database with pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for storing documents with vectors
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(768),  -- וקטור של 768 מימדים
    metadata JSONB,         -- מטאדטה גמישה בפורמט JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create table for chat history
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255)
);

-- Insert some sample data
INSERT INTO documents (content, metadata) VALUES 
('PostgreSQL is a powerful, open source object-relational database system.', '{"type": "definition", "category": "database"}'),
('pgvector is an extension for PostgreSQL that adds vector similarity search capabilities.', '{"type": "definition", "category": "extension"}'),
('FastAPI is a modern, fast web framework for building APIs with Python.', '{"type": "definition", "category": "framework"}');
```

**מרכיבים חשובים:**
- **vector(768):** טיפוס נתונים מיוחד לאחסון embeddings
- **JSONB:** פורמט יעיל לאחסון מטאדטה גמישה
- **ivfflat index:** אינדקס מיועד לחיפוש מהיר בוקטורים
- **vector_cosine_ops:** אופרטור לחישוב דמיון קוסיני

---

## 🛠️ שלב 5: MCP Server - המוח של המערכת

### קובץ: `mcp_server/Dockerfile`

**מטרה:** הגדרת סביבת הרצה ל-MCP Server

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8001

CMD ["python", "server.py"]
```

### קובץ: `mcp_server/requirements.txt`

**מטרה:** רשימת החבילות הנדרשות

```txt
fastapi==0.104.1
uvicorn==0.24.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
google-generativeai==0.3.2
numpy==1.24.3
pydantic==2.0.0
python-dotenv==1.0.0
httpx==0.25.2
```

### קובץ: `mcp_server/server.py`

**מטרה:** השרת שמספק כלים לעבודה עם מסד הנתונים וה-AI

**מבנה עיקרי:**

1. **מחלקת DatabaseManager** - מנהלת את החיבור למסד הנתונים
2. **מחלקת GeminiManager** - מנהלת את האינטגרציה עם Gemini AI  
3. **כלי MCP (Tools)** - פונקציות מיוחדות שהמערכת מספקת

**כלים זמינים:**
- `vector_search` - חיפוש דמיון בוקטורים
- `add_document` - הוספת מסמך חדש עם embedding
- `chat_with_context` - שיחה עם AI באמצעות קונטקסט רלוונטי
- `get_chat_history` - קבלת היסטוריית שיחות

**איך זה עובד:**
1. משתמש שולח בקשה ל-FastAPI
2. FastAPI קוראת לכלי ב-MCP Server
3. MCP Server מחפש קונטקסט רלוונטי במסד הנתונים
4. שולח את השאלה + קונטקסט ל-Gemini AI
5. מחזיר תשובה משולבת

---

## 🚀 שלב 6: FastAPI App - הממשק הראשי

### קובץ: `fastapi_app/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

### קובץ: `fastapi_app/requirements.txt`

```txt
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
pydantic==2.5.0
python-dotenv==1.0.0
google-generativeai==0.3.2
```

### קובץ: `fastapi_app/main.py`

**מטרה:** ממשק HTTP שמחבר בין המשתמש לכל המערכת

**מרכיבים עיקריים:**

1. **MCPClient** - לקוח לתקשורת עם MCP Server
2. **GeminiManager** - ניהול ישיר של Gemini AI (כגיבוי)
3. **API Endpoints** - נקודות קצה שמשתמשים יכולים לקרוא להן

**Endpoints עיקריים:**
- `POST /process` - עיבוד הודעה עם/בלי חיפוש וקטורי
- `POST /search` - חיפוש ישיר במסד הנתונים הוקטורי  
- `POST /add_document` - הוספת מסמך חדש
- `GET /chat_history` - קבלת היסטוריית שיחות
- `POST /gemini_direct` - שיחה ישירה עם Gemini ללא קונטקסט

---

## 🧪 שלב 7: בדיקות ותיקוף

### קובץ: `test_api.py`

**מטרה:** וידוא שכל המערכת עובדת כמו שצריך

**בדיקות שמתבצעות:**
1. **Health Check** - כל השירותים פעילים?
2. **Vector Search** - חיפוש בוקטורים עובד?
3. **Document Addition** - הוספת מסמכים עובדת?
4. **AI Chat** - התשובות מGemini הגיוניות?
5. **History** - שמירת היסטוריה עובדת?

**מדוע הבדיקות האלה טובות:**
- **כיסוי מלא:** בודקות כל רכיב במערכת
- **אינטגרציה:** בודקות שהרכיבים עובדים יחד
- **נתונים אמיתיים:** משתמשות בנתונים דומים לשימוש אמיתי
- **שגיאות:** מזהות בעיות לפני שמשתמשים נתקלים בהן

### סקריפטי עזר

**`start.sh`** - הפעלת המערכת:
```bash
#!/bin/bash
# בדיקת קובץ .env
# הפעלת כל השירותים
# המתנה שהכל יהיה מוכן
# בדיקת בריאות השירותים
```

**`stop.sh`** - כיבוי המערכת:
```bash
#!/bin/bash
docker-compose down
```

---

## 🎯 איך להריץ את המערכת

### שלב 1: הכנה

```bash
# 1. העתקת תבנית משתני הסביבה
cp .env.example .env

# 2. עריכת הקובץ והוספת המפתחות
nano .env  # או עורך אחר

# 3. הוספת מפתח Gemini API
GEMINI_API_KEY=your_actual_api_key_here
```

### שלב 2: הפעלה

```bash
# הפעלת המערכת
./start.sh

# או ידנית:
docker-compose up --build
```

### שלב 3: בדיקה

```bash
# הרצת הטסטים
python test_api.py

# בדיקה ידנית
curl http://localhost:8000/health
```

---

## 🧪 הרצת בדיקות מפורטת

### 1. בדיקה עם הסקריפט

```bash
python test_api.py
```

**מה הסקריפט בודק:**
- ✅ שכל השירותים פעילים (health check)
- ✅ שחיפוש וקטורי מחזיר תוצאות רלוונטיות  
- ✅ שהוספת מסמכים עובדת ומחזירה ID
- ✅ שהתשובות מ-AI הגיוניות ולא שגיאות
- ✅ שהיסטוריית השיחות נשמרת נכון

### 2. בדיקה עם Postman

```bash
# ייבוא הקולקציה
postman_collection.json

# בדיקת endpoints:
POST http://localhost:8000/process
POST http://localhost:8000/search  
POST http://localhost:8000/add_document
GET  http://localhost:8000/chat_history
```

### 3. בדיקה ידנית עם curl

```bash
# בדיקת בריאות
curl http://localhost:8000/health

# שליחת הודעה לעיבוד
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{"message": "מה זה PostgreSQL?", "use_vector_search": true}'
```

---

## 📊 מדוע הבדיקות האלה יעילות

### 1. **בדיקת Integration מלאה**
- בודק שכל השירותים מתחברים נכון
- וודא שנתונים זורמים בין הרכיבים

### 2. **בדיקת Real-world Scenarios**
- שימוש בשאלות אמיתיות שמשתמשים ישאלו
- בדיקת תרחישים שונים (עם/בלי vector search)

### 3. **בדיקת Error Handling**
- מה קורה כשאין חיבור לGemini?
- מה קורה כשמסד הנתונים לא זמין?

### 4. **בדיקת Performance**
- זמני תגובה סבירים?
- האם המערכת יציבה תחת עומס?

---

## 🎓 משימות לתלמיד

### משימה 1: יצירת כלי חדש ב-MCP Server

**מטרה:** ליצור כלי שמחפש מסמכים לפי קטגוריה

**שלבים:**
1. פתח את `mcp_server/server.py`
2. הוסף פונקציה חדשה:

```python
@app.post("/tools/search_by_category", response_model=MCPResponse)
async def search_by_category(category: str, limit: int = 5):
    """חפש מסמכים לפי קטגוריה במטאדטה"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, content, metadata, created_at
                    FROM documents 
                    WHERE metadata->>'category' = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (category, limit))
                
                results = cur.fetchall()
                
        return MCPResponse(
            success=True,
            data={
                "category": category,
                "results": [dict(row) for row in results],
                "count": len(results)
            }
        )
    except Exception as e:
        logger.error(f"Category search failed: {e}")
        return MCPResponse(success=False, error=str(e))
```

3. הוסף את הכלי לרשימה ב-`list_tools()`

**בדיקה:**
```bash
curl -X POST "http://localhost:8001/tools/search_by_category" \
     -H "Content-Type: application/json" \
     -d '{"category": "database", "limit": 3}'
```

### משימה 2: הוספת Endpoint ב-FastAPI

**מטרה:** ליצור endpoint שמשתמש בכלי החדש

**שלבים:**
1. פתח את `fastapi_app/main.py`
2. הוסף Pydantic model:

```python
class CategorySearchRequest(BaseModel):
    category: str
    limit: int = 5
```

3. הוסף endpoint חדש:

```python
@app.post("/search_category", response_model=APIResponse)
async def search_by_category(request: CategorySearchRequest):
    """חפש מסמכים לפי קטגוריה"""
    try:
        result = await mcp_client.call_tool("search_by_category", {
            "category": request.category,
            "limit": request.limit
        })
        
        return APIResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            source="mcp_server"
        )
    except Exception as e:
        logger.error(f"Category search failed: {e}")
        return APIResponse(success=False, error=str(e))
```

**בדיקה:**
```bash
curl -X POST "http://localhost:8000/search_category" \
     -H "Content-Type: application/json" \
     -d '{"category": "database", "limit": 3}'
```

### משימה 3: הוספת בדיקה לטסט

**מטרה:** להוסיף בדיקה של הכלי החדש ל-`test_api.py`

**שלבים:**
1. פתח את `test_api.py`
2. הוסף בדיקה חדשה:

```python
# Test category search
print("9. Testing category search...")
try:
    category_data = {
        "category": "database",
        "limit": 3
    }
    response = await client.post(f"{BASE_URL}/search_category", json=category_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result['success']}")
        if result['success']:
            results = result['data']['results']
            print(f"   Found {len(results)} documents in category")
        print("   ✓ Category search passed\n")
except Exception as e:
    print(f"   ✗ Category search failed: {e}\n")
    all_tests_passed = False
```

### משימה 4: תיעוד השינויים

**עדכן את הקבצים הבאים:**
1. `README.md` - הוסף תיאור של הכלי החדש
2. `postman_collection.json` - הוסף request לכלי החדש
3. `DEVELOPMENT.md` - הוסף הסבר איך ליצור כלים נוספים

---

## 🎯 טיפים לפיתוח נוסף

### 1. **הוספת כלים נוספים**
- כלי לעדכון מסמכים קיימים
- כלי למחיקת מסמכים
- כלי לסטטיסטיקות על מסד הנתונים

### 2. **שיפור החיפוש הוקטורי**
- שימוש במודל embeddings טוב יותר
- הוספת פילטרים לחיפוש
- שיפור אלגוריתם הדירוג

### 3. **הוספת תכונות אבטחה**
- אימות משתמשים
- הגבלת קצב בקשות (rate limiting)
- הצפנת נתונים רגישים

### 4. **ניטור ו-Logging**
- לוגים מפורטים יותר
- מטריקות ביצועים
- התראות על שגיאות

---

## 🏁 סיכום

בניית המערכת הזאת לימדה אותך:

1. **ארכיטקטורת Microservices** - איך שירותים שונים עובדים יחד
2. **Vector Databases** - איך לאחסן ולחפש מידע בצורה חכמה
3. **AI Integration** - איך לשלב בינה מלאכותית באפליקציה
4. **Docker & Orchestration** - איך לנהל מערכות מורכבות
5. **API Design** - איך לתכנן ממשקים נקיים ויעילים
6. **Testing Strategy** - איך לוודא שהמערכת עובדת כמו שצריך

המערכת הזאת יכולה לשמש בסיס לפרויקטים מתקדמים כמו:
- מערכות שאלות ותשובות חכמות
- מנועי חיפוש מתקדמים
- אסיסטנטים וירטואליים
- מערכות המלצות

המשך לנסות, לשפר ולהוסיף תכונות חדשות! 🚀
