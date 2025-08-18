#!/usr/bin/env python3
"""
Test script for PDF Manual Q&A functionality
"""

import requests
import json
import os

# Server configuration
SERVER_URL = "http://localhost:8001"
TEST_PDF_PATH = "test_manual.pdf"  # This is the progit.pdf file

def test_upload_pdf():
    """Test uploading a PDF manual"""
    print("🔄 Testing PDF upload...")
    
    url = f"{SERVER_URL}/tools/upload_pdf_manual"
    
    # Check if test PDF exists
    if not os.path.exists(TEST_PDF_PATH):
        print(f"❌ Test PDF file not found: {TEST_PDF_PATH}")
        print("📝 Please create a test PDF file or update the path")
        return None
    
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': (TEST_PDF_PATH, f, 'application/pdf')}
            data = {
                'title': 'Pro Git Manual',
                'category': 'git_manual'
            }
        
        try:
            response = requests.post(url, files=files, data=data)
            result = response.json()
            
            if result['success']:
                print("✅ PDF uploaded successfully!")
                print(f"📄 Document ID: {result['data']['document_id']}")
                print(f"📊 Text length: {result['data']['text_length']} characters")
                return result['data']['document_id']
            else:
                print(f"❌ Upload failed: {result['error']}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

def test_ask_question():
    """Test asking questions about the PDF manual"""
    print("\n🔄 Testing PDF Q&A...")
    
    url = f"{SERVER_URL}/tools/ask_pdf_manual"
    
    questions = [
        "מה הם השלבים הראשונים להתקנה?",
        "איך אני פותר בעיות נפוצות?",
        "מה הדרישות המערכת?",
        "How do I reset the device?"
    ]
    
    for question in questions:
        print(f"\n❓ שאלה: {question}")
        
        data = {
            "question": question,
            "pdf_category": "git_manual",
            "limit": 2
        }
        
        try:
            response = requests.post(url, json=data)
            result = response.json()
            
            if result['success']:
                print("✅ תשובה התקבלה:")
                print(f"💬 {result['data']['answer']}")
                print(f"📚 מקורות: {len(result['data']['sources'])}")
                for source in result['data']['sources']:
                    print(f"   - {source['title']} (דמיון: {source['similarity']:.2f})")
            else:
                print(f"❌ שגיאה: {result['error']}")
                
        except Exception as e:
            print(f"❌ בקשה נכשלה: {e}")

def test_health_check():
    """Test server health"""
    print("🔄 Testing server health...")
    
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy!")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Make sure Docker containers are running (./start.sh)")
        return False

def main():
    print("🚀 Testing PDF Manual Q&A System")
    print("=" * 50)
    
    # Test server health first
    if not test_health_check():
        return
    
    # Test PDF upload
    doc_id = test_upload_pdf()
    
    # Test Q&A regardless of upload success (might have existing PDFs)
    test_ask_question()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\n💡 Tips:")
    print("   - Place a test PDF file at 'test_manual.pdf'")
    print("   - Make sure Docker containers are running")
    print("   - Check server logs for detailed error messages")

if __name__ == "__main__":
    main()
