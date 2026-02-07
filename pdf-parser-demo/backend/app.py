import os
import uuid
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
from engines import (
    PyMuPDFEngine, 
    PdfPlumberEngine, 
    CamelotEngine, 
    PyPDFEngine,
    LaTeXOCREngine,
    SimpleFormulaDetector,
    OpenDataLoaderEngine,
    DoclingEngine
)

app = Flask(__name__)
CORS(app, resources={r"/upload": {"origins": "*"}})

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Engine Registry
ENGINES = {
    'PyMuPDF': PyMuPDFEngine(),
    'pdfplumber': PdfPlumberEngine(),
    'camelot': CamelotEngine(),
    'docling': DoclingEngine(),
    'OpenDataLoader': OpenDataLoaderEngine(),
    'PyPDF': PyPDFEngine(),
    'LaTeXOCR': LaTeXOCREngine(),
    'SimpleFormulaDetector': SimpleFormulaDetector()
}

@app.route('/upload', methods=['POST'])
def upload_and_parse():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    engine_name = request.form.get('engine', 'PyMuPDF')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    engine = ENGINES.get(engine_name)
    
    if not engine:
        return jsonify({"error": f"Engine {engine_name} not found"}), 400
    
    try:
        result = engine.parse(filepath)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
        
    return jsonify({
        "filename": file.filename,
        "url": f"/uploads/{filename}",
        "result": result
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
