import socket
import json
import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
from collections import deque
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# UDP 서버 설정
UDP_IP = "192.168.0.10"  # 서버 IP 주소
UDP_PORT = 3333  # 포트 번호

# 데이터 저장을 위한 딕셔너리와 데이터 큐
devices = {}
data_queue = deque(maxlen=100)  # 최대 100개의 최근 데이터 포인트 저장

# 그래프 초기화
fig, ax = plt.subplots()
scatter = ax.scatter([], [], animated=True)
texts = []
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_title("Device Positions")
ax.set_xlabel("X (m)")
ax.set_ylabel("Y (m)")

def update_plot(_):
    """플롯 업데이트 함수"""
    global texts
    for text in texts:
        text.remove()
    texts = []
    
    x = [dev['position'][0] for dev in devices.values()]
    y = [dev['position'][1] for dev in devices.values()]
    if x and y:
        scatter.set_offsets(list(zip(x, y)))
        for i, (addr, dev) in enumerate(devices.items()):
            texts.append(ax.annotate(f"{addr} ({dev['role']})", (x[i], y[i])))
    return scatter, *texts

def validate_distance(distance):
    """거리 데이터 유효성 검사"""
    return 0 <= distance <= 100  # 0m에서 100m 사이를 유효한 범위로 가정

def process_data(data):
    """수신된 데이터 처리"""
    try:
        json_data = json.loads(data.decode())
        device_address = json_data['device_address']
        role = json_data.get('role', devices.get(device_address, {}).get('role', 'UNKNOWN'))

        if device_address not in devices:
            devices[device_address] = {'role': role, 'position': [0, 0]}
        elif devices[device_address]['role'] != role:
            logger.info("Device %s changed role from %s to %s",
                        device_address, devices[device_address]['role'], role)
        devices[device_address]['role'] = role

        if 'range_data' in json_data:
            for range_info in json_data['range_data']:
                if validate_distance(range_info['range']):
                    devices[device_address]['position'] = [range_info['range'], range_info['range']]
                    break

        data_queue.append((time.time(), devices.copy()))
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON data")
    except KeyError as e:
        logger.error("Missing key in JSON data: %s", e)

def udp_listener():
    """UDP 리스너 함수"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    logger.info("UDP server listening on %s:%s", UDP_IP, UDP_PORT)

    while True:
        try:
            data, _ = sock.recvfrom(1024)
            process_data(data)
        except BlockingIOError:
            time.sleep(0.001)  # CPU 사용량을 줄이기 위한 짧은 대기
        except Exception as e:
            logger.error("Error in UDP listener: %s", e)

def main():
    """메인 함수"""
    # UDP 리스너 스레드 시작
    udp_thread = threading.Thread(target=udp_listener, daemon=True)
    udp_thread.start()

    # 애니메이션 설정 및 시작
    animation = FuncAnimation(fig, update_plot, interval=100, blit=True, cache_frame_data=False)
    plt.show()

if __name__ == "__main__":
    main()