# Legal DocVQA System

Hệ thống hỏi đáp tài liệu pháp lý thông minh sử dụng DeepSeek OCR và RAG (Retrieval-Augmented Generation) để phân tích và trả lời các câu hỏi về tài liệu pháp lý tiếng Việt.

## 🎯 Mục Tiêu

- **OCR chính xác**: Sử dụng DeepSeek để trích xuất văn bản và cấu trúc (bảng biểu, tiêu đề) từ ảnh tài liệu với độ chính xác cao, xuất định dạng Markdown
- **RAG pháp lý**: Xây dựng hệ thống truy xuất thông tin để tìm kiếm các điều luật liên quan dựa trên ngữ cảnh của tài liệu
- **Lập luận logic**: Kết hợp thông tin từ ảnh và điều luật để tạo ra câu trả lời có tính lập luận logic, phát hiện mâu thuẫn

## 🏗️ Kiến Trúc Hệ Thống

### Bước 1: Xử Lý OCR (Optical Character Recognition)
- Sử dụng **DeepSeek Vision API** để trích xuất văn bản từ ảnh tài liệu
- Prompt engineering để xuất định dạng **Markdown**, bảo toàn:
  - Cấu trúc phân cấp (tiêu đề, tiêu đề phụ)
  - Bảng biểu
  - Số thứ tự, điều khoản
- Văn bản trích xuất (Document Context) được mã hóa thành vector embeddings

### Bước 2: Truy Xuất Tri Thức Pháp Lý (Legal RAG)
- Dựa trên Embedding của câu hỏi và nội dung tài liệu
- Thực hiện **Semantic Search** trong cơ sở dữ liệu Vector chứa các văn bản luật
- Áp dụng kỹ thuật **HyDE (Hypothetical Document Embeddings)** để tăng độ chính xác
- Trả về Top-K điều luật liên quan nhất

### Bước 3: Kết Hợp và Sinh Câu Trả Lời (Reasoning & Generation)
- Xây dựng Prompt bao gồm:
  1. Nội dung tài liệu đã OCR
  2. Top-K điều luật đã truy xuất
  3. Câu hỏi người dùng
- LLM thực hiện **Chain-of-Thought** reasoning:
  - Đọc và hiểu tài liệu
  - Xác định điều khoản liên quan
  - Đối chiếu với quy định pháp luật
  - Phát hiện mâu thuẫn (nếu có)
  - Đưa ra kết luận và giải thích

## 🚀 Hướng Dẫn Cài Đặt

### 1. Cài Đặt UV

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Cài Đặt Dependencies

```bash
# Clone repo và vào thư mục project
cd rag-legal

# Tạo virtual environment và cài dependencies
uv sync
```

### 3. Cấu Hình Environment Variables

Tạo file `.env` trong thư mục gốc:

```bash
# OpenAI API Key (cho LLM và Embeddings)
OPENAI_API_KEY=sk-your-openai-api-key-here

# DeepSeek API Key (cho OCR)
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_HTTP_PORT=6333
QDRANT_API_KEY=your-qdrant-api-key-if-needed
```

### 4. Chuẩn Bị Dữ Liệu Pháp Lý

Đặt các file PDF chứa văn bản luật vào thư mục `data/`, sau đó chạy:

```bash
python ingest.py
```

Script này sẽ:
- Đọc các file PDF từ thư mục `data/`
- Chia nhỏ thành các chunks
- Tạo embeddings và lưu vào Qdrant Vector Database

### 5. Chạy Ứng Dụng

```bash
# Chạy với UV (không cần activate)
uv run python main.py

# Hoặc chạy trực tiếp
python main.py
```

Server sẽ chạy tại: `http://localhost:8080`

## 📖 Sử Dụng

### Giao Diện Demo

Truy cập: `http://localhost:8080/demo`

Giao diện web cho phép:
- Upload ảnh tài liệu pháp lý
- Nhập câu hỏi
- Xem kết quả với:
  - Câu trả lời chi tiết
  - Danh sách điều luật được trích dẫn
  - Các điểm mâu thuẫn phát hiện được (nếu có)

### API Endpoints

#### 1. Chat với ảnh (JSON)

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "question": "Điều khoản này có hợp pháp không?",
  "image_base64": "base64-encoded-image-string"
}
```

#### 2. Chat với document context có sẵn

```bash
POST /api/v1/chat
Content-Type: application/json

{
  "question": "Phân tích điều khoản này",
  "document_context": "# Tài liệu\n\nNội dung markdown..."
}
```

#### 3. Upload file ảnh trực tiếp

```bash
POST /api/v1/chat/upload
Content-Type: multipart/form-data

