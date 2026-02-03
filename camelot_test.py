import camelot
import pandas as pd

# 设置显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def debug_pdf_tables(pdf_path):
    print(f"🔍 正在调试文件: {pdf_path}")
    print("="*50)

    # [测试 1] Lattice 模式 (寻找线条)
    print("\n[测试 1] 尝试 'Lattice' 模式...")
    try:
        # 纯净的 lattice 调用，不带任何 extra 参数
        tables_lattice = camelot.read_pdf(pdf_path, pages='1', flavor='lattice')
        print(f"   -> 结果: 发现了 {len(tables_lattice)} 个表格")
    except Exception as e:
        print(f"   -> 报错: {e}")

    print("-" * 30)

    # [测试 2] Stream 模式 (寻找空白)
    print("\n[测试 2] 尝试 'Stream' 模式...")
    try:
        # ✅ 修正点：这里必须明确写 flavor='stream'
        # row_tol=10 是为了容忍一些行稍微有点歪的情况
        tables_stream = camelot.read_pdf(pdf_path, pages='1', flavor='stream', row_tol=10)
        
        print(f"   -> 结果: 发现了 {len(tables_stream)} 个表格")
        if len(tables_stream) > 0:
            print("\n   --- 表格预览 ---")
            print(tables_stream[0].df)
            
    except Exception as e:
        print(f"   -> 报错: {e}")

if __name__ == "__main__":
    pdf_file = "data/test/test-1.pdf"
    debug_pdf_tables(pdf_file)