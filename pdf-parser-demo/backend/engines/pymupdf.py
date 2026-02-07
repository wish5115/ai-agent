from .base import BasePDFEngine, normalize_bbox
import fitz  # PyMuPDF 的标准导入名称是 fitz

class PyMuPDFEngine(BasePDFEngine):
    def parse(self, filepath):
        # 使用 fitz.open 替代 pymupdf.open，避免命名冲突且更稳定
        doc = fitz.open(filepath)
        
        # Extract metadata
        metadata = doc.metadata
        if not metadata:
            metadata = {}
            
        pages_data = []
        
        for page_num, page in enumerate(doc):
            # 获取页面宽高
            width, height = page.rect.width, page.rect.height
            
            # 获取页面元素块
            text_page = page.get_text("dict")
            blocks = text_page["blocks"] if "blocks" in text_page else []
            
            elements = []
            for block in blocks:
                if block["type"] == 0: # Text
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    
                    text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text += span["text"]
                        text += "\n"
                    
                    content = text.strip()
                    
                    # Check for formula (heuristic)
                    if content.startswith('$') and content.endswith('$'):
                        elements.append({
                            "id": self.generate_id(),
                            "page": page_num + 1,
                            "type": "formula",
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
                elif block["type"] == 1: # Image
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    elements.append({
                        "id": self.generate_id(),
                        "page": page_num + 1,
                        "type": "image",
                        "bbox": norm
                    })
            
            # Visual Sorting:
            # 1. Sort by Y coordinate (top to bottom), using normalized Y from bbox
            # 2. If Y is close (within a small threshold), sort by X (left to right)
            # This helps with multi-column layouts where blocks might be interleaved in the raw PDF order.
            elements.sort(key=lambda el: (el["bbox"]["y"], el["bbox"]["x"]))
            
            pages_data.append({
                "page_number": page_num + 1,
                "width": width,
                "height": height,
                "elements": elements
            })
        
        # Extract Table of Contents (Headings)
        toc = []
        try:
            toc = doc.get_toc()
        except Exception:
            pass
        
        # Clean up
        doc.close()
        return {
            "metadata": metadata,
            "pages": pages_data,
            "toc": toc
        }