# PDF Manual Q&A Tool

## תיאור הכלי
כלי לשאלות ותשובות על בסיס ספרי הוראות בפורמט PDF. הכלי מאפשר:
- העלאת קבצי PDF (ספרי הוראות)
- המרת הטקסט מה-PDF לפורמט טקסט רגיל
- יצירת embedding וקטורי לחיפוש סמנטי
- שאילת שאלות וקבלת תשובות מבוססות AI על בסיס תוכן המסמכים

## קבצים שנוספו
- `mcp_server/server.py` - הוספת endpoints חדשים:
  - `POST /tools/upload_pdf_manual` - העלאת PDF
  - `POST /tools/ask_pdf_manual` - שאילת שאלות
- `test_pdf_manual.py` - סקריפט טסט
- `pdf_manual_frontend.html` - ממשק משתמש פשוט
- `PDF_MANUAL_README.md` - הוראות זה

## הוראות הרצה

### 1. הכנה
```bash
# וודא שהקונטיינרים רצים
./start.sh

# התקן PyPDF2 (אם לא מותקן)
pip install PyPDF2
```

### 2. בדיקת הכלי
```bash
# הרץ טסט בסיסי
python test_pdf_manual.py

# או בדוק את ה-API documentation
# פתח בדפדפן: http://localhost:8001/docs
```

### 3. שימוש בממשק הגרפי
```bash
# פתח את הקובץ בדפדפן
open pdf_manual_frontend.html
# או גרור את הקובץ לדפדפן
```

### 4. שימוש ב-API ישירות

#### העלאת PDF:
```bash
curl -X POST "http://localhost:8001/tools/upload_pdf_manual" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_manual.pdf" \
  -F "title=Product Manual" \
  -F "category=support"
```

#### שאילת שאלה:
```bash
curl -X POST "http://localhost:8001/tools/ask_pdf_manual" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "איך מתקינים את המוצר?",
    "pdf_category": "support",
    "limit": 3
  }'
```

## דוגמאות שימוש

### עבור תמיכה טכנית:
1. העלה ספר הוראות של מוצר
2. תומכי הטלפון שואלים: "לקוח שואל איך לאפס את המכשיר"
3. המערכת מחזירה תשובה מבוססת על ספר ההוראות

### עבור אתר ממשלתי:
1. העלה מדריכי שירות ממשלתיים
2. אזרחים שואלים שאלות על השירות
3. קבלת תשובות אוטומטיות מבוססות על המדריכים

## טיפים לשימוש מיטבי
- השתמש בקבצי PDF עם טקסט ברור (לא סרוק)
- תן כותרות ברורות למסמכים
- השתמש בקטגוריות לארגון טוב יותר
- שאל שאלות ברורות ומפורטות

## פתרון בעיות נפוצות
- **שגיאת חיבור**: וודא שהקונטיינרים רצים (`./start.sh`)
- **PDF לא נקרא**: וודא שהקובץ מכיל טקסט ולא רק תמונות
- **תשובות לא רלוונטיות**: נסה לנסח את השאלה בצורה יותר ספציפית
