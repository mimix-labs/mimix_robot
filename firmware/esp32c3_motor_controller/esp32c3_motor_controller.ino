/*
  Mimix Robot - controlador de traccion por USB serial
  Placa: ESP32-C3 SuperMini
  Driver: TB6612FNG

  Protocolo de una linea a 115200 baudios:
    PING
    STOP
    MOVE FORWARD|BACKWARD|LEFT|RIGHT <duracion_ms> <velocidad>

  El robot inicia detenido. Toda orden invalida detiene los motores.
*/

#include <string.h>
#include <stdio.h>

// TB6612FNG: motor A izquierdo, motor B derecho.
const int PWMA = 3;
const int IN1 = 4;
const int IN2 = 5;
const int STBY = 1;
const int IN3 = 6;
const int IN4 = 7;
const int PWMB = 10;

// Reservados para sensores/servos futuros; no se usan en esta etapa.
const int SDA_I2C = 8;
const int SCL_I2C = 9;

const int MAX_SPEED = 180;              // Protege el driver y la primera prueba.
const unsigned long MAX_DURATION_MS = 3000;
const size_t COMMAND_BUFFER_SIZE = 64;

char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;
bool motionActive = false;
unsigned long motionDeadline = 0;

void stopMotors() {
  analogWrite(PWMA, 0);
  analogWrite(PWMB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  digitalWrite(STBY, LOW);
  motionActive = false;
}

void applyMotion(const char* direction, int speed) {
  digitalWrite(STBY, HIGH);

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
    return;
  }

  analogWrite(PWMA, speed);
  analogWrite(PWMB, speed);
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
  int speed = 0;
  if (sscanf(command, "MOVE %9s %ld %d", direction, &durationMs, &speed) != 3) {
    stopMotors();
    Serial.println("ERR INVALID_COMMAND");
    return;
  }

  const bool validDirection =
    strcmp(direction, "FORWARD") == 0 ||
    strcmp(direction, "BACKWARD") == 0 ||
    strcmp(direction, "LEFT") == 0 ||
    strcmp(direction, "RIGHT") == 0;

  if (!validDirection || durationMs <= 0 || durationMs > MAX_DURATION_MS || speed <= 0 || speed > MAX_SPEED) {
    stopMotors();
    Serial.println("ERR OUT_OF_RANGE");
    return;
  }

  applyMotion(direction, speed);
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

  pinMode(PWMA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(PWMB, OUTPUT);

  stopMotors();
  Serial.println("READY MIMIX_MOTOR_V1");
}

void loop() {
  readSerialCommands();

  if (motionActive && static_cast<long>(millis() - motionDeadline) >= 0) {
    stopMotors();
    Serial.println("EVENT MOTION_TIMEOUT STOP");
  }
}
