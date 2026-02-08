from .pymupdf import PyMuPDFEngine
from .pdfplumber import PdfPlumberEngine
from .camelot import CamelotEngine
from .pypdf import PyPDFEngine
from .latexocr import LaTeXOCREngine, SimpleFormulaDetector

# 新增：真正的 Docling 导入
from .docling import DoclingEngine 

# OpenDataLoader 暂时还是假的，因为这个库配置非常复杂 (MinerU)
class OpenDataLoaderEngine(PyMuPDFEngine):
    pass

__all__ = [
    'PyMuPDFEngine',
    'PdfPlumberEngine',
    'CamelotEngine',
    'PyPDFEngine',
    'LaTeXOCREngine',
    'SimpleFormulaDetector',
    'OpenDataLoaderEngine',
    'DoclingEngine' # 确保导出
]