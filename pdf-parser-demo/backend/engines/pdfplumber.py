from .base import BasePDFEngine, normalize_bbox
import pdfplumber

class PdfPlumberEngine(BasePDFEngine):
    def parse(self, filepath):
        self.element_counter = 0
        pages_data = []
        
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                width = float(page.width)
                height = float(page.height)
                
                elements = []
                
                # 1. 提取表格 (Tables)
                # pdfplumber 的表格提取非常强大
                try:
                    tables = page.find_tables()
                    for table in tables:
                        norm = normalize_bbox(table.bbox, width, height)
                        # 尝试提取表格数据作为 content，而不仅仅是 "Table Data"
                        # extract() 返回 [['row1_col1', ...], ...]
                        table_content = table.extract() 
                        content_str = str(table_content) if table_content else "Table"
                        
                        elements.append({
                            "id": self.generate_id(),
                            "page": i + 1,
                            "type": "table",
                            "content": content_str, 
                            "bbox": norm,
                            "raw_bbox": table.bbox # 用于后续去重
                        })
                except Exception as e:
                    print(f"Table extraction error on page {i+1}: {e}")

                # 2. 提取图片 (Images) - 【新功能已释放】
                # pdfplumber 原生支持图片对象提取
                try:
                    for img in page.images:
                        # pdfplumber image dict contains x0, top, x1, bottom
                        bbox = [img['x0'], img['top'], img['x1'], img['bottom']]
                        norm = normalize_bbox(bbox, width, height)
                        elements.append({
                            "id": self.generate_id(),
                            "page": i + 1,
                            "type": "image",
                            "bbox": norm
                        })
                except Exception as e:
                    print(f"Image extraction error on page {i+1}: {e}")

                # 3. 提取文本 (Text words)
                words = page.extract_words()
                for word in words:
                    bbox = [word['x0'], word['top'], word['x1'], word['bottom']]
                    norm = normalize_bbox(bbox, width, height)
                    content = word['text']
                    
                    # 简单的去重逻辑：如果文本完全在某个表格内部，可以选择忽略
                    # 这里为了"全能力释放"，我们保留所有内容，交给前端去渲染
                    
                    # 简单公式检测
                    type_ = "text"
                    if content.startswith('$') and content.endswith('$'):
                        type_ = "formula"

                    elements.append({
                        "id": self.generate_id(),
                        "page": i + 1,
                        "type": type_,
                        "content": content,
                        "bbox": norm
                    })
                
                # 【重要】不要在这里强制排序，信任提取顺序
                # 或者按照垂直位置微调（可选），但 pdfplumber extract_words 默认已经是排好序的
                
                pages_data.append({
                    "page_number": i + 1,
                    "width": width,
                    "height": height,
                    "elements": elements
                })
                
        return {
            "metadata": {}, 
            "pages": pages_data,
            "engine": "pdfplumber (Fully Unleashed)"
        }