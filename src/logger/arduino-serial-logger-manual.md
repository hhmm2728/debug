# Arduino 시리얼 데이터 로거 사용 메뉴얼 (수정된 스크립트)

## 1. 개요
이 메뉴얼은 Arduino에서 시리얼 데이터를 받아 로깅하는 Python 스크립트의 사용 방법을 설명합니다.

## 2. 필요 사항
- Python 3.6 이상
- pyserial 라이브러리
- Arduino 보드
- USB 케이블

## 3. 설치 방법
터미널에서 다음 명령어를 실행하여 필요한 라이브러리를 설치합니다:
```
pip install pyserial
```

## 4. Python 스크립트
다음은 전체 Python 스크립트입니다. 이 스크립트를 'arduino_serial_logger.py'로 저장하세요.

```python
import serial
import time
import datetime

def wait_for_arduino():
    while True:
        try:
            # 시리얼 포트 설정 (필요에 따라 'COM3' 또는 '/dev/ttyUSB0' 등으로 변경)
            ser = serial.Serial('COM3', 115200, timeout=0.1)  # timeout을 0.1초로 설정
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
```

## 5. 스크립트 설명
- 스크립트는 지정된 시리얼 포트에서 데이터를 읽어 타임스탬프와 함께 로그 파일에 기록합니다.
- 데이터는 화면에 출력되며 동시에 'arduino_log.txt' 파일에 저장됩니다.
- 로깅은 Ctrl+C를 눌러 수동으로 종료할 때까지 계속됩니다.

## 6. 사용 방법
1. Arduino 보드에 원하는 코드를 업로드합니다. (Serial.begin(115200) 사용)
2. Arduino를 USB로 컴퓨터에 연결합니다.
3. 스크립트에서 시리얼 포트 설정을 확인하고 필요시 수정합니다:
   - Windows: 'COM3' (또는 해당하는 COM 포트)
   - Mac/Linux: '/dev/ttyUSB0' (또는 해당하는 장치 파일)
4. 터미널에서 스크립트가 있는 디렉토리로 이동합니다.
5. 다음 명령어로 스크립트를 실행합니다:
   ```
   python arduino_serial_logger.py
   ```
6. 스크립트가 실행되면 Arduino에서 보내는 데이터가 화면에 출력되고 로그 파일에 저장됩니다.

## 7. 로깅 종료
- Ctrl+C를 눌러 스크립트를 종료합니다.
- "로깅을 종료합니다." 메시지가 표시되고 로그 파일이 자동으로 저장됩니다.

## 8. 주의사항
- 스크립트의 baud rate(115200)가 Arduino 코드의 설정과 일치하는지 확인하세요.
- 시리얼 포트 설정('COM3' 또는 '/dev/ttyUSB0')이 사용 중인 시스템과 Arduino 연결에 맞게 설정되었는지 확인하세요.
- 로그 파일('arduino_log.txt')은 스크립트가 있는 디렉토리에 생성됩니다.

## 9. 문제 해결
- 연결 오류 발생 시 시리얼 포트 설정을 확인하세요.
- Arduino가 올바르게 연결되어 있는지 확인하세요.
- 다른 프로그램(예: Arduino IDE의 Serial Monitor)이 해당 포트를 사용 중이지 않은지 확인하세요.

이 메뉴얼을 참고하여 Arduino 시리얼 데이터 로거를 사용하시기 바랍니다. 추가 질문이나 문제가 있으면 언제든 문의해주세요.
