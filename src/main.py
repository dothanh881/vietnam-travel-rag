from ingestion.pdf_loader import PDFLoader

loader = PDFLoader(password=None)
docs = loader.load("dataset_builder/pdf/test.pdf")

# 3. Kiểm tra kết quả đơn giản
if __name__ == "__main__":
    if docs:
        for i,doc in enumerate(docs):
            print(f"--- Nội dung Trang {i + 1} ---")
            print(doc.page_content)
            print("-" * 30)
    else:
        print("Không có dữ liệu hoặc file lỗi.")