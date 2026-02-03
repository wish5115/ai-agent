import json
import os
from langchain_community.document_loaders import PyPDFLoader

def langchain_loader_to_json(pdf_path, json_output_path):
    print(f"🚀 [LangChain] 开始解析: {pdf_path}")

    # 1. 使用 PyPDFLoader 加载
    try:
        loader = PyPDFLoader(pdf_path)
        pages = loader.load() # 返回的是 LangChain 的 Document 对象列表
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return

    # 2. 构建标准 JSON 结构
    result_data = {
        "file_name": os.path.basename(pdf_path),
        "metadata": {
            "loader": "LangChain_PyPDFLoader",
            "source": pdf_path
        },
        "total_pages": len(pages),
        "pages": []
    }

    # 3. 遍历 LangChain 的 Document 对象
    for i, doc in enumerate(pages):
        # PyPDFLoader 的 metadata 通常包含 {'source': '...', 'page': 0}
        source_meta = doc.metadata
        
        page_info = {
            "page_number": source_meta.get("page", i) + 1,
            # PyPDFLoader 无法获取页面宽高，只能设为 null 或默认值
            "width": None, 
            "height": None,
            "elements": []
        }

        # --- 关键限制说明 ---
        # PyPDFLoader 将整页内容合并为一个字符串 (page_content)
        # 它不知道换行在哪里是段落，也不知道坐标 (bbox)
        # 所以我们只能把它当做一个巨大的 "Text Block" 处理
        
        if doc.page_content.strip():
            element = {
                "type": "text",
                # !注意!: pypdf 不提供坐标，所以这里只能是 null
                "bbox": None, 
                "content": doc.page_content,
                "confidence": 1.0
            }
            page_info["elements"].append(element)

        result_data["pages"].append(page_info)

    # 4. 保存为 JSON
    print(f"💾 正在保存 JSON 到: {json_output_path}")
    os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
    
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    print("✅ 完成！注意：PyPDFLoader 无法提取坐标信息。")

# --- 运行测试 ---
if __name__ == "__main__":
    # file_path = "data/saigusa2021.pdf"
    file_path = "data/test/test-1.pdf" # 请修改为你的路径
    output_json = "data/test/output_langchain.json"
    
    langchain_loader_to_json(file_path, output_json)

# from langchain_community.document_loaders import PyPDFLoader
# # file_path = "data/saigusa2021.pdf"
# file_path = "data/存论文.pdf"
# loader = PyPDFLoader(file_path)
# pages = loader.load()
# print(f"加载了 {len(pages)} 页PDF文档")
# for page in pages:
#     print(page.page_content)