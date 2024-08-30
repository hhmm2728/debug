#include <SPI.h>
#include "DW1000Ranging.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23
#define DW_CS 4

const uint8_t PIN_RST = 27;
const uint8_t PIN_IRQ = 34;
const uint8_t PIN_SS = 4;

// WiFi 설정
const char* ssid = "your_wifi_ssid";
const char* password = "your_wifi_password";
const char* udpAddress = "192.168.0.10";
const int udpPort = 3333;

WiFiUDP udp;

enum DeviceRole { DEVICE_ANCHOR, DEVICE_TAG };
DeviceRole currentRole = DEVICE_ANCHOR;

// unsigned long lastRoleSwitchTime = 0;
unsigned long lastAnchorRoleSwitchTime = 0;    
unsigned long lastTagRoleSwitchTime = 0;       
//const unsigned long ROLE_SWITCH_INTERVAL = 30000;     // 30초마다 역할 전환
const unsigned long ANCHOR_ROLE_SWITCH_INTERVAL = 5000;     // Anchor일 때 5초마다 역할 전환
const unsigned long TAG_ROLE_SWITCH_INTERVAL = 15000;     // TAG일 때 15초마다 역할 전환
const unsigned long MEASUREMENT_INTERVAL = 100;    // 100ms마다 측정
unsigned long lastMeasurementTime = 0;
unsigned long lastSyncTime = 0;
const unsigned long SYNC_INTERVAL = 5000;  // 5초마다 시간 동기화

#define DEVICE_ADDRESS "7D:00:22:EA:82:60:3B:9C"

struct DeviceInfo {
    uint16_t shortAddress;
    float range;
    float rxPower;
};

std::vector<DeviceInfo> deviceList;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("Setup started");
    setupWiFi();
    setupUWB();
    
    lastAnchorRoleSwitchTime = millis(); // 초기 앵커 역할 전환 시간 이슈 테스트
    lastTagRoleSwitchTime = millis();
    
    Serial.println("Setup completed");
}

void loop() {
    unsigned long currentTime = millis();
    // loop() 함수 실행시마다 WiFi 연결 상태 체크
    // WL_CONNECTED 상태가 아니면 setupWiFi() 호출해서 재설정
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi connection lost. Reconnecting...");
        setupWiFi();
    }

    /* // 역할 전환 체크
    if (currentTime - lastRoleSwitchTime >= ROLE_SWITCH_INTERVAL) {
        switchRole();
        lastRoleSwitchTime = currentTime;
    } */

    // anchor,tag 역할 전환 체크
    checkAndSwitchRole(currentTime);

    // 거리 측정 체크
    if (currentTime - lastMeasurementTime >= MEASUREMENT_INTERVAL) {
        measureDistances();
        lastMeasurementTime = currentTime;
    }

    // 시간 동기화 체크
    if (currentTime - lastSyncTime >= SYNC_INTERVAL) {
        syncTime();
        lastSyncTime = currentTime;
    }

    DW1000Ranging.loop();
}
//setup(), loop()에서 호출
void setupWiFi() {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected successfully");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nFailed to connect to WiFi. Please check your credentials.");
    }
}

void setupUWB() {
    Serial.println("Initializing UWB...");
    SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
    DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);
    DW1000Ranging.attachNewRange(newRange);
    DW1000Ranging.attachNewDevice(newDevice);
    DW1000Ranging.attachInactiveDevice(inactiveDevice);
    setRole(currentRole);
    Serial.println("UWB initialized");
}

void setRole(DeviceRole role) {
    Serial.println("Setting role to: " + String(role == DEVICE_ANCHOR ? "ANCHOR" : "TAG"));
    if (role == DEVICE_ANCHOR) {
        DW1000Ranging.startAsAnchor(DEVICE_ADDRESS, DW1000.MODE_LONGDATA_RANGE_LOWPOWER);
    } else {
        DW1000Ranging.startAsTag(DEVICE_ADDRESS, DW1000.MODE_LONGDATA_RANGE_LOWPOWER);
    }
   // 호출 후 실질적 Role 수행
    delay(100);
    Serial.println("Role set successfully");
}

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

