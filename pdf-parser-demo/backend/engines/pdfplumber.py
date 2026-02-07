from .base import BasePDFEngine, normalize_bbox
import pdfplumber

class PdfPlumberEngine(BasePDFEngine):
    def parse(self, filepath):
        pages_data = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                width = float(page.width)
                height = float(page.height)
                
                elements = []
                
                # Tables
                tables = page.find_tables()
                for table in tables:
                    norm = normalize_bbox(table.bbox, width, height)
                    elements.append({
                        "id": self.generate_id(),
                        "page": i + 1,
                        "type": "table",
                        "content": "Table Data",
                        "bbox": norm
                    })
                    
                # Text (words)
                words = page.extract_words()
                for word in words:
                    bbox = [word['x0'], word['top'], word['x1'], word['bottom']]
                    norm = normalize_bbox(bbox, width, height)
                    
                    content = word['text']
                    
                    # Check for formula (heuristic)
                    if content.startswith('$') and content.endswith('$'):
                        elements.append({
                            "id": self.generate_id(),
                            "page": i + 1,
                            "type": "formula",
                            "content": content,
                            "bbox": norm
                        })
                    else:
                        elements.append({
                            "id": self.generate_id(),
                            "page": i + 1,
                            "type": "text",
                            "content": content,
                            "bbox": norm
                        })
                    
                pages_data.append({
                    "page_number": i + 1,
                    "width": width,
                    "height": height,
                    "elements": elements
                })
                
        return {
            "metadata": {}, # pdfplumber doesn't expose simple metadata easily without inspecting the PDF object
            "pages": pages_data
        }

