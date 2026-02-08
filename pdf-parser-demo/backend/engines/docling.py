from .base import BasePDFEngine, normalize_bbox
import os

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

class DoclingEngine(BasePDFEngine):
    """
    真正的 IBM Docling 引擎实现
    功能：SOTA 级的文档布局分析、表格识别和 Markdown 导出
    """
    
    def __init__(self):
        super().__init__()
        if DOCLING_AVAILABLE:
            self.converter = DocumentConverter()
        else:
            self.converter = None

    def parse(self, filepath):
        self.element_counter = 0
        
        if not DOCLING_AVAILABLE:
            return {
                "error": "Docling library not installed. Please run: pip install docling",
                "pages": []
            }

        try:
            # 1. 执行转换 (这是最耗时的一步)
            print(f"Docling parsing: {filepath} ...")
            result = self.converter.convert(filepath)
            doc = result.document
            
            pages_data = []
            
            # Docling 的数据结构是分层的，这里我们需要把它展平以适应你的前端
            # Docling 能够极其精准地识别段落、标题、表格
            
            for page_no, page in doc.pages.items():
                width = page.size.width
                height = page.size.height
                elements = []
                
                # 遍历页面上的所有项目 (Text, Table, Image)
                # Docling 的 assemble 过程已经处理好了阅读顺序
                
                # 获取所有文本单元
                for item in page.assembled.body:
                    # 这是一个简化的处理，Docling 的结构很深
                    # item 可能是一个 TextItem, TableItem, etc.
                    # 我们需要获取它的 bbox 和 text
                    
                    # 注意：Docling 的坐标原点通常是左下角 (Bottom-Left)，需要确认
                    # 经查阅，Docling 坐标系通常为 Bottom-Left
                    
                    bbox = None
                    text_content = ""
                    type_ = "text"
                    
                    if hasattr(item, "text"):
                        text_content = item.text
                    
                    # 获取 Bounding Box
                    # Docling 的 item.prov 通常包含位置信息
                    if hasattr(item, "prov") and item.prov:
                        # 取第一个来源的 bbox
                        bbox_obj = item.prov[0].bbox
                        # Docling bbox is [l, b, r, t] (Left, Bottom, Right, Top)
                        # Need to convert to Top-Left system for frontend
                        # y_top = page_height - y_top_docling
                        
                        x0 = bbox_obj.l
                        y0 = height - bbox_obj.t  # Flip Y
                        x1 = bbox_obj.r
                        y1 = height - bbox_obj.b  # Flip Y
                        
                        norm = normalize_bbox([x0, y0, x1, y1], width, height)
                        bbox = norm
                    
                    # 简单的类型判断
                    if item.label == "table":
                        type_ = "table"
                    elif item.label == "image":
                        type_ = "image"
                    elif item.label == "formula":
                        type_ = "formula"
                    elif item.label in ["title", "section_header"]:
                        type_ = "heading" # 前端可能需要支持 heading
                        text_content = f"# {text_content}" # 简单转 Markdown
                        
                    if bbox and text_content.strip():
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_no,
                            "type": type_,
                            "content": text_content,
                            "bbox": bbox
                        })

                pages_data.append({
                    "page_number": page_no,
                    "width": width,
                    "height": height,
                    "elements": elements
                })

            # Docling 生成的 Markdown 非常高质量，可以直接放在 metadata 里
            markdown_output = doc.export_to_markdown()
            
            return {
                "metadata": {"full_markdown": markdown_output},
                "pages": pages_data,
                "engine": "Docling (Real SOTA)"
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Docling parsing failed: {str(e)}", "pages": []}