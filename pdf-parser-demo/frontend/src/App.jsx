import { useState } from 'react'
import axios from 'axios'
import { Document, Page, pdfjs } from 'react-pdf'
import ReactMarkdown from 'react-markdown'
import './App.css'

// Set worker script for react-pdf
// Using a CDN for reliability in this demo setup
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

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
    'PyPDF'
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
                const style = {
                    left: `${el.bbox.x * 100}%`,
                    top: `${el.bbox.y * 100}%`,
                    width: `${el.bbox.w * 100}%`,
                    height: `${el.bbox.h * 100}%`,
                    backgroundColor: el.type === 'table' ? 'rgba(255, 0, 0, 0.2)' : 
                                    el.type === 'image' ? 'rgba(0, 255, 0, 0.2)' : 
                                    'rgba(0, 0, 255, 0.1)',
                    border: '1px solid red',
                    position: 'absolute',
                }
                return <div key={idx} style={style} title={el.type} />
             })}
        </div>
      )
  }

  return (
    <div className="app-container">
      <h1 className="header-title">PDF Parser Demo</h1>
      <header className="header">
        <div className="controls">
          <select value={engine} onChange={(e) => setEngine(e.target.value)}>
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
          </div>
          
          <div className="result-content">
            {activeTab === 'json' ? (
              <pre>{JSON.stringify(result, null, 2)}</pre>
            ) : (
              <ReactMarkdown>
                  {result?.result?.pages?.map(p => p.elements.map(e => e.content).join('\n')).join('\n\n')}
              </ReactMarkdown>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
