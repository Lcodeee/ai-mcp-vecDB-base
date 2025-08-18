# PDF Q&A System - Architecture Overview

## תיאור המערכת
מערכת Q&A מתקדמת המאפשרת העלאת מסמכי PDF וביצוע שאלות על תוכנם באמצעות חיפוש סמנטי וינטיליגנציה מלאכותית.

## ארכיטקטורת המערכת

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │    │   MCP Server     │    │   PostgreSQL    │
│  (PDF Upload)   │───▶│   FastAPI        │───▶│   + pgvector    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Google Gemini  │
                       │   AI Model       │
                       └──────────────────┘
```

## זרימת העבודה המפורטת

### שלב 1: העלאת PDF והכנת הנתונים

#### 1.1 העלאת קובץ PDF
```http
POST /tools/upload_pdf_manual?title=Manual&category=appliance
Content-Type: multipart/form-data
```

#### 1.2 עיבוד הקובץ
1. **קריאת PDF**: PyPDF2 חולץ טקסט גולמי מכל עמוד
2. **ניקוי טקסט**: Regex מנקה:
   - הסרת מקפים מיותרים (`-{3,}`)
   - תיקון רווחים (`\s+`)
   - תיקון פיסוק ומספור
   - הסרת תווים בודדים (OCR artifacts)

#### 1.3 חלוקה לחתיכות (Chunking)
```python
def chunk_text(text: str, max_chars: int = 15000) -> List[str]:
    # חלוקה חכמה עם שמירה על גבולות משפטים
    # מקסימום 12,000 תווים לכל chunk (בפועל)
```

**אסטרטגיית החלוקה:**
- מקסימום 12,000 תווים לכל חלק
- חיפוש גבולות משפטים (נקודות)
- נסיגה לגבולות מילים אם נדרש
- חיתוך כפוי במקרה קיצון

#### 1.4 יצירת Embeddings
```python
# עבור כל chunk בנפרד:
embedding = await gemini_manager.generate_embedding(chunk_text)
# תוצאה: vector של 768 ממדים
```

#### 1.5 שמירה במסד הנתונים
```sql
INSERT INTO documents (content, embedding, metadata)
VALUES (chunk_content, embedding_vector, metadata_json)
```

**מבנה Metadata:**
```json
{
  "title": "Samsung Manual",
  "category": "appliance", 
  "type": "pdf_manual",
  "filename": "manual.pdf",
  "text_length": 11850,
  "chunk_index": 0,
  "total_chunks": 3
}
```

### שלב 2: שאילת שאלות וקבלת תשובות

#### 2.1 קבלת שאלה
```http
POST /tools/ask_pdf_manual
Content-Type: application/json

{
  "question": "how do I adjust the leveling feet",
  "pdf_category": "appliance",
  "limit": 3
}
```

#### 2.2 יצירת Embedding לשאלה
```python
query_embedding = await gemini_manager.generate_embedding(question)
# תוצאה: vector של 768 ממדים עבור השאלה
```

#### 2.3 חיפוש סמנטי ב-pgvector
```sql
SELECT id, content, metadata, 
       1 - (embedding <=> %s::vector) as similarity
FROM documents 
WHERE embedding IS NOT NULL 
AND metadata->>'type' = 'pdf_manual'
AND metadata->>'category' = %s
ORDER BY embedding <=> %s::vector
LIMIT %s
```

**אלגוריתם החיפוש:**
- **Cosine Distance**: `<=>` operator של pgvector
- **Similarity Score**: `1 - distance` (כך שגבוה יותר = דומה יותר)
- **סינון**: לפי קטגוריה ו-type
- **מיון**: לפי דמיון (הכי דומה ראשון)

#### 2.4 הכנת הקשר (Context)
```python
context_parts = []
for row in results:
    # שימוש בתוכן המלא של כל chunk - ללא חיתוך!
    full_content = row['content']
    context_parts.append(f"מתוך ספר הוראות '{title}' (חלק {chunk_index}): {full_content}")

context = "\n\n".join(context_parts)
```

#### 2.5 שליחה לגמיני לתשובה
```python
prompt = f"""
אתה עוזר תמיכה טכנית המבוסס על ספרי הוראות. ענה על השאלה בעברית בצורה ברורה ומדויקת.

הקשר מספרי ההוראות:
{context}

שאלת המשתמש: {question}

תן תשובה מקצועית ומועילת המבוססת על המידע מספרי ההוראות.
"""

answer = await gemini_manager.generate_response(prompt)
```

#### 2.6 החזרת תשובה מובנית
```json
{
  "success": true,
  "data": {
    "question": "how do I adjust the leveling feet",
    "answer": "כדי לכוון את רגליות הוויזון: 1. שחרר את ברגי הרגליות...",
    "sources": [
      {
        "document_id": 35,
        "title": "Samsung Manual", 
        "similarity": 0.6292
      }
    ],
    "context_used": 2
  }
}
```

## רכיבי המערכת

### 1. MCP Server (FastAPI)
- **פורט**: 8001
- **endpoints**: `/tools/upload_pdf_manual`, `/tools/ask_pdf_manual`
- **CORS**: מופעל לגישה מדפדפן

### 2. PostgreSQL + pgvector
- **פורט**: 5433
- **טבלה**: `documents`
- **אינדקס וקטורי**: `embedding` column with vector(768)

### 3. Google Gemini
- **Embedding Model**: `models/embedding-001`
- **Response Model**: `gemini-pro`
- **מגבלות**: 30K תווים לכל request

### 4. Docker Environment
```yaml
services:
  mcp_server:
    ports: "8001:8001"
  postgres:
    image: pgvector/pgvector:pg16
    ports: "5433:5432"
```

## תכונות מתקדמות

### חיפוש חכם
- **Vector Similarity**: חיפוש סמנטי לא רק לפי מילות מפתח
- **Multi-chunk Support**: שילוב מידע ממספר חלקים
- **Category Filtering**: חיפוש בקטגוריות ספציפיות

### טיפול בטקסט
- **Smart Chunking**: חלוקה שמשמרת הקשר
- **Text Cleaning**: ניקוי אוטומטי של פורמט PDF
- **Boundary Detection**: חיתוך בגבולות משפטים

### ביצועים
- **Async Processing**: עיבוד אסינכרוני עם asyncio
- **Connection Pooling**: ניהול חיבורי מסד נתונים
- **Error Handling**: טיפול מתקדם בשגיאות

## דוגמאות שימוש

### העלאת PDF
```bash
curl -X POST "http://localhost:8001/tools/upload_pdf_manual?title=Samsung%20Manual&category=appliance" \
     -F "file=@manual.pdf"
```

### שאילת שאלה
```bash
curl -X POST "http://localhost:8001/tools/ask_pdf_manual" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "how to clean the filter",
       "pdf_category": "appliance",
       "limit": 3
     }'
```

## מגבלות ושיקולים

1. **גודל קובץ**: עד 10MB לכל PDF
2. **זיכרון**: כל chunk עד 12K תווים
3. **API Limits**: מגבלות Gemini API
4. **שפה**: עדיפות לתשובות בעברית

## תיקונים שבוצעו

1. **Text Extraction**: שיפור חילוץ טקסט מ-PDF
2. **Chunking Algorithm**: תיקון חלוקה לגדלים נכונים  
3. **Content Delivery**: העברת תוכן מלא (לא חתוך) לGemini
4. **Search Quality**: שיפור איכות החיפוש הוקטורי

---

**מערכת זו מספקת פתרון מקצועי לחיפוש מידע במסמכי PDF באמצעות AI מתקדם וטכנולוגיות וקטוריות.**
