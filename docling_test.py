"""
Docling PDF 解析测试代码 (修复版 - 适配 Docling v2+)
"""

import json
import os
from typing import Dict, Any

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DoclingDocument
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

def docling_to_json(
    pdf_path: str, 
    json_output_path: str,
    extract_images: bool = True,
    extract_tables: bool = True,
    ocr_enabled: bool = False
) -> Dict[str, Any]:
    """
    使用 Docling 解析 PDF 并转换为 JSON 格式
    """
    print(f"🚀 [Docling] 开始解析: {pdf_path}")
    
    try:
        # --- 1. 配置 Pipeline 选项 (API 修正) ---
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = ocr_enabled
        pipeline_options.do_table_structure = extract_tables
        
        # 如果需要提取图片，设置 scale (默认是 0 即不生成，设置为 1.0 或 2.0 生成)
        if extract_images:
            pipeline_options.images_scale = 1.0 
            pipeline_options.generate_page_images = True
        
        # --- 2. 创建文档转换器 ---
        # 注意：这里需要使用 PdfFormatOption 包装 pipeline_options
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        
        # --- 3. 解析 PDF ---
        # convert 返回的是 ConversionResult 对象
        result = converter.convert(pdf_path)
        
        # --- 4. 检查结果 (API 修正) ---
        # 新版没有 result.success，直接获取 document，如果有严重错误通常在 convert 时已抛出异常
        if not result.document:
             print(f"❌ PDF 解析未返回文档对象")
             return {"error": "No document returned"}

        doc: DoclingDocument = result.document
        
        # 构建结果结构
        result_data = {
            "file_name": os.path.basename(pdf_path),
            "metadata": {
                # 注意：部分元数据字段可能为 None，需做安全处理
                "title": doc.name or "",  # meta.doc_title 可能变为 name
                "page_count": len(doc.pages) if hasattr(doc, 'pages') else 0,
            },
            "pages": []
        }
        
        # 简单地序列化 Docling 原生 JSON 结构 (推荐)
        # Docling v2 的 export_to_dict() 包含了非常详尽的信息
        print(f"💾 正在保存 JSON 到: {json_output_path}")
        os.makedirs(os.path.dirname(json_output_path) if os.path.dirname(json_output_path) else '.', exist_ok=True)
        
        # 直接导出 Docling 的标准 JSON 格式
        with open(json_output_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(doc.export_to_dict(), indent=2, ensure_ascii=False))
        
        print(f"✅ Docling 解析完成！")
        return result_data
        
    except Exception as e:
        print(f"❌ 解析过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def docling_to_markdown(pdf_path: str, md_output_path: str = None) -> str:
    """
    使用 Docling 提取 Markdown 格式
    """
    print(f"🚀 [Docling] 提取 Markdown: {pdf_path}")
    
    try:
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        
        # 修正：移除 result.success 判断
        if result.document:
            md_text = result.document.export_to_markdown()
            
            if md_output_path:
                print(f"💾 正在保存 Markdown 到: {md_output_path}")
                os.makedirs(os.path.dirname(md_output_path) if os.path.dirname(md_output_path) else '.', exist_ok=True)
                
                with open(md_output_path, 'w', encoding='utf-8') as f:
                    f.write(md_text)
            
            print(f"✅ Markdown 提取完成！")
            return md_text
        else:
            print(f"❌ Markdown 提取失败: 未能生成 Document 对象")
            return ""
            
    except Exception as e:
        print(f"❌ 提取过程中出错: {e}")
        return ""


def docling_to_text(pdf_path: str, txt_output_path: str = None) -> str:
    """
    使用 Docling 提取纯文本格式
    """
    print(f"🚀 [Docling] 提取纯文本: {pdf_path}")
    
    try:
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        
        # 修正：移除 result.success 判断
        if result.document:
            # Docling 没有直接的 export_to_text，通常用 Markdown 替代或手动遍历
            # 但 export_to_markdown 已经非常接近纯文本（如果忽略格式符号）
            # 或者我们可以尝试 render_text (如果版本支持)
            try:
                # 尝试 v2 新 API 或回退到 Markdown
                txt_text = result.document.export_to_markdown(strict_text=True) 
            except TypeError:
                 # 如果不支持 strict_text 参数，直接用 md
                 txt_text = result.document.export_to_markdown()

            if txt_output_path:
                print(f"💾 正在保存文本到: {txt_output_path}")
                os.makedirs(os.path.dirname(txt_output_path) if os.path.dirname(txt_output_path) else '.', exist_ok=True)
                
                with open(txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(txt_text)
            
            print(f"✅ 纯文本提取完成！")
            return txt_text
        else:
            print(f"❌ 纯文本提取失败")
            return ""
            
    except Exception as e:
        print(f"❌ 提取过程中出错: {e}")
        return ""


# --- 运行测试 ---
if __name__ == "__main__":
    # 确保测试目录存在
    os.makedirs("data/test", exist_ok=True)
    
    # 请确保此文件存在，或者修改为实际存在的 PDF 路径
    input_pdf = "data/test/test-1.pdf" 
    output_json = "data/test/output_docling.json"
    output_md = "data/test/output_docling.md"
    output_txt = "data/test/output_docling.txt"
    
    if not os.path.exists(input_pdf):
        print(f"⚠️ 文件不存在: {input_pdf}，请先创建一个测试 PDF。")
    else:
        # 1. 解析为 JSON
        result = docling_to_json(
            pdf_path=input_pdf,
            json_output_path=output_json,
            extract_images=True,
            extract_tables=True,
            ocr_enabled=False 
        )
        
        # 2. 提取 Markdown
        md_content = docling_to_markdown(input_pdf, output_md)
        
        # 3. 提取纯文本
        txt_content = docling_to_text(input_pdf, output_txt)
        
        if md_content:
            print("\n📄 Markdown 预览（前500字符）:")
            print("-" * 50)
            print(md_content[:500])
            print("-" * 50)