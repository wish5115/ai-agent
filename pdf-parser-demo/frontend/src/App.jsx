import { useState, useEffect } from 'react'
import axios from 'axios'
import { Document, Page, pdfjs } from 'react-pdf'
import ReactMarkdown from 'react-markdown'

import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './App.css'

// 显式引入 worker
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.js?url';
pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

function App() {
  const [file, setFile] = useState(null)
  const [engine, setEngine] = useState('PyMuPDF')
  const [pdfUrl, setPdfUrl] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('json') 
  const [numPages, setNumPages] = useState(null)
  const [pageNumber, setPageNumber] = useState(1)
  
  // 1. 新增：控制标记显示的开关状态
  const [showAnnotations, setShowAnnotations] = useState(true)

  const engineOptions = [
    { value: 'PyMuPDF', label: 'PyMuPDF (极速 / 通用 / 阅读流)' },
    { value: 'pdfplumber', label: 'pdfplumber (精准坐标 / 表格 / 图片)' },
    { value: 'camelot', label: 'camelot (表格识别 - Stream/Lattice)' },
    { value: 'docling', label: 'docling (布局分析 / Markdown)' },
    { value: 'PyPDF', label: 'PyPDF (基础纯文本 / 按行)' },
    { value: 'LaTeXOCR', label: 'LaTeXOCR (公式识别 / 截图转LaTeX)' },
    { value: 'SimpleFormulaDetector', label: 'SimpleFormulaDetector (数学公式正则检测)' }
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

  // 2. 新增：点击标记框，跳转到 JSON 对应位置
  const scrollToElement = (id) => {
    // 如果当前不在 JSON tab，先切换过去
    if (activeTab !== 'json') {
      setActiveTab('json');
    }

    // 给一点时间让 Tab 切换完成并渲染 DOM
    setTimeout(() => {
      const targetId = `json-item-${id}`;
      const element = document.getElementById(targetId);
      if (element) {
        // 滚动到视图中间
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // 添加高亮闪烁效果
        element.classList.add('flash-highlight');
        setTimeout(() => element.classList.remove('flash-highlight'), 2000);
      } else {
        console.warn(`Element with ID ${targetId} not found in DOM.`);
      }
    }, 100);
  }

  const renderHighlightOverlay = () => {
    if (!showAnnotations) return null;
    if (!result || !result.result || !result.result.pages) return null;
    
    const pageData = result.result.pages.find(p => p.page_number === pageNumber);
    if (!pageData) return null;

    return (
      <div className="highlight-overlay">
           {pageData.elements.map((el, idx) => {
              if (!el.bbox) return null;
              
              // --- 1. 定义边框和背景色 (根据类型区分) ---
              let borderColor, backgroundColor;

              switch (el.type) {
                  case 'table':
                      borderColor = 'red';   // 表格：红色边框
                      backgroundColor = 'rgba(255, 0, 0, 0.1)';
                      break;
                  case 'image':
                      borderColor = 'green'; // 图片：绿色边框
                      backgroundColor = 'rgba(0, 255, 0, 0.1)';
                      break;
                  case 'formula':
                      borderColor = 'orange'; // 公式：橙色边框
                      backgroundColor = 'rgba(255, 165, 0, 0.1)';
                      break;
                  case 'text':
                  default:
                      borderColor = 'blue';  // 文本：蓝色边框
                      backgroundColor = 'rgba(0, 0, 255, 0.05)';
                      break;
              }

              const style = {
                  left: `${el.bbox.x * 100}%`,
                  top: `${el.bbox.y * 100}%`,
                  width: `${el.bbox.w * 100}%`,
                  height: `${el.bbox.h * 100}%`,
                  
                  // 应用上面定义的动态颜色
                  border: `1px solid ${borderColor}`,
                  backgroundColor: backgroundColor,
                  
                  // --- 2. 关键修改：序号文字始终为红色 ---
                  color: 'red', 
                  
                  position: 'absolute',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  fontWeight: 'bold',
                  overflow: 'hidden',
                  cursor: 'pointer',
                  zIndex: 10
              }
              
              return (
                <div 
                  key={idx} 
                  style={style} 
                  title={`ID: ${el.id} (${el.type})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    scrollToElement(el.id);
                  }}
                >
                  {el.id}
                </div>
              )
           })}
      </div>
    )
  }

  // 5. 新增：特殊的 JSON 渲染器
  // 为了能让 scrollIntoView 工作，我们需要把每个 element 渲染成独立的带 ID 的 DOM 节点
  const renderJsonView = () => {
    if (!result || !result.result) return <pre>No data</pre>;

    // 提取顶层属性（不包含 pages，避免重复）
    const { pages, ...topLevel } = result.result;

    return (
      <div className="json-viewer">
        <div className="json-block">
          {/* 渲染顶层元数据 */}
          <pre>{JSON.stringify({ 
            filename: result.filename, 
            ...topLevel 
          }, null, 2).slice(0, -1)}</pre>
          
          {/* 手动渲染 Pages 数组以注入 ID */}
          <div className="json-key">  "pages": [</div>
          {pages.map((page, pIdx) => (
            <div key={pIdx} className="json-page-block">
              <div className="json-indent">{`{`}</div>
              <div className="json-indent-2">
                <div>"page_number": {page.page_number},</div>
                <div>"width": {page.width},</div>
                <div>"height": {page.height},</div>
                <div>"elements": [</div>
                
                {/* 渲染 Elements */}
                {page.elements.map((el, eIdx) => (
                  <div 
                    key={el.id} 
                    id={`json-item-${el.id}`} // 关键：这是锚点 ID
                    className="json-element-item"
                  >
                    {/* 使用 JSON.stringify 渲染单个元素对象 */}
                    <pre style={{margin: 0, display: 'inline-block'}}>
                      {JSON.stringify(el, null, 2)}
                    </pre>
                    {eIdx < page.elements.length - 1 ? ',' : ''}
                  </div>
                ))}
                
                <div>]</div>
              </div>
              <div className="json-indent">{`}`}{pIdx < pages.length - 1 ? ',' : ''}</div>
            </div>
          ))}
          <div>  ]</div>
          <div>{`}`}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="header">
        <h2 className="header-title">PDF Parser Demo</h2>
        <div className="controls">
          <select 
            value={engine} 
            onChange={(e) => setEngine(e.target.value)}
            style={{ minWidth: '250px' }}
          >
            {engineOptions.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
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
                
                {/* 6. 新增：显隐控制按钮 */}
                <div style={{ width: '20px' }}></div> {/* Spacer */}
                <button 
                  onClick={() => setShowAnnotations(!showAnnotations)}
                  style={{ 
                    backgroundColor: showAnnotations ? '#e0e0e0' : '#007bff',
                    color: showAnnotations ? '#333' : '#fff',
                    borderColor: '#ccc'
                  }}
                >
                  {showAnnotations ? 'Hide Marks' : 'Show Marks'}
                </button>
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
                        width={800}
                      />
                      {renderHighlightOverlay()}
                  </div>
                </Document>
             </div>
             <div className="legend">
                <div className="legend-item"><span className="legend-color text"></span><span>Text</span></div>
                <div className="legend-item"><span className="legend-color image"></span><span>Image</span></div>
                <div className="legend-item"><span className="legend-color table"></span><span>Table</span></div>
                <div className="legend-item"><span className="legend-color formula"></span><span>Formula</span></div>
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
              // 使用新的渲染函数
              renderJsonView()
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