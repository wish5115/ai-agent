import pymupdf

def normalize_bbox(bbox, page_width, page_height, target_width=800):
    """
    Convert bbox from PDF point coordinates to a standardized ratio (0-1).
    PyMuPDF and pdfplumber typically use Top-Left origin (0,0).
    Frontend (CSS) also uses Top-Left origin.
    So NO Y-axis flipping is needed.
    """
    if not bbox:
        return None
    
    x0, y0, x1, y1 = bbox
    
    # 直接计算比例，不需要 page_height - y
    return {
        "x": x0 / page_width,
        "y": y0 / page_height, 
        "w": (x1 - x0) / page_width,
        "h": (y1 - y0) / page_height,
        "raw": bbox
    }

# def normalize_bbox(bbox, page_width, page_height):
#     if not bbox:
#         return None
    
#     x0, y0, x1, y1 = bbox
    
#     # Normalize Y
#     ny0 = page_height - y1
#     ny1 = page_height - y0
    
#     return {
#         "x": x0 / page_width,
#         "y": ny0 / page_height,
#         "w": (x1 - x0) / page_width,
#         "h": (ny1 - ny0) / page_height,
#         "raw": bbox
#     }

class BasePDFEngine:
    def __init__(self):
        self.element_counter = 0
        
    def parse(self, filepath):
        raise NotImplementedError
        
    def generate_id(self):
        self.element_counter += 1
        return self.element_counter

