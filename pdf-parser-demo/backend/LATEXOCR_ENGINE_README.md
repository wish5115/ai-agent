# LaTeX-OCR 引擎使用指南

## 概述

本项目新增了基于 Pix2Text 的 LaTeX-OCR 引擎，用于识别 PDF 中的数学公式并将其转换为 LaTeX 代码。

## 新增引擎

### 1. LaTeXOCREngine

使用 Pix2Text 的 LatexOCR 组件识别数学公式图像。

**特性:**
- 从 PDF 中提取图像区域
- 使用 LaTeX-OCR 将公式图像转换为 LaTeX 代码
- 支持内联公式检测（基于 `$` 符号）
- 返回标准格式的解析结果

### 2. Pix2TextEngine

使用完整的 Pix2Text 解析器，同时识别文本和数学公式。

**特性:**
- 一站式解析 PDF 文本和公式
- 自动布局分析
- 返回标准格式的输出

## 安装

```bash
# 使用虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install pix2text
```

## API 使用

### 请求格式

```http
POST /upload HTTP/1.1
Content-Type: multipart/form-data

engine=LaTeXOCR  # 或 'Pix2Text'
file=your.pdf
```

### 响应示例

```json
{
  "filename": "document.pdf",
  "url": "/uploads/uuid_document.pdf",
  "result": {
    "metadata": {...},
    "pages": [
      {
        "page_number": 1,
        "width": 800,
        "height": 1000,
        "elements": [
          {
            "id": 1,
            "page": 1,
            "type": "text",
            "content": "Example text",
            "bbox": {...}
          },
          {
            "id": 2,
            "page": 1,
            "type": "formula_image",
            "content": "\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}",
            "bbox": {...},
            "recognized": true
          }
        ]
      }
    ],
    "formulas": [
      {
        "id": 2,
        "page": 1,
        "latex": "\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}",
        "bbox": {...}
      }
    ],
    "engine": "latexocr"
  }
}
```

## 引擎特性详解

### LaTeXOCREngine

1. **图像提取**: 从 PDF 页面提取指定区域的图像
2. **公式识别**: 使用 LatexOCR 识别数学公式
3. **格式转换**: 将识别结果转换为 LaTeX 代码
4. **位置追踪**: 记录公式在页面中的位置信息

### Pix2TextEngine

1. **整体解析**: 一次性解析整个 PDF 页面
2. **多类型识别**: 同时识别文本、公式和表格
3. **智能布局**: 自动处理多栏布局
4. **标准输出**: 返回与其他引擎兼容的输出格式

## 依赖

- `pix2text` - Pix2Text 核心库
- `pymupdf` - PDF 处理库
- `Pillow` - 图像处理库

## 注意事项

1. **首次使用**: 首次运行时会自动下载模型文件
2. **性能考虑**: 公式识别可能需要几秒钟
3. **内存使用**: 高分辨率 PDF 可能占用较多内存
4. **CUDA 支持**: 如有 NVIDIA GPU，可加速识别过程

## 配置选项

### LaTeXOCREngine

```python
from engines import LaTeXOCREngine

# 使用 ONNX 后端（默认，推荐）
engine = LaTeXOCREngine(model_backend='onnx', device='auto')

# 使用 PyTorch 后端
engine = LaTeXOCREngine(model_backend='pytorch', device='cuda')
```

### Pix2TextEngine

```python
from engines import Pix2TextEngine

# 使用 ONNX 后端（默认）
engine = Pix2TextEngine(model_backend='onnx', device='auto')

# 使用 PyTorch 后端
engine = Pix2TextEngine(model_backend='pytorch', device='cuda')
```

## 故障排除

### 模型下载失败

如果首次运行时报错，检查网络连接。Pix2Text 需要下载预训练模型。

### 内存不足

对于大型 PDF，考虑：
- 减少页面处理数量
- 使用 `device='cpu'` 避免 GPU 内存问题
- 增加系统可用内存

### 识别不准确

- 确保公式图像清晰
- 尝试调整 PDF 渲染分辨率
- 预处理图像（调整大小、对比度等）

## 与其他引擎对比

| 特性 | LaTeXOCR | Pix2Text | PyMuPDF |
|------|----------|----------|---------|
| 公式识别 | ✓ | ✓ | 基础 |
| 文本提取 | ✓ | ✓ | ✓ |
| 表格识别 | ✗ | ✓ | ✗ |
| 速度 | 中 | 慢 | 快 |
| 准确性 | 高 | 高 | 中 |

## 示例

```python
from engines import LaTeXOCREngine

# 创建引擎实例
engine = LaTeXOCREngine()

# 解析 PDF
result = engine.parse("math_document.pdf")

# 提取所有公式
formulas = result.get('formulas', [])

for formula in formulas:
    print(f"Page {formula['page']}: {formula['latex']}")
```

