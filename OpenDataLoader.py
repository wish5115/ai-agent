"""
OpenDataLoader PDF 解析测试代码

⚠️ 依赖说明:
本脚本依赖 opendataloader-pdf。
该工具基于 Java (JAR) 开发，因此运行时需要安装 Java Runtime Environment (JRE)。
如果没有安装 Java，请先安装 (https://www.java.com/download/) 或使用系统包管理器 (如 brew install openjdk)。
"""
import opendataloader_pdf
import os
import shutil
import subprocess

def is_java_installed():
    """检查系统是否安装了 Java"""
    return shutil.which("java") is not None

def opendataloader_to_json(pdf_path, json_output_path):
    print(f"🚀 [OpenDataLoader] 开始极速解析: {pdf_path}")
    
    # 1. 检查 Java 环境
    if not is_java_installed():
        print("❌ [OpenDataLoader] 错误: 未检测到 Java 运行时环境。")
        print("   OpenDataLoader PDF 依赖 Java。请安装 JRE 后重试。")
        print("   下载地址: https://www.java.com/download/")
        return None
    
    try:
        # 2. 调用 convert 方法
        output_dir = os.path.dirname(json_output_path) or "."
        
        print(f"📂 输出目录: {output_dir}")
        
        result = opendataloader_pdf.convert(
            input_path=pdf_path,
            output_dir=output_dir,
            format="json"
        )
        
        print(f"✅ 转换完成，返回值类型: {type(result)}")
        # print(f"DEBUG RESULT: {result}") # 调试用
        
        # 3. 处理结果
        # result 可能是 Null (如果指定了 --output-dir 可能会写入文件而不返回内容)
        # 或者返回生成的文件路径列表
        
        generated_json_path = None
        
        # 策略：查找生成的 JSON 文件
        # OpenDataLoader 默认生成同名文件
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        potential_path = os.path.join(output_dir, base_name + ".json")
        
        # 如果 convert 返回了路径列表，在其中查找
        if isinstance(result, list):
            for item in result:
                if isinstance(item, str) and item.endswith(".json"):
                    # 简单判断，如果包含源文件名或者就在输出目录
                    if base_name in os.path.basename(item) or os.path.dirname(item) == os.path.abspath(output_dir):
                        generated_json_path = item
                        break
        
        # 如果 result 不是列表或者没找到，直接检查文件是否存在
        if not generated_json_path and os.path.exists(potential_path):
            generated_json_path = potential_path
            
        if generated_json_path:
            print(f"📄 检测到生成的 JSON 文件: {generated_json_path}")
            print(f"💾 正在保存/移动到: {json_output_path}")
            
            os.makedirs(os.path.dirname(json_output_path) if os.path.dirname(json_output_path) else '.', exist_ok=True)
            
            # 读取内容并写入目标路径 (保留原始格式)
            with open(generated_json_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            with open(json_output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 解析完成！")
            return json_output_path
        else:
            print(f"❌ 未能找到生成的 JSON 文件。")
            print(f"   检查了: {potential_path}")
            if isinstance(result, list):
                print(f"   返回列表内容: {result}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ OpenDataLoader 执行出错: {e}")
        print("   请确保 Java 运行时环境已正确安装并配置。")
        return None
    except Exception as e:
        print(f"❌ 解析过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 确保测试目录存在
    os.makedirs("data/test", exist_ok=True)
    
    input_pdf = "data/test/test-1.pdf"
    output_json = "data/test/output_opendataloader.json"
    
    if not os.path.exists(input_pdf):
        print(f"⚠️ 文件不存在: {input_pdf}")
    else:
        opendataloader_to_json(input_pdf, output_json)

