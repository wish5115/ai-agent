from .base import BasePDFEngine, normalize_bbox
from langchain_community.document_loaders import PyPDFLoader

class PyPDFEngine(BasePDFEngine):
    def parse(self, filepath):
        self.element_counter = 0
        loader = PyPDFLoader(filepath)
        pages = loader.load()
        
        pages_data = []
        for i, doc in enumerate(pages):
            # Split content by lines to find potential formulas
            lines = doc.page_content.split('\n')
            elements = []
            for line in lines:
                content = line.strip()
                if not content: continue
                
                if content.startswith('$') and content.endswith('$'):
                    elements.append({
                        "id": self.generate_id(),
                        "page": i + 1,
                        "type": "formula",
                        "content": content,
                        "bbox": None
                    })
                else:
                    elements.append({
                        "id": self.generate_id(),
                        "page": i + 1,
                        "type": "text",
                        "content": content,
                        "bbox": None
                    })
            
            pages_data.append({
                "page_number": i + 1,
                "width": 0,
                "height": 0,
                "elements": elements
            })
        return {
            "metadata": {},
            "pages": pages_data
        }

