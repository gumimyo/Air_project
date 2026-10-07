import sys
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QPushButton,
)


class DropArea(QFrame):
    # 파일이 드롭되면 파일 경로 목록을 전달
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()

        self.setAcceptDrops(True)
        self.setMinimumHeight(180)

        self.label = QLabel(
            "📂\n\n"
            "파일을 여기에 드래그하세요\n\n"
            "전송하기 전까지 이곳에서 대기합니다."
        )

        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)

        self.setLayout(layout)

        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #888;
                border-radius: 15px;
                background-color: #f5f5f5;
            }

            QLabel {
                color: #555;
                font-size: 16px;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

            self.label.setText(
                "📥\n\n"
                "여기에 놓으세요!"
            )

    def dragLeaveEvent(self, event):
        self.label.setText(
            "📂\n\n"
            "파일을 여기에 드래그하세요\n\n"
            "전송하기 전까지 이곳에서 대기합니다."
        )

    def dropEvent(self, event):

        file_paths = []

        for url in event.mimeData().urls():

            if url.isLocalFile():

                path = url.toLocalFile()

                if os.path.isfile(path):
                    file_paths.append(path)

        if file_paths:
            self.files_dropped.emit(file_paths)

        self.label.setText(
            "📂\n\n"
            "파일을 여기에 드래그하세요\n\n"
            "전송하기 전까지 이곳에서 대기합니다."
        )

        event.acceptProposedAction()


class GestureDrop(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("GestureDrop")
        self.resize(700, 600)

        # 현재 전송 대기 중인 파일
        self.waiting_files = []

        self.init_ui()

    def init_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # 제목
        title = QLabel("GestureDrop")

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            margin: 10px;
        """)

        layout.addWidget(title)

        # 설명
        description = QLabel(
            "파일을 준비하고 제스처로 전송하세요."
        )

        description.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(description)

        # 파일 드롭 영역
        self.drop_area = DropArea()

        # ⭐ 핵심
        self.drop_area.files_dropped.connect(
            self.add_files
        )

        layout.addWidget(self.drop_area)

        # 상태
        self.status_label = QLabel(
            "상태: 전송할 파일이 없습니다."
        )

        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status_label.setStyleSheet("""
            font-size: 15px;
            margin: 10px;
        """)

        layout.addWidget(self.status_label)

        # 대기 목록 제목
        waiting_title = QLabel(
            "📋 전송 대기 목록"
        )

        waiting_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            margin-top: 10px;
        """)

        layout.addWidget(waiting_title)

        # 파일 목록
        self.file_list = QListWidget()

        layout.addWidget(self.file_list)

        #파일 삭제 버튼
        self.delete_button = QPushButton("🗑 선택한 파일 삭제")

        self.delete_button.clicked.connect(
            self.remove_selected_file
        )

        layout.addWidget(self.delete_button)

    def add_files(self, files):

        for file_path in files:

            # 중복 방지
            if file_path in self.waiting_files:
                continue

            self.waiting_files.append(file_path)

            file_name = os.path.basename(file_path)

            file_size = os.path.getsize(file_path)

            # KB / MB 표시
            if file_size < 1024 * 1024:

                size_text = (
                    f"{file_size / 1024:.1f} KB"
                )

            else:

                size_text = (
                    f"{file_size / (1024 * 1024):.2f} MB"
                )

            item = QListWidgetItem(
                f"📄  {file_name}    ({size_text})"
            )

            # 나중에 실제 전송할 때 사용할 파일 경로
            item.setData(
                Qt.ItemDataRole.UserRole,
                file_path
            )

            self.file_list.addItem(item)

        self.update_status()

    def update_status(self):

        count = len(self.waiting_files)

        if count == 0:

            self.status_label.setText(
                "상태: 전송할 파일이 없습니다."
            )

        elif count == 1:

            self.status_label.setText(
                "상태: 1개 파일 전송 대기 중"
            )

        else:

            self.status_label.setText(
                f"상태: {count}개 파일 전송 대기 중"
            )
    def remove_selected_file(self):

        selected_item = self.file_list.currentItem()

        # 선택된 파일이 없으면 아무것도 하지 않음
        if selected_item is None:
            return

        # 실제 파일 경로 가져오기
        file_path = selected_item.data(
        Qt.ItemDataRole.UserRole
        )

        # 대기 목록에서 제거
        if file_path in self.waiting_files:
            self.waiting_files.remove(file_path)

        # 화면에서 제거
        row = self.file_list.row(selected_item)

        self.file_list.takeItem(row)

        # 상태 업데이트
        self.update_status()

def main():

    app = QApplication(sys.argv)

    window = GestureDrop()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()