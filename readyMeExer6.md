# Exercise 6: PDF Manual Q&A Assistant Implementation Guide

## Overview
This guide provides a step-by-step implementation of a PDF Manual Q&A Assistant tool that integrates with the existing MCP/AI system. The tool allows support agents to upload PDF instruction manuals and answer customer questions based on the manual content using AI-powered semantic search.

## Prerequisites
- Starting from the initial commit of `next-class-adding-tools` branch
- Docker and Docker Compose installed
- Python 3.9+ with required dependencies
- PostgreSQL with pgvector extension
- Google Gemini AI API access

## Architecture Overview
The implementation adds two main endpoints to the MCP server:
1. `POST /tools/upload_pdf_manual` - Upload and process PDF files
2. `POST /tools/ask_pdf_manual` - Query the processed PDF content

## Step-by-Step Implementation

### Step 1: Add Required Dependencies

First, update the `requirements.txt` file in the `mcp_server` directory:

```bash
# Add to mcp_server/requirements.txt
PyPDF2==3.0.1
python-multipart==0.0.6
```

**Why these dependencies?**
- `PyPDF2`: For extracting text content from PDF files
- `python-multipart`: Required by FastAPI for handling file uploads

### Step 2: Define Data Models

Add the following Pydantic models to `server.py`:

```python
# Add after existing imports
from fastapi import File, UploadFile
import PyPDF2
import io

# Add after existing Pydantic models
class PDFQuestionRequest(BaseModel):
    question: str
    pdf_category: Optional[str] = None
    limit: int = 5
```

### Step 3: Implement PDF Text Extraction

Add the PDF text extraction method to the `GeminiManager` class:

```python
# Add to GeminiManager class in server.py
async def extract_text_from_pdf(self, pdf_content: bytes) -> str:
    """Extract text content from PDF bytes"""
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_content = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(f"Page {page_num + 1}:\n{page_text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                continue
        
        if not text_content:
            return "Error: No readable text found in PDF"
        
        return "\n\n".join(text_content)
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return f"Error extracting PDF text: {str(e)}"
```

### Step 4: Implement PDF Upload Endpoint

Add the upload endpoint to `server.py`:

```python
@app.post("/tools/upload_pdf_manual", response_model=MCPResponse)
async def upload_pdf_manual(title: str, category: str = "manual", file: UploadFile = File(...)):
    """Upload PDF instruction manual and process it for Q&A"""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read PDF content
        pdf_content = await file.read()
        
        # Extract text from PDF
        extracted_text = await gemini_manager.extract_text_from_pdf(pdf_content)
        
        if extracted_text.startswith("Error"):
            raise HTTPException(status_code=400, detail=extracted_text)
        
        # Generate embedding for the entire PDF content
        embedding = await gemini_manager.generate_embedding(extracted_text)
        
        # Store in database
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    metadata = {
                        "type": "pdf_manual",
                        "title": title,
                        "category": category,
                        "filename": file.filename,
                        "upload_date": datetime.now().isoformat()
                    }
                    cur.execute("""
                        INSERT INTO documents (content, embedding, metadata) 
                        VALUES (%s, %s::vector, %s)
                        RETURNING id
                    """, (extracted_text, str(embedding), json.dumps(metadata)))
                    doc_id = cur.fetchone()['id']
                    conn.commit()
                    return doc_id

        doc_id = await asyncio.to_thread(_db_op)

        return MCPResponse(
            success=True,
            data={
                "document_id": doc_id,
                "title": title,
                "category": category,
                "filename": file.filename,
                "text_length": len(extracted_text),
                "message": "PDF manual uploaded and processed successfully"
            }
        )
    except Exception as e:
        logger.error(f"PDF upload failed: {e}")
        return MCPResponse(success=False, error=str(e))
```

### Step 5: Implement Q&A Query Endpoint

Add the query endpoint to `server.py`:

