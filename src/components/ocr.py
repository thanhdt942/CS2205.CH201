"""
OCR Module sử dụng DeepSeek API để trích xuất văn bản và cấu trúc từ ảnh tài liệu.
Xuất ra định dạng Markdown để bảo toàn cấu trúc phân cấp và bảng biểu.
"""
import base64
import requests
from typing import Optional
from src.config import cfg
from src.logger import logger


def encode_image_to_base64(image_path: str) -> str:
    """Chuyển đổi ảnh thành base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def encode_image_bytes_to_base64(image_bytes: bytes) -> str:
    """Chuyển đổi image bytes thành base64 string"""
    return base64.b64encode(image_bytes).decode('utf-8')


def extract_text_with_deepseek(
    image_path: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    image_base64: Optional[str] = None
) -> str:
    """
    Sử dụng DeepSeek Vision API để trích xuất văn bản từ ảnh.
    Prompt được tinh chỉnh để xuất ra định dạng Markdown.
    
    Args:
        image_path: Đường dẫn đến file ảnh
        image_bytes: Bytes của ảnh
        image_base64: Base64 string của ảnh (nếu đã encode sẵn)
    
    Returns:
        Văn bản đã trích xuất ở định dạng Markdown
    """
    # Xác định base64 image
    if image_base64:
        base64_image = image_base64
    elif image_bytes:
        base64_image = encode_image_bytes_to_base64(image_bytes)
    elif image_path:
        base64_image = encode_image_to_base64(image_path)
    else:
        raise ValueError("Phải cung cấp ít nhất một trong: image_path, image_bytes, hoặc image_base64")
    
    # Prompt được tinh chỉnh để xuất Markdown với cấu trúc
    ocr_prompt = """Bạn là một hệ thống OCR chuyên nghiệp. Nhiệm vụ của bạn là trích xuất văn bản từ ảnh tài liệu pháp lý tiếng Việt.

Yêu cầu:
1. Trích xuất CHÍNH XÁC tất cả văn bản trong ảnh
2. Bảo toàn cấu trúc phân cấp của tài liệu:
   - Sử dụng # cho tiêu đề chính
   - Sử dụng ## cho tiêu đề phụ
   - Sử dụng ### cho tiêu đề nhỏ hơn
3. Bảo toàn định dạng bảng biểu:
   - Sử dụng Markdown table syntax (| cột1 | cột2 |)
   - Giữ nguyên số hàng và cột
4. Giữ nguyên số thứ tự, điều khoản, khoản, điểm
5. Không thêm thông tin không có trong ảnh
6. Giữ nguyên định dạng ngày tháng, số tiền, địa chỉ

Xuất ra định dạng Markdown hoàn chỉnh."""

    try:
        # Gọi DeepSeek Vision API
        # Note: DeepSeek có thể sử dụng OpenAI-compatible API
        api_key = cfg.deepseek.api_key
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY chưa được cấu hình trong file .env")
        
        base_url = cfg.deepseek.base_url or "https://api.deepseek.com"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": cfg.deepseek.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": ocr_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        logger.info("Đang gọi DeepSeek OCR API...")
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        result = response.json()
        
        extracted_text = result["choices"][0]["message"]["content"]
        logger.success(f"Trích xuất thành công {len(extracted_text)} ký tự")
        
        return extracted_text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi khi gọi DeepSeek API: {e}")
        raise Exception(f"Không thể trích xuất văn bản từ ảnh: {str(e)}")
    except Exception as e:
        logger.error(f"Lỗi không xác định: {e}")
        raise
