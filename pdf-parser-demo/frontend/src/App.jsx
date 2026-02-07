import { useState } from 'react'
import axios from 'axios'
// 1. 引入 react-pdf
import { Document, Page, pdfjs } from 'react-pdf'
import ReactMarkdown from 'react-markdown'

// 2. 引入样式
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './App.css'

// 3. 【核心修改】显式引入 worker 文件的 URL
// 注意：不要手动写路径字符串，让 Vite 帮你处理路径
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.js?url';

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;


function App() {
  const [file, setFile] = useState(null)
  const [engine, setEngine] = useState('PyMuPDF')
  const [pdfUrl, setPdfUrl] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('json') // 'json' or 'markdown'
  const [numPages, setNumPages] = useState(null)
  const [pageNumber, setPageNumber] = useState(1)

  const engines = [
    'PyMuPDF',
    'pdfplumber',
    'camelot',
    'docling',
    'OpenDataLoader',
    'PyPDF',
    'LaTeXOCR',
    'SimpleFormulaDetector'
  ]

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    if (e.target.files[0]) {
        setPdfUrl(URL.createObjectURL(e.target.files[0]))
        setResult(null)
        setPageNumber(1)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('engine', engine)

    try {
      // 注意：这里直接写 http://localhost:5000/upload
      //const response = await axios.post('http://localhost:5001/upload', formData)
      const response = await axios.post('/api/upload', formData)
      setResult(response.data)
      console.log(response.data)
    } catch (error) {
      console.error('Error uploading file:', error)
      alert('Failed to parse PDF')
    } finally {
      setLoading(false)
    }
  }

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages)
  }

  const renderHighlightOverlay = () => {
      if (!result || !result.result || !result.result.pages) return null;
      
      const pageData = result.result.pages.find(p => p.page_number === pageNumber);
      if (!pageData) return null;

      return (
        <div className="highlight-overlay" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
             {pageData.elements.map((el, idx) => {
                if (!el.bbox) return null;
                const isText = el.type === 'text';
                const isImage = el.type === 'image';
                const isTable = el.type === 'table';
                const isFormula = el.type === 'formula';
                
                const style = {
                    left: `${el.bbox.x * 100}%`,
                    top: `${el.bbox.y * 100}%`,
                    width: `${el.bbox.w * 100}%`,
                    height: `${el.bbox.h * 100}%`,
                    backgroundColor: isTable ? 'rgba(255, 0, 0, 0.2)' : 
                                    isImage ? 'rgba(0, 255, 0, 0.2)' : 
                                    isFormula ? 'rgba(255, 165, 0, 0.3)' : // Orange for formula
                                    'rgba(0, 0, 255, 0.1)',
                    border: isTable ? '2px solid red' : 
                            isImage ? '2px solid green' : 
                            isFormula ? '2px solid orange' :
                            '1px solid blue',
                    position: 'absolute',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '12px',
                    color: 'red', // 红色字体
                    fontWeight: 'bold',
                    overflow: 'hidden'
                }
                return <div key={idx} style={style} title={`ID: ${el.id} (${el.type})`}>{el.id}</div>
             })}
        </div>
      )
  }

  return (
    <div className="app-container">
      <header className="header">
        <h2 className="header-title">PDF Parser Demo</h2>
        <div className="controls">
          <select value={engine} onChange={(e) => {
            setEngine(e.target.value)
            if (file) handleUpload()
          }}>
            {engines.map(e => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
          <input type="file" accept="application/pdf" onChange={handleFileChange} />
          <button onClick={handleUpload} disabled={!file || loading}>
            {loading ? 'Parsing...' : 'Upload & Parse'}
          </button>
        </div>
      </header>

      <main className="main-content">
        {pdfUrl && (
          <div className="pdf-section">
             <div className="pdf-controls">
                <button onClick={() => setPageNumber(prev => Math.max(prev - 1, 1))} disabled={pageNumber <= 1}>Previous</button>
                <span>Page {pageNumber} of {numPages}</span>
                <button onClick={() => setPageNumber(prev => Math.min(prev + 1, numPages))} disabled={pageNumber >= numPages}>Next</button>
             </div>
             
             <div className="pdf-viewer-container">
                <Document
                  file={pdfUrl}
                  onLoadSuccess={onDocumentLoadSuccess}
                  className="pdf-document"
                >
                  <div style={{ position: 'relative' }}>
                      <Page 
                        pageNumber={pageNumber} 
                        renderTextLayer={false}
                        renderAnnotationLayer={false}
                        className="pdf-page"
                        width={800} // Fixed width for consistency
                      />
                      {renderHighlightOverlay()}
                  </div>
                </Document>
             </div>
             <div className="legend">
                <div className="legend-item">
                    <span className="legend-color text"></span>
                    <span>Text</span>
                </div>
                <div className="legend-item">
                    <span className="legend-color image"></span>
                    <span>Image</span>
                </div>
                <div className="legend-item">
                    <span className="legend-color table"></span>
                    <span>Table</span>
                </div>
                <div className="legend-item">
                    <span className="legend-color formula"></span>
                    <span>Formula</span>
                </div>
             </div>
          </div>
        )}

        <div className="result-section">
          <div className="tabs">
            <button 
              className={activeTab === 'json' ? 'active' : ''} 
              onClick={() => setActiveTab('json')}
            >
              JSON
            </button>
            <button 
              className={activeTab === 'markdown' ? 'active' : ''} 
              onClick={() => setActiveTab('markdown')}
            >
              Markdown
            </button>
            <button 
              className={activeTab === 'metadata' ? 'active' : ''} 
              onClick={() => setActiveTab('metadata')}
            >
              Metadata
            </button>
          </div>
          
          <div className="result-content">
            {activeTab === 'json' ? (
              <pre>{JSON.stringify(result, null, 2)}</pre>
            ) : activeTab === 'markdown' ? (
              <ReactMarkdown>
                  {result?.result?.pages?.map(p => p.elements.map(e => e.content).join('\n')).join('\n\n')}
              </ReactMarkdown>
            ) : (
              <pre>{JSON.stringify(result?.result?.metadata || {}, null, 2)}</pre>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
