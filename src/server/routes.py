from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from typing import Optional
import base64
from src.server.schemas import ChatRequest, ChatResponse, LegalCitation
from src.graph.workflow import app_graph
from src.logger import logger

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Endpoint chính để xử lý câu hỏi pháp lý với tài liệu (nếu có)
    """
    inputs = {
        "question": req.question,
        "generation": "",  # Initialize empty
        "documents": [],  # Initialize empty
        "retrieve": "",  # Initialize empty
        "loop_step": 0,
        "no_relevant_count": 0,
        "image_base64": req.image_base64,
        "document_context": req.document_context,
        "citations": [],
        "contradictions": None
    }
    
    logger.info(f"Nhận câu hỏi: {req.question[:100]}...")
    if req.image_base64:
        logger.info("Có ảnh đính kèm")
    if req.document_context:
        logger.info("Có document context")
    
    # Invoke Graph
    result = await app_graph.ainvoke(inputs)
    
    # Chuyển đổi citations từ dict sang LegalCitation objects
    citations = [
        LegalCitation(**citation) if isinstance(citation, dict) else citation
        for citation in result.get("citations", [])
    ]
    
    return ChatResponse(
        answer=result.get("generation", "Không thể tạo câu trả lời"),
        citations=citations,
        document_context=result.get("document_context"),
        contradictions=result.get("contradictions")
    )


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_with_upload(
    question: str = Form(...),
    image: UploadFile = File(...)
):
    """
    Endpoint để upload ảnh và hỏi đáp
    Hỗ trợ upload file ảnh trực tiếp
    """
    # Đọc và encode ảnh
    image_bytes = await image.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    req = ChatRequest(
        question=question,
        image_base64=image_base64
    )
    
    return await chat_endpoint(req)


@router.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """
    Trả về trang demo HTML
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Legal DocVQA - Demo</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            
            .header p {
                font-size: 1.1em;
                opacity: 0.9;
            }
            
            .content {
                padding: 40px;
            }
            
            .upload-section {
                margin-bottom: 30px;
                padding: 30px;
                background: #f8f9fa;
                border-radius: 15px;
                border: 2px dashed #667eea;
            }
            
            .upload-section h2 {
                color: #333;
                margin-bottom: 20px;
                font-size: 1.5em;
            }
            
            .file-input-wrapper {
                position: relative;
                display: inline-block;
                width: 100%;
            }
            
            .file-input-wrapper input[type=file] {
                position: absolute;
                opacity: 0;
                width: 100%;
                height: 100%;
                cursor: pointer;
            }
            
            .file-input-label {
                display: block;
                padding: 20px;
                background: white;
                border: 2px solid #667eea;
                border-radius: 10px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .file-input-label:hover {
                background: #667eea;
                color: white;
            }
            
            .preview-image {
                max-width: 100%;
                max-height: 400px;
                margin-top: 20px;
                border-radius: 10px;
                display: none;
            }
            
            .question-section {
                margin-bottom: 30px;
            }
            
            .question-section h2 {
                color: #333;
                margin-bottom: 15px;
                font-size: 1.5em;
            }
            
            .question-input {
                width: 100%;
                padding: 15px;
                font-size: 1.1em;
                border: 2px solid #ddd;
                border-radius: 10px;
                resize: vertical;
                min-height: 100px;
                font-family: inherit;
            }
            
            .question-input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .submit-btn {
                width: 100%;
                padding: 15px;
                font-size: 1.2em;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: transform 0.2s;
                font-weight: bold;
            }
            
            .submit-btn:hover {
                transform: translateY(-2px);
            }
            
            .submit-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .result-section {
                margin-top: 30px;
                padding: 30px;
                background: #f8f9fa;
                border-radius: 15px;
                display: none;
            }
            
            .result-section h2 {
                color: #333;
                margin-bottom: 20px;
                font-size: 1.5em;
            }
            
            .answer-box {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                line-height: 1.8;
                font-size: 1.1em;
            }
            
            .citations-box {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            
            .citations-box h3 {
                color: #667eea;
                margin-bottom: 15px;
            }
            
            .citation-item {
                padding: 15px;
                margin-bottom: 10px;
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                border-radius: 5px;
            }
            
            .contradictions-box {
                background: #fff3cd;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #ffc107;
            }
            
            .contradictions-box h3 {
                color: #856404;
                margin-bottom: 15px;
            }
            
            .loading {
                text-align: center;
                padding: 20px;
                display: none;
            }
            
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚖️ Legal DocVQA System</h1>
                <p>Hệ thống hỏi đáp tài liệu pháp lý thông minh</p>
            </div>
            
            <div class="content">
                <form id="chatForm">
                    <div class="upload-section">
                        <h2>📄 Upload Tài Liệu</h2>
                        <div class="file-input-wrapper">
                            <input type="file" id="imageInput" accept="image/*">
                            <label for="imageInput" class="file-input-label">
                                📎 Chọn ảnh tài liệu (JPG, PNG, ...)
                            </label>
                        </div>
                        <img id="imagePreview" class="preview-image" alt="Preview">
                    </div>
                    
                    <div class="question-section">
                        <h2>❓ Câu Hỏi Của Bạn</h2>
                        <textarea 
                            id="questionInput" 
                            class="question-input" 
                            placeholder="Nhập câu hỏi về tài liệu pháp lý của bạn..."
                            required
                        ></textarea>
                    </div>
                    
                    <button type="submit" class="submit-btn" id="submitBtn">
                        🚀 Gửi Câu Hỏi
                    </button>
                </form>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 15px;">Đang xử lý...</p>
                </div>
                
                <div class="result-section" id="resultSection">
                    <h2>📋 Kết Quả</h2>
                    <div class="answer-box" id="answerBox"></div>
                    
                    <div class="citations-box" id="citationsBox" style="display: none;">
                        <h3>📚 Điều Luật Được Trích Dẫn</h3>
                        <div id="citationsList"></div>
                    </div>
                    
                    <div class="contradictions-box" id="contradictionsBox" style="display: none;">
                        <h3>⚠️ Điểm Mâu Thuẫn Phát Hiện</h3>
                        <ul id="contradictionsList"></ul>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const imageInput = document.getElementById('imageInput');
            const imagePreview = document.getElementById('imagePreview');
            const chatForm = document.getElementById('chatForm');
            const questionInput = document.getElementById('questionInput');
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const resultSection = document.getElementById('resultSection');
            const answerBox = document.getElementById('answerBox');
            const citationsBox = document.getElementById('citationsBox');
            const citationsList = document.getElementById('citationsList');
            const contradictionsBox = document.getElementById('contradictionsBox');
            const contradictionsList = document.getElementById('contradictionsList');
            
            let imageBase64 = null;
            
            imageInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        imageBase64 = e.target.result.split(',')[1];
                        imagePreview.src = e.target.result;
                        imagePreview.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                }
            });
            
            chatForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const question = questionInput.value.trim();
                if (!question) {
                    alert('Vui lòng nhập câu hỏi!');
                    return;
                }
                
                // Show loading
                submitBtn.disabled = true;
                loading.style.display = 'block';
                resultSection.style.display = 'none';
                
                try {
                    const payload = {
                        question: question
                    };
                    
                    if (imageBase64) {
                        payload.image_base64 = imageBase64;
                    }
                    
                    const response = await fetch('/api/v1/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                    
                    if (!response.ok) {
                        throw new Error('Lỗi khi gửi yêu cầu');
                    }
                    
                    const data = await response.json();
                    
                    // Display answer
                    answerBox.innerHTML = data.answer.replace(/\\n/g, '<br>');
                    
                    // Display citations
                    if (data.citations && data.citations.length > 0) {
                        citationsList.innerHTML = data.citations.map((citation, idx) => `
                            <div class="citation-item">
                                <strong>Điều luật ${idx + 1}:</strong>
                                <p>${citation.content}</p>
                                ${citation.source ? `<small>Nguồn: ${citation.source}</small>` : ''}
                            </div>
                        `).join('');
                        citationsBox.style.display = 'block';
                    } else {
                        citationsBox.style.display = 'none';
                    }
                    
                    // Display contradictions
                    if (data.contradictions && data.contradictions.length > 0) {
                        contradictionsList.innerHTML = data.contradictions.map(cont => 
                            `<li>${cont}</li>`
                        ).join('');
                        contradictionsBox.style.display = 'block';
                    } else {
                        contradictionsBox.style.display = 'none';
                    }
                    
                    resultSection.style.display = 'block';
                    
                } catch (error) {
                    alert('Lỗi: ' + error.message);
                } finally {
                    submitBtn.disabled = false;
                    loading.style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)