question: "Câu hỏi của bạn"
image: [file]
```

### Response Format

```json
{
  "answer": "Câu trả lời chi tiết với lập luận logic...",
  "citations": [
    {
      "content": "Nội dung điều luật",
      "source": "Tên văn bản, số điều",
      "relevance_score": 0.95
    }
  ],
  "document_context": "Nội dung tài liệu đã OCR (Markdown)",
  "contradictions": [
    "Điểm mâu thuẫn 1: ...",
    "Điểm mâu thuẫn 2: ..."
  ]
}
```

## 📁 Cấu Trúc Project

```
rag-legal/
├── data/                      # Thư mục chứa PDF văn bản luật
├── src/
│   ├── components/
│   │   ├── ocr.py            # Module OCR sử dụng DeepSeek
│   │   └── vectordb.py       # Vector database (Qdrant)
│   ├── chains/
│   │   └── modules.py        # LangChain chains (HyDE, generators, graders)
│   ├── graph/
│   │   ├── nodes.py          # Graph nodes (OCR, retrieve, generate, detect contradictions)
│   │   └── workflow.py       # LangGraph workflow definition
│   ├── server/
│   │   ├── app.py            # FastAPI app
│   │   ├── routes.py         # API routes
│   │   └── schemas.py        # Pydantic schemas
│   ├── conf/
│   │   ├── config.yaml       # Hydra config
│   │   └── structure.py      # Config dataclasses
│   ├── config.py             # Config loader
│   ├── state.py              # GraphState definition
│   └── logger.py             # Logging setup
├── ingest.py                 # Script để ingest dữ liệu vào vector DB
├── main.py                   # Entry point
├── pyproject.toml           # Dependencies
└── README.md                # Tài liệu này
```

## 🔧 Cấu Hình

Cấu hình được quản lý qua Hydra trong `src/conf/config.yaml`:

```yaml
project_name: "Legal-DocVQA-System"
chunk_size: 500
chunk_overlap: 50

server:
  host: "127.0.0.1"
  port: 8080
  reload: true

llm:
  name: "gpt-4o-mini"
  temperature: 0

deepseek:
  api_key: ${oc.env:DEEPSEEK_API_KEY}
  base_url: "https://api.deepseek.com"
  model: "deepseek-chat"

qdrant:
  collection_name: "rag_collection"
  host: ${oc.env:QDRANT_HOST}
  port: ${oc.env:QDRANT_HTTP_PORT}

search:
  max_results: 10
```

## 🛠️ Commands Thường Dùng

```bash
# Sync dependencies
uv sync

# Chạy app
uv run python main.py

# Ingest dữ liệu pháp lý vào vector DB
python ingest.py

# Kiểm tra dependencies
uv tree

# Update dependencies
uv lock --upgrade
```

## 🔍 Troubleshooting

### Lỗi DeepSeek API Key

Đảm bảo đã thêm `DEEPSEEK_API_KEY` vào file `.env`

### Lỗi Qdrant Connection

- Kiểm tra Qdrant đang chạy: `docker-compose up -d` (nếu dùng Docker)
- Hoặc cài đặt Qdrant local và cập nhật `QDRANT_HOST` và `QDRANT_HTTP_PORT`

### Lỗi Import Module

```bash
# Re-sync dependencies
uv sync --reinstall
```

### Port đã được sử dụng

```bash
# Đổi port trong command
python main.py server.port=8001
```

## 📚 Tính Năng Chính

✅ **OCR chính xác** với DeepSeek, xuất Markdown  
✅ **HyDE** để cải thiện độ chính xác retrieval  
✅ **Chain-of-Thought** reasoning cho legal analysis  
✅ **Phát hiện mâu thuẫn** giữa tài liệu và quy định pháp luật  
✅ **Citation tracking** - hiển thị các điều luật được sử dụng  
✅ **Giao diện demo** đẹp mắt và dễ sử dụng  

## 🎓 Kết Quả Mong Đợi

- ✅ Xây dựng thành công hệ thống DocVQA có khả năng đọc hiểu hợp đồng/văn bản hành chính tiếng Việt
- ✅ Hệ thống có khả năng phát hiện các điểm mâu thuẫn giữa văn bản trong ảnh và quy định pháp luật
- ✅ Giao diện demo cho phép người dùng upload ảnh, hỏi đáp và xem được trích dẫn luật cụ thể

## 📝 License

MIT License
