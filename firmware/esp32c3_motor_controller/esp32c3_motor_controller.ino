/*
 * Mimix Robot - ESP32-C3 motor controller
 *
 * Este sketch se abre directamente desde Arduino IDE.
 * Hardware objetivo: ESP32-C3 SuperMini + TB6612FNG + dos motores DC.
 *
 * Estado inicial seguro: no controla salidas de motor. Primero se debe
 * validar el cableado y configurar los pines en este archivo.
 */

#include <Arduino.h>
#include <string.h>

// Cambiar a true solo después de validar el cableado y la alimentación.
constexpr bool MOTOR_OUTPUTS_ENABLED = false;

// TODO: reemplazar por los GPIO reales. No usar pines de arranque sin validarlos.
constexpr int PIN_AIN1 = -1;
constexpr int PIN_AIN2 = -1;
constexpr int PIN_PWMA = -1;
constexpr int PIN_BIN1 = -1;
constexpr int PIN_BIN2 = -1;
constexpr int PIN_PWMB = -1;
constexpr int PIN_STBY = -1;

constexpr unsigned long HEARTBEAT_TIMEOUT_MS = 1500;
constexpr size_t COMMAND_BUFFER_SIZE = 64;

unsigned long lastHeartbeatMs = 0;
char commandBuffer[COMMAND_BUFFER_SIZE] = {};
size_t commandLength = 0;

bool motorPinsConfigured() {
  return PIN_AIN1 >= 0 && PIN_AIN2 >= 0 && PIN_PWMA >= 0 &&
         PIN_BIN1 >= 0 && PIN_BIN2 >= 0 && PIN_PWMB >= 0 && PIN_STBY >= 0;
}

void stopMotors() {
  if (!MOTOR_OUTPUTS_ENABLED || !motorPinsConfigured()) {
    return;
  }

  // TB6612FNG: STBY en LOW deshabilita ambos puentes H.
  digitalWrite(PIN_STBY, LOW);
  digitalWrite(PIN_AIN1, LOW);
  digitalWrite(PIN_AIN2, LOW);
  digitalWrite(PIN_BIN1, LOW);
  digitalWrite(PIN_BIN2, LOW);
  analogWrite(PIN_PWMA, 0);
  analogWrite(PIN_PWMB, 0);
}

void configureMotorPins() {
  if (!MOTOR_OUTPUTS_ENABLED || !motorPinsConfigured()) {
    Serial.println("STATUS SAFE_MODE motors_disabled");
    return;
  }

  pinMode(PIN_AIN1, OUTPUT);
  pinMode(PIN_AIN2, OUTPUT);
  pinMode(PIN_PWMA, OUTPUT);
  pinMode(PIN_BIN1, OUTPUT);
  pinMode(PIN_BIN2, OUTPUT);
  pinMode(PIN_PWMB, OUTPUT);
  pinMode(PIN_STBY, OUTPUT);
  stopMotors();
}

void handleCommand(const char *command) {
  if (strcmp(command, "PING") == 0) {
    Serial.println("PONG mimix-esp32c3");
  } else if (strcmp(command, "HEARTBEAT") == 0) {
    lastHeartbeatMs = millis();
    Serial.println("ACK HEARTBEAT");
  } else if (strcmp(command, "STOP") == 0) {
    stopMotors();
    Serial.println("ACK STOP");
  } else {
    // Los comandos de movimiento se agregarán solo tras validar seguridad.
    Serial.println("ERROR unsupported_command");
  }
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    const char current = static_cast<char>(Serial.read());

    if (current == '\n' || current == '\r') {
      if (commandLength > 0) {
        commandBuffer[commandLength] = '\0';
        handleCommand(commandBuffer);
        commandLength = 0;
      }
      continue;
    }

    if (commandLength < COMMAND_BUFFER_SIZE - 1) {
      commandBuffer[commandLength++] = current;
    } else {
      commandLength = 0;
      Serial.println("ERROR command_too_long");
    }
  }
}

void setup() {
  Serial.begin(115200);
  configureMotorPins();
  lastHeartbeatMs = millis();
  Serial.println("READY mimix-esp32c3 safe_mode");
}

void loop() {
  readSerialCommands();

  // Incluso cuando se habiliten motores, perder el heartbeat debe detenerlos.
  if (millis() - lastHeartbeatMs > HEARTBEAT_TIMEOUT_MS) {
    stopMotors();
  }
}