```python
@app.post("/tools/ask_pdf_manual", response_model=MCPResponse)
async def ask_pdf_manual(request: PDFQuestionRequest):
    """Ask questions about PDF manuals"""
    try:
        # Search for relevant manual content
        query_embedding = await gemini_manager.generate_embedding(request.question)
        
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    if request.pdf_category:
                        cur.execute("""
                            SELECT id, content, metadata, 
                                   1 - (embedding <=> %s::vector) as similarity
                            FROM documents 
                            WHERE embedding IS NOT NULL 
                            AND metadata->>'type' = 'pdf_manual'
                            AND metadata->>'category' = %s
                            ORDER BY embedding <=> %s::vector
                            LIMIT %s
                        """, (str(query_embedding), request.pdf_category, str(query_embedding), request.limit))
                    else:
                        cur.execute("""
                            SELECT id, content, metadata, 
                                   1 - (embedding <=> %s::vector) as similarity
                            FROM documents 
                            WHERE embedding IS NOT NULL 
                            AND metadata->>'type' = 'pdf_manual'
                            ORDER BY embedding <=> %s::vector
                            LIMIT %s
                        """, (str(query_embedding), str(query_embedding), request.limit))
                    return cur.fetchall()

        results = await asyncio.to_thread(_db_op)
        
        if not results:
            return MCPResponse(
                success=True,
                data={
                    "question": request.question,
                    "answer": "לא נמצאו ספרי הוראות רלוונטיים למענה על השאלה.",
                    "sources": []
                }
            )
        
        # Build context from relevant manual sections
        context_parts = []
        sources = []
        for row in results:
            context_parts.append(f"מתוך ספר הוראות '{row['metadata']['title']}': {row['content'][:500]}...")
            # Handle potential NaN or infinity values
            similarity = row.get('similarity', 0.0)
            if not isinstance(similarity, (int, float)) or similarity != similarity or similarity == float('inf') or similarity == float('-inf'):
                similarity = 0.0
            sources.append({
                "document_id": row['id'],
                "title": row['metadata']['title'],
                "similarity": round(float(similarity), 4)
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using Gemini
        prompt = f"""
        אתה עוזר תמיכה טכנית המבוסס על ספרי הוראות. ענה על השאלה בעברית בצורה ברורה ומדויקת.
        
        הקשר מספרי ההוראות:
        {context}
        
        שאלת המשתמש: {request.question}
        
        תן תשובה מקצועית ומועילה המבוססת על המידע מספרי ההוראות. אם המידע לא מספיק, ציין זאת.
        """
        
        answer = await gemini_manager.generate_response(prompt)
        
        return MCPResponse(
            success=True,
            data={
                "question": request.question,
                "answer": answer,
                "sources": sources,
                "context_used": len(results)
            }
        )
    except Exception as e:
        logger.error(f"PDF Q&A failed: {e}")
        return MCPResponse(success=False, error=str(e))
```

### Step 6: Update Tools List

Add the new tools to the tools list in the `/tools` endpoint:

```python
# Add to the tools list in get_tools() function
{
    "name": "upload_pdf_manual",
    "description": "Upload PDF instruction manual for Q&A system",
    "inputSchema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Manual title"},
            "category": {"type": "string", "description": "Manual category", "default": "manual"},
            "file": {"type": "string", "format": "binary", "description": "PDF file to upload"}
        },
        "required": ["title", "file"]
    }
},
{
    "name": "ask_pdf_manual",
    "description": "Ask questions about uploaded PDF manuals",
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question about the manual"},
            "pdf_category": {"type": "string", "description": "Optional: filter by category"},
            "limit": {"type": "integer", "description": "Max results", "default": 5}
        },
        "required": ["question"]
    }
}
```

### Step 7: Build and Deploy

Update Docker containers with new dependencies:

```bash
# Stop containers
docker-compose down

# Rebuild with new dependencies
docker-compose build --no-cache mcp_server

# Start all services
docker-compose up -d

# Wait for containers to be ready (about 180 seconds)
sleep 180
```

### Step 8: Create Test Script

Create `test_pdf_manual.py` for testing:

