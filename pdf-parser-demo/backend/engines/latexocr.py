"""
简化的 LaTeX-OCR 引擎 - 不依赖 pix2text
使用开放的 LaTeX OCR 模型进行数学公式识别
"""

from .base import BasePDFEngine, normalize_bbox
import fitz  # PyMuPDF
from PIL import Image
import io
import os

# 尝试导入依赖
try:
    import torch
    from transformers import AutoProcessor, VisionEncoderDecoderModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class LaTeXOCREngine(BasePDFEngine):
    """
    使用 Hugging Face Transformers 的 LaTeX-OCR 模型识别数学公式
    """
    
    def __init__(self, model_name="rokmr/latex-ocr-base"):
        super().__init__()
        self.model_name = model_name
        self._model = None
        self._processor = None
    
    @property
    def model(self):
        if self._model is None:
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("Transformers library is not installed.")
            print(f"Loading LaTeX-OCR model: {self.model_name}...")
            self._processor = AutoProcessor.from_pretrained(self.model_name)
            self._model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
            print("✓ Model loaded successfully")
        return self._model
    
    @property
    def processor(self):
        if self._processor is None:
            _ = self.model
        return self._processor
    
    def _extract_image_from_pdf_page(self, page, bbox, scale=2):
        try:
            rect = fitz.Rect(bbox)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            return image
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None
    
    def _recognize_formula(self, image):
        try:
            if image is None: return None
            pixel_values = self.processor(images=image, return_tensors="pt").pixel_values
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values, max_length=512, num_beams=5, early_stopping=True
                )
            latex = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return latex
        except Exception as e:
            print(f"Formula recognition error: {e}")
            return None
    
    def parse(self, filepath):
        self.element_counter = 0
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers is required.")
        
        doc = fitz.open(filepath)
        metadata = doc.metadata if doc.metadata else {}
        pages_data = []
        all_formulas = []
        
        for page_num, page in enumerate(doc):
            width, height = page.rect.width, page.rect.height
            text_page = page.get_text("dict")
            blocks = text_page["blocks"] if "blocks" in text_page else []
            elements = []
            
            for block in blocks:
                bbox = block["bbox"]
                norm = normalize_bbox(bbox, width, height)

                if block["type"] == 0:  # Text
                    text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text += span["text"]
                        text += "\n"
                    content = text.strip()
                    
                    if '$' in content:
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "text_with_inline_formula",
                            "content": content,
                            "bbox": norm
                        })
                    else:
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "text",
                            "content": content,
                            "bbox": norm
                        })
                
                elif block["type"] == 1:  # Image
                    # 检查是否可能是公式图像（基于大小）
                    # 尝试识别公式
                    image = self._extract_image_from_pdf_page(page, bbox)
                    latex_code = None
                    if image:
                        try:
                            latex_code = self._recognize_formula(image)
                        except Exception:
                            pass
                            
                    if latex_code and len(latex_code.strip()) > 0:
                        formula_id = self.generate_id()
                        elements.append({
                            "id": formula_id,
                            "page": page_num + 1,
                            "type": "formula_image",
                            "content": latex_code,
                            "bbox": norm,
                            "recognized": True
                        })
                        all_formulas.append({
                            "id": formula_id,
                            "page": page_num + 1,
                            "latex": latex_code,
                            "bbox": norm
                        })
                    else:
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "image",
                            "bbox": norm
                        })
            
            # 【核心修改】已删除 elements.sort(...)
            # 保持 PDF 原生阅读顺序
            
            pages_data.append({
                "page_number": page_num + 1,
                "width": width,
                "height": height,
                "elements": elements
            })
        
        doc.close()
        return {
            "metadata": metadata,
            "pages": pages_data,
            "formulas": all_formulas,
            "engine": "latexocr (Natural Order)"
        }


class SimpleFormulaDetector(BasePDFEngine):
    r"""
    简单的公式检测器 - 基于规则的检测方法
    识别常见的数学公式模式，如：
    - 分数: \frac{...}{...}
    - 根号: \sqrt{...}
    """
    
    def __init__(self):
        super().__init__()
        self.latex_patterns = [
            r'\\frac\s*\{[^}]+\}\s*\{[^}]+\}',
            r'\\sqrt\s*\{[^}]+\}',
            r'\^{[^}]+}',
            r'\_\{[^}]+\}',
            r'\\int\s+',
            r'\\sum\s+',
            r'\$[^$]+\$',
            r'\$\$[^$]+\$\$',
        ]
        import re
        self.pattern = re.compile('|'.join(self.latex_patterns))
    
    def _contains_formula(self, text):
        return bool(self.pattern.search(text))
    
    def _classify_formula(self, text):
        if '$$' in text: return "display"
        elif '$' in text: return "inline"
        else: return "standalone"
    
    def parse(self, filepath):
        self.element_counter = 0
        doc = fitz.open(filepath)
        metadata = doc.metadata if doc.metadata else {}
        pages_data = []
        
        for page_num, page in enumerate(doc):
            width, height = page.rect.width, page.rect.height
            text_page = page.get_text("dict")
            blocks = text_page["blocks"] if "blocks" in text_page else []
            elements = []
            
            for block in blocks:
                bbox = block["bbox"]
                norm = normalize_bbox(bbox, width, height)

                if block["type"] == 0:  # Text
                    text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text += span["text"]
                        text += "\n"
                    content = text.strip()
                    
                    if self._contains_formula(content):
                         elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "formula",
                            "content": content,
                            "bbox": norm,
                            "formula_type": self._classify_formula(content)
                        })
                    else:
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "text",
                            "content": content,
                            "bbox": norm
                        })
                
                elif block["type"] == 1:  # Image
                    elements.append({
                        "id": self.generate_id(),
                        "page": page_num + 1,
                        "type": "image",
                        "bbox": norm
                    })
            
            # 【核心修改】已删除 elements.sort(...)
            
            pages_data.append({
                "page_number": page_num + 1,
                "width": width,
                "height": height,
                "elements": elements
            })
        
        doc.close()
        return {
            "metadata": metadata,
            "pages": pages_data,
            "engine": "simple_formula_detector"
        }