/*
  Mimix Robot - prueba de motores
  Placa: ESP32-C3 SuperMini
  Driver: TB6612FNG

  Al encender, el robot hace UNA sola secuencia:
  adelante -> quieto -> atras -> quieto -> izquierda -> quieto -> derecha -> quieto

  Probar primero con las ruedas elevadas.
*/

// Pines del TB6612FNG
const int PWMA = 3;   // Velocidad motor A (motor izquierdo)
const int AIN1 = 4;   // Direccion motor A
const int AIN2 = 5;   // Direccion motor A
const int STBY = 1;   // Habilita o deshabilita el driver
const int BIN1 = 6;   // Direccion motor B (motor derecho)
const int BIN2 = 7;   // Direccion motor B (motor derecho)
const int PWMB = 10;  // Velocidad motor B

// Pines reservados para conexiones futuras. NO se usan para motores.
const int SDA_I2C = 8;
const int SCL_I2C = 9;
const int RX_JETSON = 20;
const int TX_JETSON = 21;

const int VELOCIDAD = 180;          // 0 a 255
const int TIEMPO_MOVIMIENTO = 1000; // milisegundos
const int TIEMPO_QUIETO = 1000;     // milisegundos

bool pruebaRealizada = false;

void setup() {
  Serial.begin(115200);

  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(PWMB, OUTPUT);

  quieto();

  Serial.println("Mimix Robot - ESP32-C3 listo");
  Serial.println("I2C reservado: SDA GPIO8, SCL GPIO9");
  Serial.println("UART Jetson reservado: RX GPIO20, TX GPIO21");
  Serial.println("La prueba inicia en 3 segundos");
  delay(3000);
}

void loop() {
  if (!pruebaRealizada) {
    probarMovimientos();
    pruebaRealizada = true;
  }

  // Cuando termina la prueba, el robot queda detenido.
  quieto();
}

void adelante() {
  Serial.println("Adelante");
  digitalWrite(STBY, HIGH);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);

  analogWrite(PWMA, VELOCIDAD);
  analogWrite(PWMB, VELOCIDAD);
}

void atras() {
  Serial.println("Atras");
  digitalWrite(STBY, HIGH);

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);

  analogWrite(PWMA, VELOCIDAD);
  analogWrite(PWMB, VELOCIDAD);
}

void izquierda() {
  Serial.println("Izquierda");
  digitalWrite(STBY, HIGH);

  // El motor izquierdo va atras y el derecho adelante.
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);
  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);

  analogWrite(PWMA, VELOCIDAD);
  analogWrite(PWMB, VELOCIDAD);
}

void derecha() {
  Serial.println("Derecha");
  digitalWrite(STBY, HIGH);

  // El motor izquierdo va adelante y el derecho atras.
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);

  analogWrite(PWMA, VELOCIDAD);
  analogWrite(PWMB, VELOCIDAD);
}

void quieto() {
  analogWrite(PWMA, 0);
  analogWrite(PWMB, 0);

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, LOW);
  digitalWrite(STBY, LOW);
}

void probarMovimientos() {
  adelante();
  delay(TIEMPO_MOVIMIENTO);
  quieto();
  delay(TIEMPO_QUIETO);

  atras();
  delay(TIEMPO_MOVIMIENTO);
  quieto();
  delay(TIEMPO_QUIETO);

  izquierda();
  delay(TIEMPO_MOVIMIENTO);
  quieto();
  delay(TIEMPO_QUIETO);

  derecha();
  delay(TIEMPO_MOVIMIENTO);
  quieto();

  Serial.println("Prueba terminada. Robot quieto.");
}
