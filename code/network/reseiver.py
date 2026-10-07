import socket
import json
import struct
import os

HOST = "0.0.0.0"
PORT = 5000

SAVE_FOLDER = "received_filse"


def receive_file():

    # 저장 폴더 만들기
    os.makedirs(SAVE_FOLDER, exist_ok=True)

    # 서버 소켓 생성
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    # IP와 포트에 연결
    server.bind((HOST, PORT))

    # 연결 대기
    server.listen(1)

    print("GestureDrop 파일 수신 대기 중...")
    print(f"PORT: {PORT}")

    # 송신 PC의 연결을 기다림
    connection, address = server.accept()

    print(f"연결됨: {address}")

    # -------------------------
    # 1. 파일 정보 받기
    # -------------------------

    # JSON 데이터의 크기를 먼저 받음
    header_size_data = connection.recv(4)

    if not header_size_data:
        print("파일 정보가 없습니다.")
        return

    header_size = struct.unpack(
        "!I",
        header_size_data
    )[0]

    # JSON 헤더 받기
    header_data = connection.recv(header_size)

    header = json.loads(
        header_data.decode("utf-8")
    )

    file_name = header["file_name"]
    file_size = header["file_size"]

    print(f"파일 이름: {file_name}")
    print(f"파일 크기: {file_size} bytes")

    # -------------------------
    # 2. 파일 저장
    # -------------------------

    save_path = os.path.join(
        SAVE_FOLDER,
        file_name
    )

    received_size = 0

    with open(save_path, "wb") as file:

        while received_size < file_size:

            data = connection.recv(1024 * 64)

            if not data:
                break

            file.write(data)

            received_size += len(data)

            print(
                f"\r받는 중: "
                f"{received_size}/{file_size} bytes",
                end=""
            )

    print()

    # -------------------------
    # 3. 결과 확인
    # -------------------------

    if received_size == file_size:

        print("파일 전송 완료!")
        print(f"저장 위치: {save_path}")

    else:

        print("파일 전송 실패")
        print(
            f"받은 크기: {received_size}"
        )

    connection.close()
    server.close()


if __name__ == "__main__":
    receive_file()