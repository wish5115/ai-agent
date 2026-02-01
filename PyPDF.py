from langchain_community.document_loaders import PyPDFLoader
# file_path = "data/saigusa2021.pdf"
file_path = "data/存论文.pdf"
loader = PyPDFLoader(file_path)
pages = loader.load()
print(f"加载了 {len(pages)} 页PDF文档")
for page in pages:
    print(page.page_content)