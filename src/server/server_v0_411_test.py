"""
UDP 서버를 이용한 디바이스 위치 추적 및 시각화 프로그램

이 모듈은 UDP를 통해 디바이스로부터 위치 데이터를 수신하고,
실시간으로 디바이스의 위치를 업데이트하여 그래프로 표시합니다.
"""

import socket
import json
import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# UDP 서버 설정
UDP_IP = "192.168.0.10"  # 서버 IP 주소
UDP_PORT = 3333  # 포트 번호

# 데이터 저장을 위한 딕셔너리
devices = {}

# 그래프 초기화
fig, ax = plt.subplots()
scatter = ax.scatter([], [], animated=True)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_title("Device Positions")
ax.set_xlabel("X")
ax.set_ylabel("Y")

def update_plot(_):
    """플롯 업데이트 함수"""
    # 기존 주석 제거
    for text in ax.texts:
        text.remove()
    
    x = [dev['position'][0] for dev in devices.values()]
    y = [dev['position'][1] for dev in devices.values()]
    if x and y:  # x와 y가 비어있지 않은 경우에만 업데이트
        scatter.set_offsets(list(zip(x, y)))
        for i, (addr, dev) in enumerate(devices.items()):
            ax.annotate(f"{addr} ({dev['role']})", (x[i], y[i]))
    return scatter,

animation = FuncAnimation(fig, update_plot, interval=1000, blit=True, cache_frame_data=False)

def validate_distance(distance):
    """거리 데이터 유효성 검사"""
    return 0 <= distance <= 100  # 예: 0m에서 100m 사이를 유효한 범위로 가정

def process_data(data):
    """수신된 데이터 처리"""
    try:
        json_data = json.loads(data.decode())
        logger.info("Received data: %s", json_data)

        device_address = json_data['device_address']
        
        # 'role' 키가 없는 경우 기존 역할을 유지하거나 기본값 설정
        role = json_data.get('role', devices.get(device_address, {}).get('role', 'UNKNOWN'))

        if device_address not in devices:
            devices[device_address] = {'role': role, 'position': [0, 0]}
        else:
            if devices[device_address]['role'] != role:
                logger.info("Device %s changed role from %s to %s",
                            device_address, devices[device_address]['role'], role)
            devices[device_address]['role'] = role

        if 'range_data' in json_data:
            for range_info in json_data['range_data']:
                if validate_distance(range_info['range']):
                    # 여기서는 간단히 첫 번째 유효한 거리 데이터로 위치를 업데이트합니다.
                    # 실제 구현에서는 더 복잡한 위치 계산 알고리즘을 사용해야 합니다.
                    devices[device_address]['position'] = [range_info['range'], range_info['range']]
                    break

        logger.info("Updated device info: %s", devices[device_address])

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON data: %s", data)
    except KeyError as e:
        logger.error("Missing key in JSON data: %s", e)

def main():
    """메인 함수"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    logger.info("UDP server listening on %s:%s", UDP_IP, UDP_PORT)

    plt.show(block=False)
    plt.pause(0.1)  # 초기 그래프 표시를 위한 잠깐의 멈춤

    while True:
        try:
            data, _ = sock.recvfrom(1024)  # 버퍼 크기는 1024바이트
            logger.debug("Received raw data: %s", data)
            process_data(data)
            plt.pause(0.01)  # 그래프 업데이트를 위한 잠깐의 멈춤
        except Exception as e:
            logger.error("Error in main loop: %s", e)

if __name__ == "__main__":
    main()