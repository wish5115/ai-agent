import os
import random
import subprocess
import shutil
import re
import json
import jinja2
from faker import Faker
from PIL import Image, ImageDraw

# =================配置区域=================
OUTPUT_DIR = "labeled_dataset_stable"
NUM_DOCS = 10
PAGE_HEIGHT_PT = 841.89
PAGE_WIDTH_PT = 595.28
# =========================================

fake = Faker()

# ---------------------------------------------------------
# 1. LaTeX 模板 (使用 \VAR{...} 风格)
# ---------------------------------------------------------
# 注意：这里我们使用 LaTeX 友好的语法，避免 {} 冲突
latex_template = r"""
\documentclass[\VAR{layout_mode}, a4paper, 12pt]{article}

\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{float}
\usepackage[margin=2.5cm]{geometry}
\usepackage{fancyhdr}
\usepackage{zref-savepos}
\usepackage{zref-user}

% --- 定义坐标追踪宏 ---
\newcounter{elemCount}
\newcommand{\traceElement}[2]{%
    \stepcounter{elemCount}%
    \zsaveposy{top:\theelemCount}%
    \zsaveposx{left:\theelemCount}%
    #2%
    \zsaveposy{bottom:\theelemCount}%
    \zsaveposx{right:\theelemCount}%
    \zlabel{meta:\theelemCount:#1}%
}

% --- 页面设置 ---
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\traceElement{header}{\VAR{header_text}}}
\fancyhead[R]{\thepage}
\fancyfoot[C]{\traceElement{footer}{\VAR{footer_text}}}

\title{\traceElement{title}{\VAR{title}}}
\author{\traceElement{author}{\VAR{author}}}
\date{\traceElement{date}{\VAR{date}}}

\begin{document}

\maketitle

\begin{abstract}
\traceElement{abstract}{This is a generated document ID: \VAR{doc_id}. It contains ground truth annotations.}
\end{abstract}

\BLOCK{for section in sections}
\section{\traceElement{section_header}{\VAR{section.title}}}

\traceElement{paragraph}{\VAR{section.content}}

\BLOCK{if section.has_list}
\traceElement{list}{
    \begin{itemize}
        \BLOCK{for item in section.list_items}
        \item \VAR{item}
        \BLOCK{endfor}
    \end{itemize}
}
\BLOCK{endif}

\BLOCK{if section.has_formula}
\traceElement{formula}{
    \begin{equation}
        f(x) = \alpha x^2 + \beta
    \end{equation}
}
\BLOCK{endif}

\BLOCK{if section.has_table}
\traceElement{table}{
    \begin{table}[H]
        \centering
        \caption{\VAR{section.table_caption}}
        \begin{tabular}{l c r}
            \toprule
            Item & Value & Rate \\
            \midrule
            Data A & 10 & 0.5 \\
            Data B & 20 & 0.8 \\
            \bottomrule
        \end{tabular}
    \end{table}
}
\BLOCK{endif}

\BLOCK{if section.has_image}
\traceElement{image}{
    \begin{figure}[H]
        \centering
        \includegraphics[width=0.6\linewidth]{\VAR{section.image_file}}
        \caption{\VAR{section.image_caption}}
    \end{figure}
}
\BLOCK{endif}

\BLOCK{endfor}

\end{document}
"""

# ---------------------------------------------------------
# 2. 辅助函数
# ---------------------------------------------------------
def parse_aux_labels(aux_file_path):
    if not os.path.exists(aux_file_path):
        return []

    elements = {}
    with open(aux_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 提取坐标
    pos_pattern = re.compile(r'\\zref@newlabel\{(top|bottom|left|right):(\d+)\}.*?\\pos[xy]\{(\d+)\}')
    meta_pattern = re.compile(r'\\zref@newlabel\{meta:(\d+):([a-zA-Z_]+)\}.*?\\page\{(\d+)\}')

    for match in pos_pattern.finditer(content):
        pos_type, eid, val = match.groups()
        if eid not in elements: elements[eid] = {}
        elements[eid][pos_type] = int(val) / 65536.0

    # 组装结果
    results = []
    for match in meta_pattern.finditer(content):
        eid, label_type, page = match.groups()
        if eid in elements:
            coords = elements[eid]
            if all(k in coords for k in ['top', 'bottom', 'left', 'right']):
                x1 = coords['left']
                x2 = coords['right']
                y_top = coords['top']
                y_bottom = coords['bottom']
                
                # 转换坐标系: LaTeX (左下原点) -> PDF (左上原点)
                # PDF Y = PageHeight - LaTeX Y
                cv_y1 = PAGE_HEIGHT_PT - y_top
                cv_y2 = PAGE_HEIGHT_PT - y_bottom
                
                # 确保 w, h 为正数
                width = abs(x2 - x1)
                height = abs(cv_y2 - cv_y1)
                
                # 过滤极小的无效框
                if width > 1 and height > 1:
                    results.append({
                        "id": int(eid),
                        "label": label_type,
                        "page": int(page),
                        "bbox": [round(x1, 2), round(cv_y1, 2), round(width, 2), round(height, 2)]
                    })
    return sorted(results, key=lambda x: x['id'])

def create_dummy_image(filename):
    img = Image.new('RGB', (400, 200), color=(random.randint(200,240), random.randint(200,240), random.randint(200,240)))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 390, 190], outline="black")
    d.text((20, 90), "GROUND TRUTH", fill="black")
    img.save(os.path.join(OUTPUT_DIR, filename))

