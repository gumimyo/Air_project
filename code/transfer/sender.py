import socket
import json
import struct
import os
import sys


PORT = 5000


def send_file(receiver_ip, file_path):

    # 파일 존재 확인
    if not os.path.isfile(file_path):

        print("파일을 찾을 수 없습니다.")
        return

    file_name = os.path.basename(file_path)

    file_size = os.path.getsize(file_path)

    print(f"파일 이름: {file_name}")
    print(f"파일 크기: {file_size} bytes")

    # -------------------------
    # 1. 수신 PC에 연결
    # -------------------------

    client = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    print(
        f"{receiver_ip}:{PORT}에 연결 중..."
    )

    client.connect(
        (receiver_ip, PORT)
    )

    print("연결 성공!")

    # -------------------------
    # 2. 파일 정보 만들기
    # -------------------------

    header = {
        "file_name": file_name,
        "file_size": file_size
    }

    header_data = json.dumps(
        header
    ).encode("utf-8")

    # JSON의 크기
    header_size = struct.pack(
        "!I",
        len(header_data)
    )

    # 파일 정보 전송
    client.sendall(header_size)
    client.sendall(header_data)

    # -------------------------
    # 3. 파일 전송
    # -------------------------

    sent_size = 0

    with open(file_path, "rb") as file:

        while True:

            data = file.read(1024 * 64)

            if not data:
                break

            client.sendall(data)

            sent_size += len(data)

            print(
                f"\r전송 중: "
                f"{sent_size}/{file_size} bytes",
                end=""
            )

    print()
    print("파일 전송 완료!")

    client.close()


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "사용법: "
            "python sender.py [수신PC IP] [파일경로]"
        )

        sys.exit()

    receiver_ip = sys.argv[1]
    file_path = sys.argv[2]

    send_file(
        receiver_ip,
        file_path
    )