void switchRole(unsigned long currentTime) {
   /*unsigned long currentTime = millis(); */ // 수정 필요한지 확인 -> 시간 측정 일관성을 위해 매개변수로 변경
    if (currentRole == DEVICE_ANCHOR) {
        currentRole = DEVICE_TAG;
        lastTagRoleSwitchTime = currentTime;
    } else {
        currentRole = DEVICE_ANCHOR;
        lastAnchorRoleSwitchTime = currentTime;
    }
    setRole(currentRole);
    broadcastRoleChange();
} // anchor, tag 시간 최신화 모두 수행

void broadcastRoleChange() {
    StaticJsonDocument<200> doc;
    doc["device_address"] = DEVICE_ADDRESS;
    doc["role"] = (currentRole == DEVICE_ANCHOR) ? "ANCHOR" : "TAG";
    doc["timestamp"] = millis();

    String jsonString;
    serializeJson(doc, jsonString);

    udp.beginPacket(udpAddress, udpPort);
    udp.print(jsonString);
    udp.endPacket();
}

void measureDistances() {
    // This function is called periodically to ensure all distances are measured
    // The actual ranging is handled by DW1000Ranging.loop() in the main loop
    // Here we can add any additional logic needed for comprehensive measurements
    Serial.println("Measuring distances...");
    // You might want to request ranging with specific devices here if needed
}

void syncTime() {
    // Simple time synchronization - in a real-world scenario, you'd use a more sophisticated method
    StaticJsonDocument<200> doc;
    doc["device_address"] = DEVICE_ADDRESS;
    doc["action"] = "sync_time";
    doc["timestamp"] = millis();

    String jsonString;
    serializeJson(doc, jsonString);

    udp.beginPacket(udpAddress, udpPort);
    udp.print(jsonString);
    udp.endPacket();
}

void newRange() {
    DeviceInfo info;
    info.shortAddress = DW1000Ranging.getDistantDevice()->getShortAddress();
    info.range = DW1000Ranging.getDistantDevice()->getRange();
    info.rxPower = DW1000Ranging.getDistantDevice()->getRXPower();

    auto it = std::find_if(deviceList.begin(), deviceList.end(),
                           [&](const DeviceInfo& d) { return d.shortAddress == info.shortAddress; });
    if (it != deviceList.end()) {
        *it = info;
    } else {
        deviceList.push_back(info);
    }

    Serial.print("Device: ");
    Serial.print(info.shortAddress, HEX);
    Serial.print(", Range: ");
    Serial.print(info.range);
    Serial.print(" m, RX power: ");
    Serial.print(info.rxPower);
    Serial.println(" dBm");

    sendRangeData();
}

void newDevice(DW1000Device *device) {
    Serial.print("New device added: ");
    Serial.println(device->getShortAddress(), HEX);
}

void inactiveDevice(DW1000Device *device) {
    Serial.print("Device inactive: ");
    Serial.println(device->getShortAddress(), HEX);
    deviceList.erase(
        std::remove_if(
            deviceList.begin(), deviceList.end(),
            [&](const DeviceInfo& d) { return d.shortAddress == device->getShortAddress(); }
        ),
        deviceList.end()
    );
}

void sendRangeData() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi not connected. Cannot send data.");
        return;
    }

    StaticJsonDocument<1024> jsonDoc;
    jsonDoc["device_address"] = DEVICE_ADDRESS;
    jsonDoc["role"] = (currentRole == DEVICE_ANCHOR) ? "ANCHOR" : "TAG";
    jsonDoc["timestamp"] = millis();

    JsonArray rangeData = jsonDoc.createNestedArray("range_data");
    for (const auto& device : deviceList) {
        JsonObject deviceData = rangeData.createNestedObject();
        deviceData["address"] = device.shortAddress;
        deviceData["range"] = device.range;
        deviceData["rx_power"] = device.rxPower;
    }

    String jsonString;
    serializeJson(jsonDoc, jsonString);

    udp.beginPacket(udpAddress, udpPort);
    size_t bytesSent = udp.print(jsonString);
    udp.endPacket();

    if (bytesSent > 0) {
        Serial.println("Range data sent via UDP successfully");
    } else {
        Serial.println("Failed to send range data via UDP");
    }

    Serial.println("JSON data: " + jsonString);
}

