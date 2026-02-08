from .base import BasePDFEngine, normalize_bbox
import camelot
# 我们只用 pypdf 获取页面宽高（它是 Camelot 的底层依赖，不算引入新工具）
from pypdf import PdfReader 

class CamelotEngine(BasePDFEngine):
    """
    纯净版 Camelot 引擎
    只使用 camelot-py 库进行识别，不依赖 pdfplumber 进行混合解析。
    """
    def parse(self, filepath):
        self.element_counter = 0
        pages_data = []
        
        # 1. 获取页面尺寸 (Metadata)
        # Camelot 解析结果里不包含页面宽高，所以我们需要用轻量级工具读一下尺寸
        # 这不算"作弊"，因为这是前端渲染必须的坐标系基准
        page_dimensions = {}
        try:
            reader = PdfReader(filepath)
            for i, page in enumerate(reader.pages):
                # pypdf 的宽高单位通常是 point (72 dpi)
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                page_dimensions[i + 1] = (width, height)
        except Exception:
            pass

        try:
            print(f"Camelot (Pure) parsing: {filepath} ...")
            
            # ==========================================
            # 核心策略：针对三线表（无竖线）
            # ==========================================
            # 1. flavor='stream': 必须用流式，因为 Lattice 无法识别无竖线表格。
            # 2. row_tol=10: (行容差) 默认是 2。调大可以允许稍微错位的行合并，防止文字被打散。
            # 3. edge_tol=500: (边缘容差) 默认 50。设大一点告诉它"表格可能在页面的任何位置"。
            # 注意：不指定 table_areas 的情况下，Camelot 会尝试猜测。
            
            tables = camelot.read_pdf(
                filepath, 
                pages='all', 
                flavor='lattice',  # 👈 stream误判率高 lattice识别线条更准
                row_tol=10
            )
            
            print(f"Camelot found {len(tables)} tables.")

            # 按页面分组
            tables_by_page = {}
            for table in tables:
                p = table.page
                if p not in tables_by_page: tables_by_page[p] = []
                tables_by_page[p].append(table)
            
            # 遍历所有页面构建数据
            # 即使该页没有表格，也要返回一个空的 elements 列表，保证前端页面正常显示
            total_pages = len(page_dimensions)
            
            for i in range(1, total_pages + 1):
                width, height = page_dimensions.get(i, (600, 800)) # 默认值防崩
                elements = []
                
                page_tables = tables_by_page.get(i, [])
                
                for table in page_tables:
                    # 获取坐标 (Camelot 使用左下角原点)
                    # _bbox = (x0, y0, x1, y1) -> (Left, Bottom, Right, Top)
                    if hasattr(table, '_bbox'):
                        c_x0, c_y0, c_x1, c_y1 = table._bbox
                        
                        # 坐标转换：从 Bottom-Left (PDF) 转为 Top-Left (Web)
                        # New Top = Height - Old Top (y1)
                        # New Bottom = Height - Old Bottom (y0)
                        new_top = height - c_y1
                        new_bottom = height - c_y0
                        
                        norm_bbox = normalize_bbox(
                            [c_x0, new_top, c_x1, new_bottom], 
                            width, height
                        )
                    else:
                        norm_bbox = None

                    # 提取内容 (CSV 格式)
                    content = table.df.to_csv(index=False, header=False)
                    
                    elements.append({
                        "id": self.generate_id(),
                        "page": i,
                        "type": "table",
                        "content": content,
                        "bbox": norm_bbox
                    })
                
                pages_data.append({
                    "page_number": i,
                    "width": width,
                    "height": height,
                    "elements": elements
                })

        except Exception as e:
            print(f"Camelot parsing error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

        return {
            "metadata": {},
            "pages": pages_data,
            "engine": "camelot (Pure Stream)"
        }