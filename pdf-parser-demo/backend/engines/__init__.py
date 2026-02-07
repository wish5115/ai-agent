from .pymupdf import PyMuPDFEngine
from .pdfplumber import PdfPlumberEngine
from .camelot import CamelotEngine
from .pypdf import PyPDFEngine
from .latexocr import LaTeXOCREngine, SimpleFormulaDetector

# Fallback for others
class OpenDataLoaderEngine(PyMuPDFEngine):
    pass

class DoclingEngine(PyMuPDFEngine):
    pass

__all__ = [
    'PyMuPDFEngine',
    'PdfPlumberEngine',
    'CamelotEngine',
    'PyPDFEngine',
    'LaTeXOCREngine',
    'SimpleFormulaDetector',
    'OpenDataLoaderEngine',
    'DoclingEngine'
]

