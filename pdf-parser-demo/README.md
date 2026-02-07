# PDF Parser Demo

This is a web-based PDF parsing demo that allows you to upload a PDF, select a parsing engine, and visualize the parsed content (JSON/Markdown) along with the PDF preview.

## Prerequisites

- Node.js (v14 or higher)
- Python (v3.8 or higher)
- Java Runtime (required for OpenDataLoader)

## Setup

### 1. Backend Setup

Navigate to the `backend` directory:

```bash
cd backend
```

Create a virtual environment (optional but recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

**Note:** Some dependencies like `camelot-py` and `opendataloader-pdf` may have system-specific requirements. Please refer to their documentation for installation help.

### 2. Frontend Setup

Navigate to the `frontend` directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

## Running the Application

You need to run both the backend and frontend servers.

### 1. Start the Backend

In the `backend` directory:

```bash
python app.py
```

The backend server will start on `http://localhost:5000`.

### 2. Start the Frontend

In the `frontend` directory:

```bash
npm run dev
```

The frontend application will be available at `http://localhost:5173`.

## Usage

1. Open your browser and navigate to `http://localhost:5173`.
2. Select a PDF file using the upload button.
3. Choose a parsing engine from the dropdown (e.g., PyMuPDF, pdfplumber).
4. Click "Upload & Parse".
5. The PDF preview will appear on the left, and parsing results (JSON/Markdown) on the right.

