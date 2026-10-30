import sys
import os
import ipaddress

from transfer.gesture_worker import GestureWorker
from transfer.receiver import ReceiverThread
from PySide6.QtCore import Qt, Signal, QThread
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
    QLineEdit,
)

# 기존 TCP 송신 함수를 가져옴
from network.sender import send_file


class SendFileThread(QThread):
    """파일 전송을 GUI와 별도로 실행하는 스레드."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, receiver_ip, file_path):
        super().__init__()
        self.receiver_ip = receiver_ip
        self.file_path = file_path

    def run(self):
        try:
            send_file(self.receiver_ip, self.file_path)

            # 주의: 현재는 수신 PC의 저장 완료 응답을 확인하지 않음.
            self.succeeded.emit(
                "송신 완료! (수신 저장 여부는 별도 확인 필요)"
            )

        except Exception as error:
            self.failed.emit(str(error))


class DropArea(QFrame):
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
            self.label.setText("📥\n\n여기에 놓으세요!")

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
        self.resize(700, 650)

        self.waiting_files = []
        self.send_thread = None

        self.init_ui()

        # 수신 서버를 백그라운드에서 시작
        self.receiver_thread = ReceiverThread(self)
        self.receiver_thread.start()
        self.gesture_worker = GestureWorker(self)

        self.gesture_worker.status_changed.connect(
            self.gesture_status_label.setText
        )

        self.gesture_worker.trigger_detected.connect(
            self.on_gesture_triggered
        )

        self.gesture_worker.start()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # 제목
        title = QLabel("GestureDrop")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.gesture_status_label = QLabel(
            "제스처: 카메라를 준비하고 있습니다."
        )
        self.gesture_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.gesture_status_label)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        # 파일 드롭 영역
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.add_files)
        layout.addWidget(self.drop_area)

        # 대기 상태
        self.status_label = QLabel(
            "상태: 전송할 파일이 없습니다."
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 15px;
            margin: 10px;
        """)
        layout.addWidget(self.status_label)

        # 대기 목록
        waiting_title = QLabel("📋 전송 대기 목록")
        waiting_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            margin-top: 10px;
        """)
        layout.addWidget(waiting_title)

        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        # 파일 삭제
        self.delete_button = QPushButton("🗑 선택한 파일 삭제")
        self.delete_button.clicked.connect(
            self.remove_selected_file
        )
        layout.addWidget(self.delete_button)

        # 수신 PC IP 입력
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText(
            "수신 PC IP 주소 (예: 192.168.0.20)"
        )
        self.ip_input.setText("127.0.0.1")
        layout.addWidget(self.ip_input)

        # 전송 버튼
        self.send_button = QPushButton("📤 선택한 파일 전송")
        self.send_button.clicked.connect(
            self.send_selected_file
        )
        layout.addWidget(self.send_button)

        # 전송 결과
        self.transfer_status_label = QLabel(
            "전송 상태: 대기 중"
        )
        self.transfer_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.transfer_status_label)

    def add_files(self, files):
        for file_path in files:
            if file_path in self.waiting_files:
                continue

            self.waiting_files.append(file_path)

            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            if file_size < 1024 * 1024:
                size_text = f"{file_size / 1024:.1f} KB"
            else:
                size_text = (
                    f"{file_size / (1024 * 1024):.2f} MB"
                )

            item = QListWidgetItem(
                f"📄  {file_name}    ({size_text})"
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                file_path
            )
            self.file_list.addItem(item)

        self.update_status()

    def update_status(self):
        count = len(self.waiting_files)

        if count == 0:
            message = "상태: 전송할 파일이 없습니다."
        elif count == 1:
            message = "상태: 1개 파일 전송 대기 중"
        else:
            message = f"상태: {count}개 파일 전송 대기 중"

        self.status_label.setText(message)

    def remove_selected_file(self):
        selected_item = self.file_list.currentItem()

        if selected_item is None:
            self.transfer_status_label.setText(
                "전송 상태: 삭제할 파일을 먼저 선택하세요."
            )
            return

        file_path = selected_item.data(
            Qt.ItemDataRole.UserRole
        )

        if file_path in self.waiting_files:
            self.waiting_files.remove(file_path)

        row = self.file_list.row(selected_item)
        self.file_list.takeItem(row)

        self.update_status()

    def send_selected_file(self):
        # 이미 전송 중이면 중복 실행 방지
        if self.send_thread is not None and self.send_thread.isRunning():
            return

        selected_item = self.file_list.currentItem()

        if selected_item is None:
            self.transfer_status_label.setText(
                "전송 상태: 전송할 파일을 선택하세요."
            )
            return

        receiver_ip = self.ip_input.text().strip()

        try:
            ipaddress.ip_address(receiver_ip)
        except ValueError:
            self.transfer_status_label.setText(
                "전송 상태: 올바른 IP 주소를 입력하세요."
            )
            return

        file_path = selected_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not os.path.isfile(file_path):
            self.transfer_status_label.setText(
                "전송 상태: 원본 파일을 찾을 수 없습니다."
            )
            return

        self.transfer_status_label.setText(
            f"전송 상태: {os.path.basename(file_path)} 전송 중..."
        )

        self.send_button.setEnabled(False)

        self.send_thread = SendFileThread(
            receiver_ip,
            file_path
        )

        self.send_thread.succeeded.connect(
            self.on_send_success
        )
        self.send_thread.failed.connect(
            self.on_send_failure
        )
        self.send_thread.finished.connect(
            self.on_send_finished
        )

        self.send_thread.start()

    def on_send_success(self, message):
        self.transfer_status_label.setText(
            f"전송 상태: {message}"
        )

    def on_send_failure(self, error):
        self.transfer_status_label.setText(
            f"전송 실패: {error}"
        )

    def on_send_finished(self):
        self.send_button.setEnabled(True)

    def closeEvent(self, event):
        self.gesture_worker.stop()
        self.gesture_worker.wait()

        self.receiver_thread.stop()
        self.receiver_thread.wait()

        event.accept()
    def on_gesture_triggered(self):
        self.gesture_status_label.setText(
            "전송 요청 감지! (테스트 모드)"
        )
        self.gesture_status_label.setStyleSheet(
            "color: green; font-weight: bold; font-size: 18px;"
        )

def main():
    app = QApplication(sys.argv)

    window = GestureDrop()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
