import socket
import json
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from filterpy.kalman import KalmanFilter
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 상수 정의
UDP_IP = "192.168.0.10"
UDP_PORT = 3333
INITIAL_SETUP_DONE = False

# UDP 소켓 생성 및 바인딩
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

devices = {}
global_anchor_positions = {}

# 3D 플롯 초기화
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

def initialize_coordinate_system(dist):
    """초기 좌표계 설정"""
    anchor_addresses = list(dist.keys())
    if len(anchor_addresses) < 4:
        logger.error("최소 4개의 앵커가 필요합니다.")
        return None

    # 거리 데이터 유효성 검사
    for addr, distance in dist.items():
        if distance <= 0:
            logger.error(f"유효하지 않은 거리 데이터: {addr}: {distance}")
            return None

    positions = {
        anchor_addresses[0]: np.array([0, 0, 0]),
        anchor_addresses[1]: np.array([dist[anchor_addresses[1]], 0, 0]),
    }
    
    # 세 번째 노드의 위치 계산
    d2 = dist[anchor_addresses[2]]
    d1 = dist[anchor_addresses[1]]
    x = (d1**2 + d2**2 - dist[anchor_addresses[2]]**2) / (2 * d1)
    y = np.sqrt(max(0, d2**2 - x**2))  # 음수가 되지 않도록 보장
    positions[anchor_addresses[2]] = np.array([x, y, 0])
    
    # 네 번째 노드의 위치 계산
    d3 = dist[anchor_addresses[3]]
    matrix_a = np.array([
        [d1, 0, 0],
        [x, y, 0],
        [positions[anchor_addresses[2]][0], positions[anchor_addresses[2]][1], 0]
    ])
    b = np.array([
        (d1**2 + d3**2 - dist[anchor_addresses[1]]**2) / 2,
        (x**2 + y**2 + d3**2 - dist[anchor_addresses[2]]**2) / 2,
        (positions[anchor_addresses[2]][0]**2 + positions[anchor_addresses[2]][1]**2 +
         d3**2 - dist[anchor_addresses[3]]**2) / 2
    ])

    # 'Singular matrix' 오류 방지를 위한 예외 처리
    try:
        result = np.linalg.solve(matrix_a, b)
        positions[anchor_addresses[3]] = result
    except np.linalg.LinAlgError:
        logger.error("행렬 계산 중 오류 발생. 앵커 배치를 확인하세요.")
        return None

    # 앵커 배치 확인
    if not check_anchor_placement(positions):
        logger.warning("앵커 배치가 적절하지 않을 수 있습니다. 재배치를 고려하세요.")

    logger.info("좌표계 초기화 완료")
    logger.debug(f"계산된 위치: {positions}")

    return positions

def check_anchor_placement(positions):
    """앵커 배치의 적절성을 확인"""
    positions_array = np.array(list(positions.values()))
    centroid = np.mean(positions_array, axis=0)
    distances_from_centroid = np.linalg.norm(positions_array - centroid, axis=1)
    
    # 모든 앵커가 중심으로부터 비슷한 거리에 있는지 확인
    distance_variance = np.var(distances_from_centroid)
    if distance_variance > 1.0:  # 임계값은 상황에 따라 조정 가능
        logger.warning(f"앵커 배치의 분산이 큽니다: {distance_variance}")
        return False
    
    # 모든 앵커가 같은 평면 상에 있지 않은지 확인
    plane_fit = np.linalg.matrix_rank(positions_array - centroid)
    if plane_fit < 3:
        logger.warning("모든 앵커가 같은 평면 상에 있습니다.")
        return False
    
    return True

def multilateration(anchor_positions, measured_distances):
    """다변측량 함수"""
    def error(point, anchors, distances):
        return sum((np.linalg.norm(point - anchor) - distance)**2
                   for anchor, distance in zip(anchors, distances))

    initial_location = np.mean(list(anchor_positions.values()), axis=0)
    result = minimize(
        error,
        initial_location,
        args=(list(anchor_positions.values()), measured_distances),
        method='L-BFGS-B'
    )
    return result.x

