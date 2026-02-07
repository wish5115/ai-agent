"""
MathPix PDF 内容提取测试代码
参考 PyMuPDF.py 的代码结构，使用 MathPix API 提取 PDF 内容

安装依赖: pip install requests pillow
"""

import json
import os
import base64
import time
import requests
from typing import Optional
from PIL import Image


class MathPixPDFExtractor:
    """使用 MathPix API 提取 PDF 内容的封装类"""
    
    def __init__(self, app_id: str, app_key: str):
        """
        初始化 MathPix 客户端
        
        Args:
            app_id: MathPix 应用ID
            app_key: MathPix 应用密钥
        """
        self.app_id = app_id
        self.app_key = app_key
        self.api_url = "https://api.mathpix.com/v3/text"
        print("✅ MathPix 客户端初始化成功")
    
    def _call_api(self, image_path: str) -> dict:
        """
        调用 MathPix API 处理图像
        
        Args:
            image_path: 图像文件路径
        
        Returns:
            API 返回的 JSON 数据
        """
        # 读取并编码图像
        with open(image_path, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
        
        # 构建请求头
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "Content-type": "application/json"
        }
        
        # 构建请求体
        data = {
            "src": f"data:image/png;base64,{encoded_image}",
            "formats": ["text", "json"],  # 获取文本和 JSON 格式
        }
        
        # 发送请求
        response = requests.post(self.api_url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API 错误: {response.status_code} - {response.text}")
    
    def _pdf_page_to_image(self, pdf_path: str, page_num: int, dpi: int = 200) -> str:
        """
        将 PDF 页面转换为图像
        
        Args:
            pdf_path: PDF 文件路径
            page_num: 页码（从 0 开始）
            dpi: 图像分辨率
        
        Returns:
            临时图像文件路径
        """
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            
            # 将页面渲染为图像
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            
            # 保存临时图像
            temp_image_path = f"/tmp/pdf_page_{page_num}_{os.getpid()}.png"
            pix.save(temp_image_path)
            
            doc.close()
            return temp_image_path
            
        except ImportError:
            # 如果没有 PyMuPDF，使用 pdf2image
            from pdf2image import convert_from_path
            
            images = convert_from_path(pdf_path, dpi=dpi, first_page=page_num+1, last_page=page_num+1)
            if images:
                temp_image_path = f"/tmp/pdf_page_{page_num}_{os.getpid()}.png"
                images[0].save(temp_image_path)
                return temp_image_path
            raise
    
    def extract_from_file(self, pdf_path: str, output_dir: str = "output") -> dict:
        """
        从本地文件提取 PDF 内容
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
        
        Returns:
            提取结果的字典
        """
        print(f"🚀 [MathPix] 开始解析本地文件: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件不存在: {pdf_path}")
        
        file_name = os.path.basename(pdf_path)
        
        try:
            # 尝试导入 PyMuPDF 用于 PDF 到图像转换
            try:
                import fitz
            except ImportError:
                print("📦 正在安装 pdf2image...")
                os.system("/Users/wish/workspace/ai_agent/venv/bin/pip install pdf2image poppler")
                from pdf2image import convert_from_path
            
            # 获取 PDF 页数
            try:
                import fitz
                doc = fitz.open(pdf_path)
                total_pages = len(doc)
                doc.close()
            except:
                from pdf2image import convert_from_path
                images = convert_from_path(pdf_path, dpi=100)
                total_pages = len(images)
            
            print(f"📄 PDF 总页数: {total_pages}")
            
            # 构建结果结构
            result_data = {
                "file_name": file_name,
                "source": "mathpix",
                "local_path": pdf_path,
                "total_pages": total_pages,
                "pages": []
            }
            
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(file_name)[0]
            
            # 处理每一页
            for page_num in range(total_pages):
                print(f"⏳ 处理第 {page_num + 1}/{total_pages} 页...")
                
                # 将 PDF 页面转换为图像
                temp_image_path = self._pdf_page_to_image(pdf_path, page_num, dpi=150)
                
                try:
                    # 调用 MathPix API
                    result = self._call_api(temp_image_path)
                    
                    # 解析结果
                    page_data = {
                        "page_number": page_num + 1,
                        "text": result.get("text", ""),
                        "confidence": result.get("confidence", 1.0),
                        "latex": result.get("latex", []),
                    }
                    
                    result_data["pages"].append(page_data)
                    
                finally:
                    # 删除临时图像
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                
                # 避免请求过于频繁
                time.sleep(0.5)
            
            # 保存完整 JSON
            json_output_path = os.path.join(output_dir, f"{base_name}_mathpix.json")
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 JSON 已保存到: {json_output_path}")
            
            # 保存纯文本
            text_output_path = os.path.join(output_dir, f"{base_name}_mathpix.txt")
            full_text = ""
            for page in result_data["pages"]:
                full_text += f"\n\n--- Page {page['page_number']} ---\n\n{page['text']}"
            with open(text_output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            print(f"💾 文本已保存到: {text_output_path}")
            
            print("✅ MathPix 本地文件解析完成！")
            return result_data
            
        except Exception as e:
            print(f"❌ MathPix 处理失败: {e}")
            raise
    
    def extract_with_detailed_ocr(self, pdf_path: str, output_dir: str = "output") -> dict:
        """
        提取详细的 OCR 数据（包含边界框等信息）
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
        
        Returns:
            包含详细 OCR 信息的字典
        """
        print(f"🚀 [MathPix] 开始详细 OCR 解析: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件不存在: {pdf_path}")
        
        file_name = os.path.basename(pdf_path)
        
        try:
            # 尝试导入 PyMuPDF 用于 PDF 到图像转换
            try:
                import fitz
            except ImportError:
                print("📦 正在安装 pdf2image...")
                os.system("/Users/wish/workspace/ai_agent/venv/bin/pip install pdf2image poppler")
                from pdf2image import convert_from_path
            
            # 获取 PDF 页数
            try:
                import fitz
                doc = fitz.open(pdf_path)
                total_pages = len(doc)
                doc.close()
            except:
                from pdf2image import convert_from_path
                images = convert_from_path(pdf_path, dpi=100)
                total_pages = len(images)
            
            print(f"📄 PDF 总页数: {total_pages}")
            
            # 构建类似 PyMuPDF 的结构
            result_data = {
                "file_name": file_name,
                "source": "mathpix_detailed",
                "total_pages": total_pages,
                "pages": []
            }
            
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(file_name)[0]
            
            # 处理每一页
            for page_num in range(total_pages):
                print(f"⏳ 处理第 {page_num + 1}/{total_pages} 页...")
                
                # 将 PDF 页面转换为图像
                temp_image_path = self._pdf_page_to_image(pdf_path, page_num, dpi=200)
                
                try:
                    # 调用 MathPix API
                    result = self._call_api(temp_image_path)
                    
                    # 解析结果，构建类似 PyMuPDF 的结构
                    page_data = {
                        "page_number": page_num + 1,
                        "elements": []
                    }
                    
                    # 添加文本内容
                    if "text" in result:
                        text_elem = {
                            "type": "text",
                            "content": result["text"],
                        }
                        page_data["elements"].append(text_elem)
                    
                    result_data["pages"].append(page_data)
                    
                finally:
                    # 删除临时图像
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                
                # 避免请求过于频繁
                time.sleep(0.5)
            
            # 保存详细结果
            json_output_path = os.path.join(output_dir, f"{base_name}_detailed.json")
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 详细 OCR 结果已保存到: {json_output_path}")
            print("✅ MathPix 详细 OCR 解析完成！")
            
            return result_data
            
        except Exception as e:
            print(f"❌ MathPix 详细 OCR 处理失败: {e}")
            raise


def mathpix_to_json(pdf_path: str, json_output_path: str, app_id: str, app_key: str):
    """
    便捷函数：使用 MathPix 提取 PDF 内容并保存为 JSON
    
    Args:
        pdf_path: PDF 文件路径
        json_output_path: JSON 输出路径
        app_id: MathPix 应用ID
        app_key: MathPix 应用密钥
    """
    extractor = MathPixPDFExtractor(app_id, app_key)
    result = extractor.extract_from_file(pdf_path)
    
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"💾 结果已保存到: {json_output_path}")
    return result


# --- 运行测试 ---
if __name__ == "__main__":
    # 配置（请替换为你的 MathPix 凭证）
    # 申请地址: https://mathpix.com/api
    APP_ID = "your-app-id-here"
    APP_KEY = "your-app-key-here"
    
    # 测试选项
    TEST_MODE = "local"  # 选择: "local" 或 "detailed"
    
    if TEST_MODE == "local":
        # 测试本地文件模式
        input_pdf = "data/test/test-1.pdf"
        output_dir = "data/test/mathpix_output"
        
        if not os.path.exists(input_pdf):
            print(f"⚠️  测试文件不存在: {input_pdf}")
            print("请将测试 PDF 文件放在: data/test/test-1.pdf")
        else:
            extractor = MathPixPDFExtractor(APP_ID, APP_KEY)
            result = extractor.extract_from_file(input_pdf, output_dir)
            # 显示第一页的文本内容
            if result['pages']:
                first_page_text = result['pages'][0].get('text', '')[:500]
                print(f"\n📄 第一页文本预览 (前500字符):\n{first_page_text}")
    
    elif TEST_MODE == "detailed":
        # 测试详细 OCR 模式
        input_pdf = "data/test/test-1.pdf"
        output_dir = "data/test/mathpix_output"
        
        if not os.path.exists(input_pdf):
            print(f"⚠️  测试文件不存在: {input_pdf}")
        else:
            extractor = MathPixPDFExtractor(APP_ID, APP_KEY)
            result = extractor.extract_with_detailed_ocr(input_pdf, output_dir)
            print(f"\n📊 页面数: {result['total_pages']}")
            if result['pages']:
                print(f"📊 第一页元素数: {len(result['pages'][0]['elements'])}")


# MathPix vs PyMuPDF 对比总结:
# ================================
# 
# MathPix 优势:
# 1. 强大的 OCR 能力，适合扫描版 PDF
# 2. 自动识别数学公式、表格
# 3. 更好的文本结构理解
# 4. 多种输出格式支持
# 5. 支持手写识别
#
# MathPix 劣势:
# 1. 需要网络连接
# 2. 有 API 调用限制
# 3. 需要注册账号和获取密钥
# 4. 可能有延迟（需要等待处理）
#
# 使用场景:
# - 扫描版 PDF: 使用 MathPix
# - 原生 PDF: 两者皆可，PyMuPDF 更快
# - 数学/科学文档: 使用 MathPix
# - 大批量处理: 考虑使用 PyMuPDF

