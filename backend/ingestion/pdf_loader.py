from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


class PDFLoader:
    """
     class load pdf
    """

    def __init__(self, extract_images: bool = False, password: Optional[str] = None):
        """
        Khởi tạo PDFLoader.
        """
        self.extract_images = extract_images
        self.password = password

    def load(self, path: str) -> List[Document]:
        """
        trả về danh sách các đối tượng Document.

        Args:
            path: Đường dẫn đến tệp PDF.

        Returns:
            List[Document]: Danh sách các tài liệu LangChain.
        """

        # Khởi tạo loader với mật khẩu nếu có
        # PyPDFLoader sử dụng thư viện pypdf bên dưới để xử lý
        loader = PyPDFLoader(path, password=self.password)

        try:
            # Thực hiện tải và phân trang tự động
            documents: List[Document] = loader.load()

            # Nếu cần xử lý logic extract_images ở đây trong tương lai,
            # bạn có thể thêm các hàm xử lý hậu kỳ (post-processing).

            return documents
        except Exception as e:
            print(f"Lỗi khi tải tệp PDF tại {path}: {e}")
            return []

