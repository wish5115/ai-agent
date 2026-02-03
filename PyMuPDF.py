import pymupdf  # 也就是 fitz
import json
import os

def pymupdf_to_json(pdf_path, json_output_path):
    print(f"🚀 [PyMuPDF] 开始极速解析: {pdf_path}")
    
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        print(f"❌ 无法打开文件: {e}")
        return

    # 1. 初始化结果结构
    result_data = {
        "file_name": os.path.basename(pdf_path),
        "metadata": doc.metadata,  # PyMuPDF 的元数据非常完整
        "total_pages": len(doc),
        "pages": []
    }

    # 2. 遍历每一页
    for page_num, page in enumerate(doc):
        # 获取页面尺寸
        width, height = page.rect.width, page.rect.height
        
        page_info = {
            "page_number": page_num + 1,
            "width": width,
            "height": height,
            "elements": []  # 存储本页所有元素
        }

        # --- 核心：使用 "dict" 模式获取详细布局信息 ---
        # 这是一个极快的方法，一次性获取所有 文本块 和 图片块 的坐标
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            element = {}
            # PyMuPDF 的 bbox 格式为 (x0, y0, x1, y1)
            bbox = [float(x) for x in block["bbox"]]

            # --- 处理文本块 (Type 0) ---
            if block["type"] == 0:
                element["type"] = "text"
                element["bbox"] = bbox
                
                # 拼接块内的所有文字
                # block -> lines -> spans -> text
                block_text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"]
                    block_text += "\n" # 每一行加个换行符，保持段落感
                
                element["content"] = block_text.strip()
                
            # --- 处理图片块 (Type 1) ---
            elif block["type"] == 1:
                element["type"] = "image"
                element["bbox"] = bbox
                # PyMuPDF 能获取图片的元数据，如扩展名、大小
                element["content"] = f"[Image: {block.get('ext', 'unk')} - size: {block.get('width')}x{block.get('height')}]"
                element["image_info"] = {
                    "ext": block.get("ext"),
                    "width": block.get("width"),
                    "height": block.get("height"),
                    "colorspace": block.get("colorspace")
                }

            if element:
                page_info["elements"].append(element)

        # --- 额外：处理链接 (Links) ---
        # 链接通常是覆盖在文本之上的热区
        links = page.get_links()
        for link in links:
            link_elem = {
                "type": "link",
                "bbox": [float(x) for x in link["from"]], # 链接的热区坐标
                "content": link.get("uri", "") or f"Go to page {link.get('page', '')+1}",
                "link_type": link["kind"] # 1: 跳转页面, 2: 外部URL
            }
            page_info["elements"].append(link_elem)

        result_data["pages"].append(page_info)

    doc.close()

    # 3. 保存为 JSON
    print(f"💾 正在保存 JSON 到: {json_output_path}")
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    print("✅ 解析完成！")

# --- 运行测试 ---
if __name__ == "__main__":
    # 请替换文件路径
    input_pdf = "data/test/test-1.pdf"
    output_json = "data/test/output_pymupdf.json"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    pymupdf_to_json(input_pdf, output_json)


# import pymupdf
# # 打开PDF文件
# doc = pymupdf.open("data/test/test-1.pdf")
# text = [page.get_text() for page in doc]
# print(text)

# # 示例: 使用PyMuPDF的基础功能
# print("=== PyMuPDF 基本信息提取 ===")
# print(f"文档页数: {len(doc)}")
# print(f"文档标题: {doc.metadata['title']}")
# print(f"文档作者: {doc.metadata['author']}")
# print(f"文档元数据: {doc.metadata}")  # 比Unstructured提供更多元数据

# # 遍历每一页
# for page_num, page in enumerate(doc):
#     # 提取文本
#     text = page.get_text()
#     print(f"\n--- 第{page_num + 1}页 ---")
#     print("文本内容:", text[:200])  # 显示前200个字符
    
#     # 提取图片
#     images = page.get_images()
#     print(f"图片数量: {len(images)}")
    
#     # 获取页面链接
#     links = page.get_links()
#     print(f"链接数量: {len(links)}")
    
#     # 获取页面大小
#     width, height = page.rect.width, page.rect.height
#     print(f"页面尺寸: {width} x {height}")
#     print(page)

# doc.close()

# PyMuPDF (fitz) 与 Unstructured 对比:
# 优势:
# 1. 更快的处理速度
# 2. 更细粒度的PDF控制能力
# 3. 可以获取更多元数据和文档结构信息
# 4. 内存占用更少
# 5. 不依赖外部工具

# 劣势:
# 1. 文本提取的智能化程度较低
# 2. 没有自动的文档结构理解
# 3. 需要手动处理布局分析