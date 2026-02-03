import pdfplumber
import json
import os
from decimal import Decimal

# --- 辅助工具：处理 JSON 无法序列化 Decimal 类型的问题 ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # 将 Decimal 转为 float
        return super(DecimalEncoder, self).default(obj)

def pdf_to_json(pdf_path, json_output_path):
    print(f"🚀 开始解析 PDF: {pdf_path}")
    
    result_data = {
        "file_name": os.path.basename(pdf_path),
        "metadata": {},
        "pages": []
    }

    with pdfplumber.open(pdf_path) as pdf:
        # 1. 获取文档元数据
        if pdf.metadata:
            result_data["metadata"] = pdf.metadata

        # 2. 遍历每一页
        for i, page in enumerate(pdf.pages):
            page_info = {
                "page_number": i + 1,
                "width": float(page.width),
                "height": float(page.height),
                "elements": []  # 存储所有的内容元素（表格、文本）
            }

            print(f"   -> 正在处理第 {i + 1} 页...")

            # --- A. 提取表格 (带坐标) ---
            # 使用 find_tables() 而不是 extract_tables()，因为我们需要 bbox
            tables = page.find_tables()
            for table in tables:
                table_data = {
                    "type": "table",
                    "bbox": [float(x) for x in table.bbox], # (x0, top, x1, bottom)
                    "content": table.extract(), # 提取表格里的文字内容 List[List[str]]
                    "confidence": 1.0 # 传统方法置信度通常设为 1
                }
                page_info["elements"].append(table_data)

            # --- B. 提取文本 (带坐标) ---
            # extract_words 返回每个词的详细信息：{'text': '..', 'x0': .., 'top': ..}
            words = page.extract_words(keep_blank_chars=False)
            
            # 为了防止 JSON 太大，这里我们可以选择把相邻的词拼成句子（简单逻辑），
            # 或者直接存储每个词。这里为了演示“精确坐标”，我们存储单词级数据。
            # 实际生产中，通常会写个算法把同一行的 word 合并成 line。
            
            for word in words:
                text_element = {
                    "type": "text",
                    # 统一坐标格式: [x0, top, x1, bottom]
                    "bbox": [
                        float(word['x0']), 
                        float(word['top']), 
                        float(word['x1']), 
                        float(word['bottom'])
                    ],
                    "content": word['text'],
                    # 还可以包含字体大小等信息，辅助判断标题
                    # "font_size": float(word.get('size', 0)) 
                }
                page_info["elements"].append(text_element)

            result_data["pages"].append(page_info)

    # 3. 写入 JSON 文件
    print(f"💾 正在保存 JSON 到: {json_output_path}")
    with open(json_output_path, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 保证中文正常显示
        json.dump(result_data, f, cls=DecimalEncoder, indent=2, ensure_ascii=False)
    
    print("✅ 完成！")

# --- 运行示例 ---
if __name__ == "__main__":
    # 请替换为你的 PDF 路径
    input_pdf = "data/test/test-1.pdf"  
    output_json = "data/test/output_pdfplumber.json"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    try:
        pdf_to_json(input_pdf, output_json)
    except Exception as e:
        print(f"❌ 错误: {e}")