def kalman_filter(z):
    """칼만 필터 함수"""
    kf = KalmanFilter(dim_x=3, dim_z=3)
    kf.x = np.array([0., 0., 0.])
    kf.F = np.eye(3)
    kf.H = np.eye(3)
    kf.P *= 1000.
    kf.R = 5
    
    kf.predict()
    kf.update(z)
    return kf.x

def update_plot():
    """3D 플롯 업데이트 함수"""
    ax.clear()
    for device in devices.values():
        color = 'r' if device['role'] == 'ANCHOR' else 'b'
        marker = 's' if device['role'] == 'ANCHOR' else 'o'
        ax.scatter(*device['position'], c=color, marker=marker)
        ax.text(*device['position'], device['address'])
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_xlim([-10, 10])
    ax.set_ylim([-10, 10])
    ax.set_zlim([0, 5])
    plt.draw()
    plt.pause(0.01)

def recalibrate_system():
    """시스템 재보정 함수"""
    recalibration_distances = {
        addr: np.linalg.norm(device['position'])
        for addr, device in devices.items() if device['role'] == 'ANCHOR'
    }
    new_anchor_positions = initialize_coordinate_system(recalibration_distances)
    if new_anchor_positions:
        for addr, position in new_anchor_positions.items():
            devices[addr]['position'] = position
        return new_anchor_positions
    else:
        logger.error("시스템 재보정 실패")
        return None

print("UDP 서버가 시작되었습니다. 데이터를 기다리는 중...")

while True:
    data, _ = sock.recvfrom(1024)
    print(f"Received data: {data.decode()}")  # 추가된 로그
    
    json_data = json.loads(data.decode())
    print(f"Parsed JSON data: {json_data}")  # 추가된 로그
    
    device_address = json_data['device_address']
    role = json_data['role']
    
    if device_address not in devices:
        devices[device_address] = {
            'role': role,
            'position': np.array([0, 0, 0]),
            'address': device_address
        }
    
    devices[device_address]['role'] = role
    print(f"Device info: {devices[device_address]}")  # 추가된 로그
    
    if not INITIAL_SETUP_DONE and len(devices) >= 4:
        anchor_devices = [dev for dev in devices.values() if dev['role'] == 'ANCHOR']
        if len(anchor_devices) >= 4:
            initial_distances = {
                addr: np.mean([d['range'] for d in json_data['range_data']])
                for addr, dev in devices.items() if dev['role'] == 'ANCHOR'
            }
            global_anchor_positions = initialize_coordinate_system(initial_distances)
            if global_anchor_positions:
                INITIAL_SETUP_DONE = True
                logger.info("초기 설정 완료")
            else:
                logger.error("초기 설정 실패")
    
    if role == 'ANCHOR':
        devices[device_address]['position'] = global_anchor_positions.get(
            device_address, np.array([0, 0, 0])
        )
    else:  # TAG
        tag_anchor_positions = {}
        tag_distances = []
        for range_data in json_data['range_data']:
            anchor_addr = range_data['address']
            if anchor_addr in devices and devices[anchor_addr]['role'] == 'ANCHOR':
                tag_anchor_positions[anchor_addr] = devices[anchor_addr]['position']
                tag_distances.append(range_data['range'])
        
        if len(tag_anchor_positions) >= 4:
            print(f"Multilateration input: positions={tag_anchor_positions}, distances={tag_distances}")  # 추가된 로그
            estimated_position = multilateration(tag_anchor_positions, tag_distances)
            print(f"Estimated position: {estimated_position}")  # 추가된 로그
            filtered_position = kalman_filter(estimated_position)
            devices[device_address]['position'] = filtered_position
            logger.info(f"장치 {device_address}의 추정 위치: {filtered_position}")
    
    print(f"Updating plot with devices: {devices}")  # 추가된 로그
    update_plot()
    
    if len(devices) % 100 == 0:
        new_positions = recalibrate_system()
        if new_positions:
            global_anchor_positions = new_positions
            logger.info("시스템 재보정 완료")
        else:
            logger.warning("시스템 재보정 실패")