# ---------------------------------------------------------
# 3. 主程序
# ---------------------------------------------------------
def generate_dataset():
    # 重新创建输出目录
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 【核心修复】：使用 raw string (r'') 定义配置，防止 Python 转义干扰
    env = jinja2.Environment(
        block_start_string=r'\BLOCK{',
        block_end_string=r'}',
        variable_start_string=r'\VAR{',
        variable_end_string=r'}',
        comment_start_string=r'\COMMENT{',
        comment_end_string=r'}',
        loader=jinja2.BaseLoader(),
        autoescape=False
    )
    
    try:
        template = env.from_string(latex_template)
    except Exception as e:
        print(f"🔥 模板编译失败: {e}")
        return

    print(f"🚀 开始生成 {NUM_DOCS} 个带标注的 PDF (稳定版)...")

    for i in range(1, NUM_DOCS + 1):
        doc_id = f"DOC_{i:03d}"
        
        # 准备数据
        sections = []
        for _ in range(3):
            img_file = f"img_{doc_id}_{len(sections)}.png"
            create_dummy_image(img_file)
            sections.append({
                "title": fake.bs().title(),
                "content": fake.paragraph(nb_sentences=8),
                "has_list": random.choice([True, False]),
                "list_items": [fake.word() for _ in range(3)],
                "has_formula": random.choice([True, False]),
                "has_table": random.choice([True, False]),
                "table_caption": fake.sentence(),
                "has_image": random.choice([True, False]),
                "image_file": img_file,
                "image_caption": fake.sentence()
            })

        context = {
            "layout_mode": "onecolumn",
            "title": fake.catch_phrase(),
            "author": fake.name(),
            "date": fake.date(),
            "doc_id": doc_id,
            "header_text": f"CONFIDENTIAL - {doc_id}",
            "footer_text": f"Generated by AutoLabeler - Page \\thepage",
            "sections": sections
        }

        # 渲染 LaTeX
        tex_content = template.render(**context)
        tex_file = os.path.join(OUTPUT_DIR, f"{doc_id}.tex")
        
        with open(tex_file, "w", encoding='utf-8') as f:
            f.write(tex_content)

        print(f"[{i}/{NUM_DOCS}] 正在编译 {doc_id}...")
        try:
            # 编译 PDF (运行两次以确保坐标正确)
            cmd = ["pdflatex", "-interaction=nonstopmode", f"{doc_id}.tex"]
            subprocess.run(cmd, cwd=OUTPUT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(cmd, cwd=OUTPUT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 提取标注
            aux_file = os.path.join(OUTPUT_DIR, f"{doc_id}.aux")
            annotations = parse_aux_labels(aux_file)
            
            if not annotations:
                print(f"⚠️  警告: {doc_id} 未提取到标注信息，可能是编译出错。")
            
            # 保存真值 JSON
            json_file = os.path.join(OUTPUT_DIR, f"{doc_id}.json")
            with open(json_file, "w") as f:
                json.dump({
                    "doc_id": doc_id,
                    "page_size": [PAGE_WIDTH_PT, PAGE_HEIGHT_PT],
                    "annotations": annotations
                }, f, indent=4)
                
        except Exception as e:
            print(f"❌ 处理 {doc_id} 时出错: {e}")

    # 清理临时文件
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(('.aux', '.log', '.out')):
            os.remove(os.path.join(OUTPUT_DIR, f))

    print(f"\n✅ 全部完成！输出目录: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    generate_dataset()