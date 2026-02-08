from .base import BasePDFEngine, normalize_bbox
import os
import json

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
            print(f"Docling parsing: {filepath} ...")
            # 1. 执行转换
            result = self.converter.convert(filepath)
            # 获取 Docling 的文档对象
            doc = result.document
            
            pages_data = []
            
            # 2. 导出为 JSON 字典格式，这样处理结构更稳定
            # Docling 提供了 export_to_dict() 方法，这比直接访问对象属性更安全
            doc_dict = doc.export_to_dict()
            
            # 获取页面尺寸信息 (Docling 的 export_to_dict 可能不直接包含每页宽高，需从对象获取)
            # 我们先建立一个页面尺寸映射
            page_dims = {}
            for page_no, page_obj in doc.pages.items():
                # page_obj.size.width / height
                page_dims[page_no] = {
                    "width": page_obj.size.width,
                    "height": page_obj.size.height
                }

            # 3. 遍历解析后的所有文本/表格元素
            # 在 export_to_dict() 的结构中，内容通常在 'texts', 'tables', 'pictures' 等字段
            # 或者我们直接遍历 doc_dict['pages'] 如果存在的话
            
            # 新版 Docling 结构通常把所有元素扁平化放在 doc.texts 和 doc.tables 中，
            # 并通过 prov (provenance) 字段关联到页面和坐标。
            
            # 初始化页面容器
            pages_map = {}
            for p_no in page_dims.keys():
                pages_map[p_no] = []

            # --- 处理文本 (Texts) ---
            for item in doc.texts:
                # item 是 TextItem 对象
                # 它的 prov 属性是一个列表，包含位置信息
                if not hasattr(item, "prov") or not item.prov:
                    continue
                
                for prov in item.prov:
                    p_no = prov.page_no
                    if p_no not in pages_map: continue
                    
                    # 获取页面尺寸用于归一化
                    p_w = page_dims[p_no]["width"]
                    p_h = page_dims[p_no]["height"]
                    
                    # 坐标转换
                    # Docling bbox: [l, b, r, t] (左, 底, 右, 顶) - 原点在左下角
                    bbox = prov.bbox
                    x0, y0, x1, y1 = bbox.l, bbox.b, bbox.r, bbox.t
                    
                    # 转换为 Top-Left (Web) 坐标系
                    # New Top = Height - Old Top (y1)
                    # New Bottom = Height - Old Bottom (y0)
                    new_top = p_h - y1
                    new_bottom = p_h - y0
                    
                    norm_bbox = normalize_bbox([x0, new_top, x1, new_bottom], p_w, p_h)
                    
                    # 确定类型
                    el_type = "text"
                    if item.label == "section_header" or item.label == "title":
                        el_type = "heading"
                    elif item.label == "code":
                        el_type = "code"
                    elif item.label == "formula":
                        el_type = "formula"
                        
                    pages_map[p_no].append({
                        "id": self.generate_id(),
                        "page": p_no,
                        "type": el_type,
                        "content": item.text,
                        "bbox": norm_bbox
                    })

            # --- 处理表格 (Tables) ---
            for table in doc.tables:
                if not hasattr(table, "prov") or not table.prov:
                    continue
                    
                # 表格通常只有一个主要位置
                prov = table.prov[0]
                p_no = prov.page_no
                if p_no not in pages_map: continue

                p_w = page_dims[p_no]["width"]
                p_h = page_dims[p_no]["height"]
                
                bbox = prov.bbox
                x0, y0, x1, y1 = bbox.l, bbox.b, bbox.r, bbox.t
                
                new_top = p_h - y1
                new_bottom = p_h - y0
                
                norm_bbox = normalize_bbox([x0, new_top, x1, new_bottom], p_w, p_h)
                
                # 导出表格内容为 CSV 或 HTML
                # table.export_to_dataframe() 需要 pandas
                try:
                    df = table.export_to_dataframe()
                    content = df.to_csv(index=False)
                except:
                    content = "Table content (export failed)"

                pages_map[p_no].append({
                    "id": self.generate_id(),
                    "page": p_no,
                    "type": "table",
                    "content": content,
                    "bbox": norm_bbox
                })

            # --- 处理图片 (Pictures) ---
            if hasattr(doc, "pictures"):
                for pic in doc.pictures:
                    if not hasattr(pic, "prov") or not pic.prov: continue
                    prov = pic.prov[0]
                    p_no = prov.page_no
                    if p_no not in pages_map: continue
                    
                    p_w = page_dims[p_no]["width"]
                    p_h = page_dims[p_no]["height"]
                    bbox = prov.bbox
                    
                    norm_bbox = normalize_bbox(
                        [bbox.l, p_h - bbox.t, bbox.r, p_h - bbox.b], 
                        p_w, p_h
                    )
                    
                    pages_map[p_no].append({
                        "id": self.generate_id(),
                        "page": p_no,
                        "type": "image",
                        "content": "<image>",
                        "bbox": norm_bbox
                    })

            # 4. 构建最终响应
            for p_no in sorted(page_dims.keys()):
                pages_data.append({
                    "page_number": p_no,
                    "width": page_dims[p_no]["width"],
                    "height": page_dims[p_no]["height"],
                    "elements": pages_map.get(p_no, [])
                })

            # 导出 Markdown
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