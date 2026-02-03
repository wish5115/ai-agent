import os
import glob
import re
import fitz  # PyMuPDF
import pdfplumber
import camelot
import pandas as pd
import numpy as np
from collections import defaultdict

# --- 配置 ---
TEST_DIR = "data/test"
REPORT_FILE = "benchmark_report.csv"

# 数学符号集 (用于公式检测)
MATH_SYMBOLS = set("αβγδεζηθικλμνξοπρστυφχψω∑∫∞≈≠≤≥±∂∇√∈∉⊂⊃∪∩")

def get_files():
    """获取所有测试PDF"""
    files = sorted(glob.glob(os.path.join(TEST_DIR, "*.pdf")))
    # 确保只取前10个（如果有更多）
    return files[:10] if len(files) > 10 else files

# ==========================================
# 1. 评估辅助函数 (Heuristics)
# ==========================================

def evaluate_text_quality(text):
    """
    评分标准: 
    1. 垃圾字符比例 (CID code, 乱码) -> 越低越好
    2. 单词长度异常比例 -> 越低越好
    """
    if not text: return 0.0
    
    # 简单的清洗
    clean_text = text.replace('\n', ' ').strip()
    if len(clean_text) == 0: return 0.0
    
    # 检测 CID 乱码 (例如 (cid:88))
    cid_matches = len(re.findall(r'\(cid:\d+\)', text))
    
    # 检测单词有效性 (简单启发式: 长度在2-15之间的字母组合比例)
    words = [w for w in clean_text.split() if w.isalpha()]
    valid_words = [w for w in words if 2 <= len(w) <= 15]
    
    word_validity_score = len(valid_words) / len(words) if words else 0
    cid_penalty = max(0, 1 - (cid_matches * 10 / len(clean_text))) # 每一个CID扣分
    
    return (word_validity_score * 0.8) + (cid_penalty * 0.2)

def evaluate_table_quality(df_list):
    """
    评分标准:
    1. 列数据一致性 (Column Consistency): 每一列的数据类型是否统一?
    """
    if not df_list: return 0.0
    
    total_consistency = 0
    total_cols = 0
    
    for df in df_list:
        if df.empty: continue
        # 跳过表头 (假设第一行是表头)
        if len(df) > 1:
            data_df = df.iloc[1:]
            for col in data_df.columns:
                col_data = data_df[col].astype(str).str.strip()
                total_cols += 1
                
                # 检查是否全是数字
                numeric_count = col_data.apply(lambda x: bool(re.match(r'^-?\d+(\.\d+)?$', x))).sum()
                ratio = numeric_count / len(col_data)
                
                # 如果这一列要么全是数字(>80%)，要么全是文本(<20%数字)，则认为是一致的
                # 如果数字和文字混杂 (e.g. 50%)，可能是解析错位
                if ratio > 0.8 or ratio < 0.2:
                    total_consistency += 1
                    
    return total_consistency / total_cols if total_cols > 0 else 0.0

def evaluate_formula_density(text):
    """
    评分标准: 数学符号在文本中的密度
    """
    if not text: return 0.0
    
    symbol_count = sum(1 for char in text if char in MATH_SYMBOLS or char in "=+")
    # 归一化：假设每页最多有 50 个数学符号算满分
    score = min(symbol_count / 20.0, 1.0)
    return score

# ==========================================
# 2. 工具处理器
# ==========================================

def analyze_pymupdf(pdf_path):
    stats = {'tool': 'PyMuPDF', 'file': os.path.basename(pdf_path)}
    full_text = ""
    img_captions_matched = 0
    img_count = 0
    
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            # --- Text ---
            text = page.get_text()
            full_text += text
            
            # --- Images (with caption check) ---
            images = page.get_images()
            img_count += len(images)
            
            # 简单的图像位置检查 (PyMuPDF 需要解析 image rect 才能做距离校验，这里简化为数量)
            # 如果要精确匹配 caption，需要获取 image bbox 和 text bbox 计算距离
            # 这里做个近似：如果页面有图且有 "Figure" 文本，算匹配
            if images and "Figure" in text:
                img_captions_matched += len(images) # 简化逻辑
                
        doc.close()
        
        stats['text_score'] = evaluate_text_quality(full_text)
        stats['formula_score'] = evaluate_formula_density(full_text)
        # PyMuPDF 不支持表格结构化提取
        stats['table_score'] = 0.0 
        stats['image_score'] = 1.0 if img_count > 0 and img_captions_matched > 0 else 0.0
        
    except Exception as e:
        print(f"[PyMuPDF] Error: {e}")
        return None
        
    return stats

