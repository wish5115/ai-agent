from .base import BasePDFEngine, normalize_bbox
import fitz  # PyMuPDF

class PyMuPDFEngine(BasePDFEngine):
    def parse(self, filepath):
        self.element_counter = 0
        doc = fitz.open(filepath)
        
        metadata = doc.metadata if doc.metadata else {}
        pages_data = []
        
        for page_num, page in enumerate(doc):
            width, height = page.rect.width, page.rect.height
            elements = []

            # 1. 尝试使用 PyMuPDF 的原生表格寻找功能 (新版功能)
            # 这会把表格区域标记出来，避免和文本混淆
            try:
                tables = page.find_tables()
                for table in tables:
                    # 获取表格边框
                    bbox = table.bbox
                    norm = normalize_bbox(bbox, width, height)
                    
                    # 提取表格内容 (输出为二维数组字符串，或者 csv)
                    # table.extract() 返回 [[col1, col2], ...]
                    content_data = table.extract()
                    content_str = str(content_data) if content_data else "Table"

                    elements.append({
                        "id": self.generate_id(),
                        "page": page_num + 1,
                        "type": "table",
                        "content": content_str,
                        "bbox": norm,
                        "raw_bbox": bbox # 用于后续可能的排重
                    })
            except Exception as e:
                print(f"PyMuPDF find_tables error: {e}")

            # 2. 获取常规内容 (文本 + 图片)
            text_page = page.get_text("dict")
            blocks = text_page["blocks"] if "blocks" in text_page else []
            
            for block in blocks:
                # 0 = Text, 1 = Image
                if block["type"] == 0: 
                    bbox = block["bbox"]
                    norm = normalize_bbox(bbox, width, height)
                    
                    # 简单的去重检查：如果这个文本块完全位于某个已识别的表格内，标记一下或忽略
                    # 这里为了简单，我们还是全部保留，让前端决定显示层级
                    
                    text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text += span["text"]
                        text += "\n"
                    
                    content = text.strip()
                    if not content: continue

                    el_type = "text"
                    if '$' in content: 
                        if content.startswith('$') and content.endswith('$'):
                             el_type = "formula"
                        else:
                             el_type = "text_with_inline_formula"

                    elements.append({
                        "id": self.generate_id(),
                        "page": page_num + 1,
                        "type": el_type,
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
            
            # 此时 elements 列表里混合了 table (先加进去的) 和 text/image (后加进去的)
            # 为了保持 ID 顺序的大致逻辑，我们可以按 y 坐标重新简单排个序，或者直接信任追加顺序
            # 建议：PyMuPDF 的 find_tables 和 get_text 是独立的，
            # 这里的混合可能会导致 表格 和 表格内的文字 重复出现。这是正常的解析现象。
            
            # 重新按 ID 排序 (其实 generate_id 已经是递增的了)
            # elements.sort(key=lambda x: x['id']) 

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
            "engine": "PyMuPDF (With Tables)"
        }