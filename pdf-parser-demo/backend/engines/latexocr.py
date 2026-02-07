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
    
    模型: latex-ocr-base (https://huggingface.co/rokmr/latex-ocr-base)
    """
    
    def __init__(self, model_name="rokmr/latex-ocr-base"):
        """
        初始化 LaTeX-OCR 引擎
        
        Args:
            model_name: Hugging Face 模型名称
        """
        super().__init__()
        self.model_name = model_name
        self._model = None
        self._processor = None
    
    @property
    def model(self):
        """延迟加载模型"""
        if self._model is None:
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "Transformers library is not installed. "
                    "Please install it with: pip install transformers torch"
                )
            print(f"Loading LaTeX-OCR model: {self.model_name}...")
            self._processor = AutoProcessor.from_pretrained(self.model_name)
            self._model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
            print("✓ Model loaded successfully")
        return self._model
    
    @property
    def processor(self):
        """延迟加载处理器"""
        if self._processor is None:
            _ = self.model  # 触发模型加载
        return self._processor
    
    def _extract_image_from_pdf_page(self, page, bbox, scale=2):
        """
        从 PDF 页面提取指定区域的图像
        
        Args:
            page: PyMuPDF 页面对象
            bbox: 边界框 (x0, y0, x1, y1)
            scale: 渲染缩放因子
            
        Returns:
            PIL Image 对象
        """
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
        """
        使用 LaTeX-OCR 识别图像中的数学公式
        
        Args:
            image: PIL Image 对象
            
        Returns:
            识别的 LaTeX 代码字符串
        """
        try:
            if image is None:
                return None
            
            # 处理图像
            pixel_values = self.processor(
                images=image, 
                return_tensors="pt"
            ).pixel_values
            
            # 生成 LaTeX
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=512,
                    num_beams=5,
                    early_stopping=True
                )
            
            # 解码
            latex = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            return latex
            
        except Exception as e:
            print(f"Formula recognition error: {e}")
            return None
    
    def parse(self, filepath):
        """
        解析 PDF 文件，识别数学公式
        
        Args:
            filepath: PDF 文件路径
            
        Returns:
            包含页面数据和公式信息的字典
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers is required for LaTeX-OCR engine. "
                "Please install it first: pip install transformers torch"
            )
        
        doc = fitz.open(filepath)
        
        metadata = doc.metadata
        if not metadata:
            metadata = {}
            
        pages_data = []
        all_formulas = []
        
        for page_num, page in enumerate(doc):
            width, height = page.rect.width, page.rect.height
            
            text_page = page.get_text("dict")
            blocks = text_page["blocks"] if "blocks" in text_page else []
            
            elements = []
            
            for block in blocks:
                if block["type"] == 0:  # Text
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    
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
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    
                    # 检查是否可能是公式图像（基于大小）
                    img_width = bbox[2] - bbox[0]
                    img_height = bbox[3] - bbox[1]
                    
                    # 尝试识别公式
                    image = self._extract_image_from_pdf_page(page, bbox)
                    
                    if image:
                        try:
                            latex_code = self._recognize_formula(image)
                            
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
                        except Exception:
                            elements.append({
                                "id": self.generate_id(),
                                "page": page_num + 1,
                                "type": "image",
                                "bbox": norm
                            })
                    else:
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "image",
                            "bbox": norm
                        })
            
            elements.sort(key=lambda el: (el["bbox"]["y"], el["bbox"]["x"]))
            
            pages_data.append({
                "page_number": page_num + 1,
                "width": width,
                "height": height,
                "elements": elements
            })
        
        toc = []
        try:
            toc = doc.get_toc()
        except Exception:
            pass
        
        doc.close()
        
        return {
            "metadata": metadata,
            "pages": pages_data,
            "toc": toc,
            "formulas": all_formulas,
            "engine": "latexocr"
        }


