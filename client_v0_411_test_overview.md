0. 개요
  
   - 디바이스 A,B,C 는 실행 시간 동안 최대한으로 앵커 1 - 태그 2 의 역할을 유지하여야 한다. (타이밍도 참조)
  
   - 디바이스 B,C 는 실행 시간 동안 앵커 1 - 태그 2의 역할을 최대한으로 유지하기 위해 초기 역할을 시작하기 전 각각 6초, 12초의 딜레이를 갖는다.
  
   - 소스코드는 디바이스 A,B,C 에 맞춰서 각각 다르며 client_v0_411.cpp 소스코드를 기반으로 한다.
  
   - 서버 측의 출력 로그를 통해 각 디바이스에서 측정된 거리 데이터와 클라이언트-서버의 송수신 계통을 검증한다.


1. 전체 수정 사항

	a. 역할 수정 시간

	* 기본 역할 전환 시 딜레이 100ms

	태그 : 15초
	앵커 : 5초

	-> client_v0_411.cpp(이하 client) line 28
	const unsigned long ROLE_SWITCH_INTERVAL = 30000;  // 30초마다 역할 전환

	* ANCHOR_ROLE_SWITCH_INTERVAL / TAG_ROLE_SWITCH_INTERVAL 와 같이 두 가지 상수 선언해서 각각 5초 15초로 설정
	> const unsigned long ANCHOR_ROLE_SWITCH_INTERVAL = 5000;
	> const unsigned long TAG_ROLE_SWITCH_INTERVAL = 15000;

	-> client line 65
	if (currentTime - lastRoleSwitchTime >= ROLE_SWITCH_INTERVAL) {
        switchRole();
        lastRoleSwitchTime = currentTime;
    
	* lastAnchorRoleSwitchTime / lastTagRoleSwitchTime 과 같이 두 가지 전역 변수 선언해서 역할에 따른 지속 시간 최신화
	> unsigned long lastAnchorRoleSwitchTime = 0;
	> unsigned long lastTagRoleSwitchTime = 0;
     	
	* 
    if() 조건문 추가해서 현재 role이 앵커이고 시간이 5초 지속된 상황이 다음과 같으면
  	T : 위 구문을 참조해 switchRole() 함수를 호출 하여 태그로 역할 전환
	F : 위 구문을 참조해 lastRoleSwtichTime의 시간 최신화

  	if() 조건문 추가해서 현재 role이 태그이고 시간이 15초 지속된 상황이 다음과 같으면
  	T : 위 구문을 참조해 switchRole() 함수를 호출 하여 앵커로 역할 전환
	F : 위 구문을 참조해 lastRoleSwtichTime의 시간 최신화

	* if() 조건문 중첩 사용에서 switch - case 조건문으로 개선
	-> 현재 역할이 anchor/tag 일 때 tag/anchor 조건을 추가적으로 검사하는 것은 불필요한 연산

	void checkAndSwitchRole(unsigned long currentTime) {
    switch(currentRole) {
        case DEVICE_ANCHOR:
            if (currentTime - lastAnchorRoleSwitchTime >= ANCHOR_ROLE_SWITCH_INTERVAL) {
                switchRole(currentTime); // switchRole 함수 수정으로 currentTime 인자로 전달
                /* lastAnchorRoleSwitchTime = currentTime; */ // 이 부분 필요한지 확인(중복됨)
            }
            break;
        
        case DEVICE_TAG:
            if (currentTime - lastTagRoleSwitchTime >= TAG_ROLE_SWITCH_INTERVAL) {
                switchRole(currentTime); // switchRole 함수 수정으로 currentTime 인자로 전달
               /* lastTagRoleSwitchTime = currentTime; */ // 이 부분 필요한지 확인(중복됨)
            }
            break;
        
        default:
            // 예외 처리 또는 로깅
            Serial.println("Unknown device role");
            break;
    }
}


	* 시간 초기화 문제 디버깅 필요
   	> switchRole()과 checkAndSwithRole() 함수 보완 

	* switchRole() 수정
	> 역할 전환 관련 시간변수가 1개에서 2개로 변하면서 switchRole() 함수 호출 시 시간 초기화 과정 추가로 수행해야 함
	> void switchRole(unsigned long currentTime) {
    if (currentRole == DEVICE_ANCHOR) {
        currentRole = DEVICE_TAG;
        lastTagRoleSwitchTime = currentTime;
    } else {
        currentRole = DEVICE_ANCHOR;
        lastAnchorRoleSwitchTime = currentTime;
    }
    setRole(currentRole);
    broadcastRoleChange();
	}
	
	-> 예를 들어 anchor의 swtich interval 초과 했을 시에 다음 loop에 tag로 역할 전환 되어 시작하면 lastTagRoleSwitchTime은 현재 시간으로 최신화 되어 있지 않기 때문에 바로 역할 전환이 이루어 질 수 있음

	* checkAndSwitchRole() 함수의 아래 부분들이 switchRole() 함수에서 중복되므로 일단은 주석처리함 없어도 될듯
  	lastAnchorRoleSwitchTime = currentTime;
  	lastAnchorRoleSwitchTime = currentTime; 

	* 실제 실행 후 디버깅 예정 

1. 디바이스 별 수정 사항

	디바이스 A (앵커 시작) : 
	디바이스 B (앵커 시작, 초기 딜레이 6초) : b 항목 수정
	디바이스 C (앵커 시작 초기 딜레이 12초) : b 항목 수정

	a. 초기 역할 수정

	* 필요시 수정
  
	-> client line 24

	enum DeviceRole { DEVICE_ANCHOR, DEVICE_TAG };
	DeviceRole currentRole = DEVICE_ANCHOR;

	b. 초기 딜레이 수정

	* 기본 초기 딜레이 1000ms

	-> client line 44

	void setup() {
    		Serial.begin(115200);
    		delay(1000);

	* 디바이스 A : 유지
	* 디바이스 B : 7000ms
	* 디바이스 C : 13000ms