```python
#!/usr/bin/env python3
import requests
import json
import os

SERVER_URL = "http://localhost:8001"
TEST_PDF = "test_manual.pdf"

def test_server_health():
    """Test if server is running"""
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy!")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return False

def test_pdf_upload():
    """Test PDF upload functionality"""
    if not os.path.exists(TEST_PDF):
        print(f"❌ Test PDF file '{TEST_PDF}' not found")
        return False
    
    try:
        with open(TEST_PDF, 'rb') as f:
            files = {'file': f}
            data = {
                'title': 'Test Manual',
                'category': 'manual'
            }
            
            response = requests.post(
                f"{SERVER_URL}/tools/upload_pdf_manual",
                params=data,
                files=files
            )
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ PDF uploaded successfully! Document ID: {result['data']['document_id']}")
            return True
        else:
            print(f"❌ PDF upload failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ PDF upload error: {e}")
        return False

def test_pdf_qa():
    """Test PDF Q&A functionality"""
    questions = [
        "מה הם השלבים הראשונים להתקנה?",
        "איך אני פותר בעיות נפוצות?",
        "מה הדרישות המערכת?",
        "How do I reset the device?"
    ]
    
    for question in questions:
        try:
            response = requests.post(
                f"{SERVER_URL}/tools/ask_pdf_manual",
                json={"question": question},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n❓ שאלה: {question}")
                print("✅ תשובה התקבלה:")
                print(f"💬 {result['data']['answer']}")
                print(f"📚 מקורות: {len(result['data']['sources'])}")
            else:
                print(f"❌ Q&A failed for '{question}': {response.status_code}")
        except Exception as e:
            print(f"❌ Q&A error for '{question}': {e}")

def main():
    print("🚀 Testing PDF Manual Q&A System")
    print("=" * 50)
    
    print("🔄 Testing server health...")
    if not test_server_health():
        return
    
    print("🔄 Testing PDF upload...")
    test_pdf_upload()
    
    print("\n🔄 Testing PDF Q&A...")
    test_pdf_qa()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
```

### Step 9: Create Frontend Interface

Create `pdf_manual_frontend.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Manual Q&A Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .upload-section, .qa-section {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        input, button, textarea {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            background-color: #007bff;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .result {
            margin-top: 15px;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 PDF Manual Q&A Assistant</h1>
        
        <div class="upload-section">
            <h2>📤 Upload PDF Manual</h2>
            <input type="text" id="title" placeholder="Manual Title (e.g., 'User Guide v1.0')" required>
            <input type="text" id="category" placeholder="Category (e.g., 'manual', 'guide')" value="manual">
            <input type="file" id="pdfFile" accept=".pdf" required>
            <button onclick="uploadPDF()">Upload PDF</button>
            <div id="uploadResult"></div>
        </div>
        
        <div class="qa-section">
            <h2>❓ Ask Questions</h2>
            <textarea id="question" placeholder="Ask your question about the uploaded manuals..." rows="3"></textarea>
            <input type="text" id="qaCategory" placeholder="Filter by category (optional)">
            <button onclick="askQuestion()">Ask Question</button>
            <div id="qaResult"></div>
        </div>
    </div>

    <script>
        const SERVER_URL = 'http://localhost:8001';

        async function uploadPDF() {
            const title = document.getElementById('title').value;
            const category = document.getElementById('category').value;
            const fileInput = document.getElementById('pdfFile');
            const resultDiv = document.getElementById('uploadResult');

            if (!title || !fileInput.files[0]) {
                resultDiv.innerHTML = '<div class="error">Please provide title and select a PDF file</div>';
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const response = await fetch(`${SERVER_URL}/tools/upload_pdf_manual?title=${encodeURIComponent(title)}&category=${encodeURIComponent(category)}`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok && result.success) {
                    resultDiv.innerHTML = `<div class="success">✅ PDF uploaded successfully!<br>Document ID: ${result.data.document_id}<br>File: ${result.data.filename}<br>Text Length: ${result.data.text_length} characters</div>`;
                    // Clear form
                    document.getElementById('title').value = '';
                    document.getElementById('category').value = 'manual';
                    fileInput.value = '';
                } else {
                    resultDiv.innerHTML = `<div class="error">❌ Upload failed: ${result.error || 'Unknown error'}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="error">❌ Upload error: ${error.message}</div>`;
            }
        }

        async function askQuestion() {
            const question = document.getElementById('question').value;
            const category = document.getElementById('qaCategory').value;
            const resultDiv = document.getElementById('qaResult');

            if (!question.trim()) {
                resultDiv.innerHTML = '<div class="error">Please enter a question</div>';
                return;
            }

            try {
                const requestBody = {
                    question: question,
                    limit: 5
                };
                
                if (category) {
                    requestBody.pdf_category = category;
                }

                const response = await fetch(`${SERVER_URL}/tools/ask_pdf_manual`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody)
                });

                const result = await response.json();
                
                if (response.ok && result.success) {
                    let sourcesHtml = '';
                    if (result.data.sources && result.data.sources.length > 0) {
                        sourcesHtml = '<br><br><strong>📚 Sources:</strong><br>';
                        result.data.sources.forEach((source, index) => {
                            sourcesHtml += `${index + 1}. ${source.title} (Similarity: ${source.similarity})<br>`;
                        });
                    }
                    
                    resultDiv.innerHTML = `<div class="success">
                        <strong>❓ Question:</strong> ${result.data.question}<br><br>
                        <strong>💬 Answer:</strong><br>${result.data.answer}${sourcesHtml}
                    </div>`;
                } else {
                    resultDiv.innerHTML = `<div class="error">❌ Q&A failed: ${result.error || 'Unknown error'}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="error">❌ Q&A error: ${error.message}</div>`;
            }
        }

        // Allow Enter key to submit question
        document.getElementById('question').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                askQuestion();
            }
        });
    </script>
</body>
</html>
```