class SimpleFormulaDetector(BasePDFEngine):
    """
    简单的公式检测器 - 基于规则的检测方法
    
    识别常见的数学公式模式，如：
    - 分数: \frac{...}{...}
    - 根号: \sqrt{...}
    - 上下标: ^{...}, _{...}
    - 积分、求和等运算符
    """
    
    def __init__(self):
        super().__init__()
        self.latex_patterns = [
            r'\\frac\s*\{[^}]+\}\s*\{[^}]+\}',  # \frac{}{}
            r'\\sqrt\s*\{[^}]+\}',               # \sqrt{}
            r'\^{[^}]+}',                         # ^{}
            r'\_\{[^}]+\}',                       # _{}
            r'\\int\s+',                         # \int
            r'\\sum\s+',                         # \sum
            r'\\prod\s+',                        # \prod
            r'\\lim\s+',                         # \lim
            r'\\infty',                           # \infty
            r'\\partial',                         # \partial
            r'\\nabla',                          # \nabla
            r'\\Delta',                          # \Delta
            r'\\sigma',                          # \sigma
            r'\\mu',                             # \mu
            r'\\pi',                             # \pi
            r'\\theta',                          # \theta
            r'\\phi',                            # \phi
            r'\\lambda',                         # \lambda
            r'\\alpha',                          # \alpha
            r'\\beta',                           # \beta
            r'\\gamma',                          # \gamma
            r'\\omega',                          # \omega
            r'\\epsilon',                        # \epsilon
            r'\$[^$]+\$',                        # inline math
            r'\$\$[^$]+\$\$',                    # display math
        ]
        
        import re
        self.pattern = re.compile('|'.join(self.latex_patterns))
    
    def _contains_formula(self, text):
        """检查文本是否包含数学公式"""
        return bool(self.pattern.search(text))
    
    def _classify_formula(self, text):
        """分类公式类型"""
        if '$$' in text:
            return "display"
        elif '$' in text:
            return "inline"
        else:
            return "standalone"
    
    def parse(self, filepath):
        """
        解析 PDF 文件，检测数学公式
        
        Args:
            filepath: PDF 文件路径
            
        Returns:
            包含页面数据和公式信息的字典
        """
        doc = fitz.open(filepath)
        
        metadata = doc.metadata
        if not metadata:
            metadata = {}
            
        pages_data = []
        all_formulas = []
        
        for page_num, page in enumerate(doc):
            width, height = page.rect.width, page.rect.height
            
            text_page = page.get_text("dict")
            blocks = text_page["blocks"] if "blocks" in text_page else []
            
            elements = []
            
            for block in blocks:
                if block["type"] == 0:  # Text
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    
                    text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text += span["text"]
                        text += "\n"
                    
                    content = text.strip()
                    
                    # 提取公式
                    formulas_in_text = self.pattern.findall(content)
                    
                    if formulas_in_text:
                        # 分割文本和公式
                        parts = self.pattern.split(content)
                        
                        for part in parts:
                            if part.strip():
                                if self._contains_formula(part):
                                    formula_id = self.generate_id()
                                    elements.append({
                                        "id": formula_id,
                                        "page": page_num + 1,
                                        "type": "formula",
                                        "content": part.strip(),
                                        "bbox": norm,
                                        "formula_type": self._classify_formula(part)
                                    })
                                    
                                    all_formulas.append({
                                        "id": formula_id,
                                        "page": page_num + 1,
                                        "latex": part.strip(),
                                        "bbox": norm
                                    })
                                else:
                                    elements.append({
                                        "id": self.generate_id(),
                                        "page": page_num + 1,
                                        "type": "text",
                                        "content": part,
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
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    
                    elements.append({
                        "id": self.generate_id(),
                        "page": page_num + 1,
                        "type": "image",
                        "bbox": norm
                    })
            
            elements.sort(key=lambda el: (el["bbox"]["y"], el["bbox"]["x"]))
            
            pages_data.append({
                "page_number": page_num + 1,
                "width": width,
                "height": height,
                "elements": elements
            })
        
        toc = []
        try:
            toc = doc.get_toc()
        except Exception:
            pass
        
        doc.close()
        
        return {
            "metadata": metadata,
            "pages": pages_data,
            "toc": toc,
            "formulas": all_formulas,
            "engine": "simple_formula_detector"
        }
