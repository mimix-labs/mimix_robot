/*
  Mimix Robot - traccion y servos por USB serial
  ESP32-C3 SuperMini + puente H de cuatro entradas + PCA9685

  Comandos desde la Jetson:
    PING
    STOP
    MOVE FORWARD|BACKWARD|LEFT|RIGHT <duracion_ms>
    BASE
    SERVO <1..5> <pulso_calibrado>

  STOP solo detiene la traccion. Los servos se conservan en su ultima
  posicion hasta que se envie BASE o una nueva orden SERVO.
*/

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <stdio.h>
#include <string.h>

// Entradas de direccion del puente H.
const int IN1 = 3;  // Motor A (izquierdo)
const int IN2 = 5;
const int IN3 = 6;  // Motor B (derecho)
const int IN4 = 7;

// Bus I2C del PCA9685.
const int SDA_I2C = 8;
const int SCL_I2C = 9;
const uint8_t PCA9685_ADDRESS = 0x40;

const unsigned long MAX_DURATION_MS = 3000;
const size_t COMMAND_BUFFER_SIZE = 64;
const uint8_t SERVO_COUNT = 5;

// Canales PCA9685 0 a 4. Los limites y posiciones base son los calibrados
// fisicamente para este robot; no son grados.
const uint8_t SERVO_CHANNELS[SERVO_COUNT] = {0, 1, 2, 3, 4};
const uint16_t SERVO_MIN_PULSES[SERVO_COUNT] = {180, 400, 180, 150, 150};
const uint16_t SERVO_MAX_PULSES[SERVO_COUNT] = {320, 480, 600, 300, 400};
const uint16_t SERVO_BASE_PULSES[SERVO_COUNT] = {180, 480, 375, 150, 400};

Adafruit_PWMServoDriver pca(PCA9685_ADDRESS);

char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;
bool motionActive = false;
unsigned long motionDeadline = 0;

void stopMotors() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  motionActive = false;
}

bool applyMotion(const char* direction) {
  if (strcmp(direction, "FORWARD") == 0) {
    // Calibracion fisica: motor B esta invertido respecto al motor A.
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
  } else if (strcmp(direction, "BACKWARD") == 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else if (strcmp(direction, "LEFT") == 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
  } else if (strcmp(direction, "RIGHT") == 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else {
    stopMotors();
    return false;
  }
  return true;
}

bool setServoPulse(int servoNumber, int pulse) {
  const int servoIndex = servoNumber - 1;
  if (servoIndex < 0 || servoIndex >= SERVO_COUNT) {
    return false;
  }
  if (pulse < SERVO_MIN_PULSES[servoIndex] || pulse > SERVO_MAX_PULSES[servoIndex]) {
    return false;
  }
  pca.setPWM(SERVO_CHANNELS[servoIndex], 0, pulse);
  return true;
}

void applyBasePose() {
  for (uint8_t index = 0; index < SERVO_COUNT; index++) {
    pca.setPWM(SERVO_CHANNELS[index], 0, SERVO_BASE_PULSES[index]);
  }
}

void processCommand(char* command) {
  if (strcmp(command, "PING") == 0) {
    Serial.println("PONG MIMIX_ROBOT_V3");
    return;
  }
  if (strcmp(command, "STOP") == 0) {
    stopMotors();
    Serial.println("OK STOP");
    return;
  }
  if (strcmp(command, "BASE") == 0) {
    applyBasePose();
    Serial.println("OK BASE");
    return;
  }

  int servoNumber = 0;
  int pulse = 0;
  if (sscanf(command, "SERVO %d %d", &servoNumber, &pulse) == 2) {
    if (!setServoPulse(servoNumber, pulse)) {
      Serial.println("ERR SERVO_OUT_OF_RANGE");
      return;
    }
    Serial.print("OK SERVO ");
    Serial.print(servoNumber);
    Serial.print(' ');
    Serial.println(pulse);
    return;
  }

  char direction[10] = {0};
  long durationMs = 0;
  if (sscanf(command, "MOVE %9s %ld", direction, &durationMs) != 2) {
    stopMotors();
    Serial.println("ERR INVALID_COMMAND");
    return;
  }
  if (durationMs <= 0 || durationMs > MAX_DURATION_MS || !applyMotion(direction)) {
    stopMotors();
    Serial.println("ERR OUT_OF_RANGE");
    return;
  }
  motionActive = true;
  motionDeadline = millis() + static_cast<unsigned long>(durationMs);
  Serial.print("OK MOVE ");
  Serial.println(direction);
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    const char character = static_cast<char>(Serial.read());
    if (character == '\r') {
      continue;
    }
    if (character == '\n') {
      commandBuffer[commandLength] = '\0';
      if (commandLength > 0) {
        processCommand(commandBuffer);
      }
      commandLength = 0;
      continue;
    }
    if (commandLength >= COMMAND_BUFFER_SIZE - 1) {
      commandLength = 0;
      stopMotors();
      Serial.println("ERR LINE_TOO_LONG");
      continue;
    }
    commandBuffer[commandLength++] = character;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopMotors();

  Wire.begin(SDA_I2C, SCL_I2C);
  pca.begin();
  pca.setPWMFreq(50);
  delay(10);
  applyBasePose();
  Serial.println("READY MIMIX_ROBOT_V3");
}

void loop() {
  readSerialCommands();
  if (motionActive && static_cast<long>(millis() - motionDeadline) >= 0) {
    stopMotors();
    Serial.println("EVENT MOTION_TIMEOUT STOP");
  }
}