## Testing the Implementation

### Test 1: Upload a PDF
```bash
curl -X POST "http://localhost:8001/tools/upload_pdf_manual?title=Test%20Manual&category=manual" -F "file=@test_manual.pdf"
```

### Test 2: Ask Questions
```bash
curl -X POST -H "Content-Type: application/json" -d '{"question": "What is Git?"}' http://localhost:8001/tools/ask_pdf_manual
```

### Test 3: Use Frontend
Open `pdf_manual_frontend.html` in your browser and test the interface.

## Common Issues and Solutions

### Issue 1: Missing Dependencies
**Problem**: `ModuleNotFoundError: No module named 'PyPDF2'`
**Solution**: Ensure `PyPDF2==3.0.1` and `python-multipart==0.0.6` are in requirements.txt and rebuild containers.

### Issue 2: JSON Serialization Error
**Problem**: `ValueError: Out of range float values are not JSON compliant`
**Solution**: Handle NaN/infinity values in similarity scores (implemented in Step 5).

### Issue 3: File Upload Format Error
**Problem**: Query parameters not recognized
**Solution**: Use correct curl format with title and category as query parameters.

### Issue 4: Container Startup Issues
**Problem**: Containers failing to start
**Solution**: Wait 180 seconds after `docker-compose up -d` for full initialization.

## File Structure
```
new-ai-advanced-app/
├── mcp_server/
│   ├── server.py (modified)
│   └── requirements.txt (modified)
├── test_pdf_manual.py (new)
├── pdf_manual_frontend.html (new)
├── readyMeExer6.md (this file)
└── test_manual.pdf (sample PDF for testing)
```

## Key Features Implemented

1. **PDF Text Extraction**: Uses PyPDF2 to extract text from uploaded PDFs
2. **Semantic Search**: Generates embeddings and uses cosine similarity for relevant content retrieval
3. **AI-Powered Q&A**: Uses Gemini AI to generate context-aware answers
4. **Category Filtering**: Allows filtering manuals by category
5. **Web Interface**: Simple HTML/JavaScript frontend for easy testing
6. **Error Handling**: Comprehensive error handling for various edge cases
7. **Database Integration**: Stores PDF content with metadata in PostgreSQL with pgvector

## Performance Considerations

- PDF processing is done asynchronously to avoid blocking
- Database operations use connection pooling
- Text extraction is limited to readable content only
- Similarity scores are rounded to prevent JSON serialization issues
- Context is truncated to 500 characters per source to manage prompt size

This implementation provides a robust foundation for a PDF-based Q&A system that can be extended with additional features like multi-language support, advanced PDF parsing, or integration with other document types.
