#!/usr/bin/env python3
"""יצירת קובץ PDF לבדיקה"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def create_test_pdf():
    filename = "test_manual.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    
    # כותרת
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Test Manual - User Guide")
    
    # תוכן לבדיקה
    c.setFont("Helvetica", 12)
    content = [
        "This is a test manual for the PDF Q&A system.",
        "",
        "How to use the system:",
        "1. Upload a PDF file containing your manual or documentation",
        "2. Ask questions about the content",
        "3. Get AI-powered answers based on the document content",
        "",
        "Troubleshooting:",
        "- If upload fails, check file format (PDF only)",
        "- If answers are not relevant, try rephrasing your question",
        "- For technical support, contact the administrator",
        "",
        "FAQ:",
        "Q: What file formats are supported?",
        "A: Only PDF files are currently supported.",
        "",
        "Q: How large can the PDF be?",
        "A: Maximum file size is 10MB.",
        "",
        "Q: How accurate are the answers?",
        "A: The AI provides answers based on document content with high accuracy."
    ]
    
    y = 700
    for line in content:
        if line:  # רק אם השורה לא ריקה
            c.drawString(100, y, line)
        y -= 20
        if y < 100:  # עמוד חדש אם צריך
            c.showPage()
            y = 750
    
    c.save()
    print(f"Created {filename}")
    return filename

if __name__ == "__main__":
    try:
        from reportlab.pdfgen import canvas
        create_test_pdf()
    except ImportError:
        print("Installing reportlab...")
        os.system("pip install reportlab")
        from reportlab.pdfgen import canvas
        create_test_pdf()
