/*
  Mimix Robot - traccion por USB serial
  ESP32-C3 SuperMini + puente H de cuatro entradas

  Comandos desde la Jetson:
    PING
    STOP
    MOVE FORWARD|BACKWARD|LEFT|RIGHT <duracion_ms>

  El puente H se usa con sus habilitaciones activas (por ejemplo, jumpers
  ENA/ENB). Este firmware solo controla las cuatro entradas de direccion.
*/

#include <string.h>
#include <stdio.h>

// Entradas de dirección del puente H.
const int IN1 = 4;  // Motor A
const int IN2 = 5;
const int IN3 = 6;  // Motor B (derecho)
const int IN4 = 7;

// Reservados para sensores futuros; no se usan para motores.
const int SDA_I2C = 8;
const int SCL_I2C = 9;

const unsigned long MAX_DURATION_MS = 3000;
const size_t COMMAND_BUFFER_SIZE = 64;

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
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else if (strcmp(direction, "BACKWARD") == 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
  } else if (strcmp(direction, "LEFT") == 0) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else if (strcmp(direction, "RIGHT") == 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
  } else {
    stopMotors();
    return false;
  }

  return true;
}

void processCommand(char* command) {
  if (strcmp(command, "PING") == 0) {
    Serial.println("PONG");
    return;
  }

  if (strcmp(command, "STOP") == 0) {
    stopMotors();
    Serial.println("OK STOP");
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
  Serial.println("READY MIMIX_MOTOR_V2");
}

void loop() {
  readSerialCommands();

  if (motionActive && static_cast<long>(millis() - motionDeadline) >= 0) {
    stopMotors();
    Serial.println("EVENT MOTION_TIMEOUT STOP");
  }
}
