

import json
import socket
import struct
from pathlib import Path

from PySide6.QtCore import QThread


HOST = "0.0.0.0"
PORT = 5000

PROJECT_DIR = Path(__file__).resolve().parents[2]
SAVE_FOLDER = PROJECT_DIR / "received_files"


def receive_exact(connection, size):
    """지정한 크기만큼 데이터를 정확하게 받기."""
    data = bytearray()

    while len(data) < size:
        chunk = connection.recv(size - len(data))

        if not chunk:
            raise ConnectionError("연결이 중간에 끊어졌습니다.")

        data.extend(chunk)

    return bytes(data)


def receive_one_file(connection):
    # 1. JSON 헤더 크기 받기
    header_size_data = receive_exact(connection, 4)
    header_size = struct.unpack("!I", header_size_data)[0]

    if header_size == 0 or header_size > 1024 * 1024:
        raise ValueError("올바르지 않은 파일 정보입니다.")

    # 2. 파일 정보 받기
    header_data = receive_exact(connection, header_size)
    header = json.loads(header_data.decode("utf-8"))

    file_name = header["file_name"]
    file_size = int(header["file_size"])

    if file_size < 0:
        raise ValueError("파일 크기가 올바르지 않습니다.")

    # 파일명만 사용해 경로 조작 방지
    file_name = file_name.replace("\\", "/").split("/")[-1]

    if not file_name:
        raise ValueError("파일 이름이 없습니다.")

    SAVE_FOLDER.mkdir(parents=True, exist_ok=True)
    save_path = SAVE_FOLDER / file_name

    received_size = 0

    try:
        with open(save_path, "wb") as file:
            while received_size < file_size:
                chunk_size = min(
                    64 * 1024,
                    file_size - received_size
                )

                data = receive_exact(connection, chunk_size)
                file.write(data)
                received_size += len(data)

        print(f"파일 수신 완료: {save_path}")

    except Exception:
        # 전송이 중간에 끊겼다면 불완전한 파일 삭제
        if save_path.exists():
            save_path.unlink()
        raise


class ReceiverThread(QThread):
    """GUI와 별도로 실행되는 TCP 파일 수신 서버."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_socket = None

    def run(self):
        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            ) as server:

                self.server_socket = server

                server.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_REUSEADDR,
                    1
                )

                server.bind((HOST, PORT))
                server.listen()

                # accept()가 무한 대기하지 않게 설정
                server.settimeout(0.5)

                print("GestureDrop 수신 서버 실행 중")
                print(f"포트: {PORT}")
                print(f"저장 폴더: {SAVE_FOLDER}")

                while not self.isInterruptionRequested():
                    try:
                        connection, address = server.accept()

                    except socket.timeout:
                        # 주기적으로 종료 요청 확인
                        continue

                    except OSError:
                        if self.isInterruptionRequested():
                            break
                        raise

                    print(f"연결됨: {address}")

                    # 현재는 한 연결씩 순서대로 처리
                    with connection:
                        # 상대가 전송 도중 멈춰도 종료 가능하도록 제한
                        connection.settimeout(2.0)

                        try:
                            receive_one_file(connection)

                        except (
                            OSError,
                            ValueError,
                            KeyError,
                            json.JSONDecodeError,
                            ConnectionError,
                        ) as error:
                            print(f"파일 수신 실패: {error}")

        except OSError as error:
            print(f"수신 서버 오류: {error}")

        finally:
            self.server_socket = None
            print("GestureDrop 수신 서버 종료")

    def stop(self):
        """서버 스레드에 안전한 종료를 요청."""
        self.requestInterruption()