def analyze_pdfplumber(pdf_path):
    stats = {'tool': 'pdfplumber', 'file': os.path.basename(pdf_path)}
    full_text = ""
    extracted_dfs = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # --- Text ---
                text = page.extract_text()
                if text: full_text += text
                
                # --- Tables ---
                tables = page.extract_tables()
                for table in tables:
                    # 转换为 DataFrame 以复用评估逻辑
                    if table:
                        clean_table = [[c if c is not None else "" for c in row] for row in table]
                        extracted_dfs.append(pd.DataFrame(clean_table))
                        
                # --- Images ---
                # pdfplumber 的 .images 通常包含 bitmap 对象
                # 注意：pdfplumber 提取图片通常不如 PyMuPDF 稳定
                
        stats['text_score'] = evaluate_text_quality(full_text)
        stats['formula_score'] = evaluate_formula_density(full_text)
        stats['table_score'] = evaluate_table_quality(extracted_dfs)
        stats['image_score'] = 0.5 # pdfplumber 图片功能较弱，给个基准分
        
    except Exception as e:
        print(f"[pdfplumber] Error: {e}")
        return None
        
    return stats

def analyze_camelot(pdf_path):
    stats = {'tool': 'Camelot', 'file': os.path.basename(pdf_path)}
    extracted_dfs = []
    
    try:
        # Camelot 只负责表格，不提取文本/公式/图片
        # 尝试 Stream 模式 (适合论文/无框线表)
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream', suppress_stdout=True)
        
        for table in tables:
            extracted_dfs.append(table.df)
            
        # 如果 Stream 没结果，尝试 Lattice
        if len(extracted_dfs) == 0:
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice', suppress_stdout=True)
            for table in tables:
                extracted_dfs.append(table.df)

        stats['text_score'] = 0.0 # 不支持
        stats['formula_score'] = 0.0 # 不支持
        stats['table_score'] = evaluate_table_quality(extracted_dfs)
        stats['image_score'] = 0.0 # 不支持
        
    except Exception as e:
        # Camelot 需要 ghostscript，如果没装会报错
        print(f"[Camelot] Error (Check Ghostscript): {e}")
        stats['table_score'] = 0.0
        
    return stats

# ==========================================
# 3. 主程序
# ==========================================

def main():
    files = get_files()
    if not files:
        print(f"❌ 未在 {TEST_DIR} 找到 PDF 文件。请先上传文件。")
        return

    print(f"🚀 开始评估 {len(files)} 个文件...")
    results = []

    for pdf_file in files:
        print(f" -> 处理: {os.path.basename(pdf_file)}")
        
        # 1. PyMuPDF
        res_fitz = analyze_pymupdf(pdf_file)
        if res_fitz: results.append(res_fitz)
        
        # 2. pdfplumber
        res_plumb = analyze_pdfplumber(pdf_file)
        if res_plumb: results.append(res_plumb)
        
        # 3. Camelot
        res_cam = analyze_camelot(pdf_file)
        if res_cam: results.append(res_cam)

    # --- 统计与输出 ---
    df_res = pd.DataFrame(results)
    
    if not df_res.empty:
        # 按工具分组取平均分
        summary = df_res.groupby('tool')[['text_score', 'table_score', 'image_score', 'formula_score']].mean()
        
        print("\n" + "="*50)
        print("📊 综合评测结果 (分数范围 0.0 - 1.0)")
        print("="*50)
        print(summary)
        print("\n说明:")
        print("- Text Score: 单词有效性与乱码率")
        print("- Table Score: 列数据类型的一致性 (结构还原度)")
        print("- Formula Score: 数学符号的提取密度")
        print("- Image Score: 图片检测与 Caption 的关联度")
        
        # 保存详细结果
        df_res.to_csv(REPORT_FILE, index=False)
        print(f"\n✅ 详细报告已保存至: {REPORT_FILE}")
    else:
        print("❌ 没有生成有效结果。")

if __name__ == "__main__":
    main()