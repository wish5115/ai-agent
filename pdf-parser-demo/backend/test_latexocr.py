#!/usr/bin/env python3
"""
测试 LaTeX-OCR 引擎功能
"""

import os
import sys

# 添加后端路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_latexocr_engine():
    """测试 LaTeX-OCR 引擎"""
    print("=" * 60)
    print("测试 LaTeX-OCR 引擎")
    print("=" * 60)
    
    try:
        from engines import LaTeXOCREngine, Pix2TextEngine
        
        # 检查 Pix2Text 是否可用
        try:
            from pix2text import Pix2Text, LatexOCR
            print("✓ Pix2Text 已安装")
        except ImportError as e:
            print(f"✗ Pix2Text 未安装: {e}")
            print("  请安装: pip install pix2text")
            return False
        
        # 创建引擎实例
        print("\n创建 LaTeXOCREngine 实例...")
        engine = LaTeXOCREngine()
        print("✓ LaTeXOCREngine 创建成功")
        
        print("\n创建 Pix2TextEngine 实例...")
        pix2text_engine = Pix2TextEngine()
        print("✓ Pix2TextEngine 创建成功")
        
        # 检查是否有测试 PDF
        test_pdf = "uploads/sample.pdf"
        if not os.path.exists(test_pdf):
            # 尝试查找其他测试文件
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file.endswith(".pdf"):
                        test_pdf = os.path.join(root, file)
                        print(f"\n找到测试 PDF: {test_pdf}")
                        break
                if test_pdf != "uploads/sample.pdf":
                    break
        
        if test_pdf != "uploads/sample.pdf" and os.path.exists(test_pdf):
            print(f"\n测试解析 PDF: {test_pdf}")
            print("-" * 60)
            
            # 测试解析
            result = engine.parse(test_pdf)
            
            print(f"✓ 解析完成!")
            print(f"  - 页面数: {len(result['pages'])}")
            print(f"  - 识别到的公式数: {len(result.get('formulas', []))}")
            print(f"  - 引擎类型: {result.get('engine', 'unknown')}")
            
            # 显示公式
            if result.get('formulas'):
                print("\n识别到的公式:")
                for i, formula in enumerate(result['formulas'][:5], 1):
                    print(f"  {i}. Page {formula['page']}: {formula['latex'][:50]}...")
            
            return True
        else:
            print("\n⚠ 没有找到测试 PDF 文件")
            print("  请上传一个包含数学公式的 PDF 文件进行测试")
            return True
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 60)
    print("LaTeX-OCR 引擎使用说明")
    print("=" * 60)
    print("""
1. 安装依赖:
   pip install pix2text
   
2. 在后端服务器中选择 'LaTeXOCR' 或 'Pix2Text' 引擎

3. 引擎特性:
   - LaTeXOCREngine: 使用 LatexOCR 识别数学公式图像
     * 提取 PDF 中的图像区域
     * 使用 LaTeX-OCR 转换为 LaTeX 代码
     
   - Pix2TextEngine: 使用完整的 Pix2Text 解析
     * 同时识别文本和数学公式
     * 返回标准格式的解析结果

4. API 调用示例:
   POST /upload
   - engine: 'LaTeXOCR' 或 'Pix2Text'
   - file: PDF 文件
    """)

if __name__ == "__main__":
    success = test_latexocr_engine()
    show_usage()
    
    sys.exit(0 if success else 1)

