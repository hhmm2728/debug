import serial
import time
import datetime

def wait_for_arduino():
    while True:
        try:
            # 시리얼 포트 설정 (필요에 따라 'COM3' 또는 '/dev/ttyUSB0' 등으로 변경)
            ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)  # timeout을 0.1초로 설정
            print("Arduino가 연결되었습니다. 데이터를 기다리는 중...")
            return ser
        except serial.SerialException:
            print("Arduino를 찾을 수 없습니다. 다시 시도합니다...")
            time.sleep(0.1)  # 0.1초 대기 후 재시도

def main():
    ser = wait_for_arduino()
    log_file = open('arduino_log.txt', 'w')
    print("로깅 준비 완료. 데이터를 기다리는 중...")

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                log_entry = f"{timestamp} - {line}\n"
                print(log_entry, end='')
                log_file.write(log_entry)
                log_file.flush()  # 버퍼를 즉시 파일에 쓰기
            time.sleep(0.001)  # 1밀리초 대기
    except KeyboardInterrupt:
        print("로깅을 종료합니다.")
    finally:
        ser.close()
        log_file.close()

if __name__ == "__main__":
    main()
