/* Casa segura - Grupo 5 - Programa unificado
   Monitor serial a 115200 baudios.
   SISMO:  ADXL335 (A0, A1, A2) + LED (53) + pulsador pull-down (11) + buzzer (3)
   GAS:    MQ-135 (A3) + ventilador MOSFET (5) + buzzer (3)
   LLUVIA: caudalimetro (18) + Funduino (A5) + servo tapa (12)
   Comandos por serial: b = nueva base MQ-135 | r = reiniciar G_max | z = nuevo reposo sismo
*/

#include <Arduino.h>
#include <Servo.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>

// ===================== PANTALLA OLED I2C (1.3" SH1106 / 128x64) =====================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SH1106G display = Adafruit_SH1106G(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
bool oledDisponible = false;
unsigned long tOled = 0;

// ===================== PINES =====================
const int PIN_X = A0, PIN_Y = A1, PIN_Z = A2;
const int PIN_MQ = A3, PIN_FUNDUINO = A5;
const int PIN_BUZZER = 3;
const int PIN_VENTILADOR = 5;   // Pin 5 (no 9): tone() usa Timer 2 y anula PWM en pines 9 y 10
const int PIN_BOTON = 11;       // Pull-down externo de 10 kOhm
const int PIN_SERVO = 12;
const int PIN_FLUJO = 18;       // Pin de interrupcion externa en Mega
const int PIN_LED = 53;

// ===================== CONSTANTES DE CALIBRACION =====================
// Sismo (calibracion del ADXL335)
const float VREF = 5.03;
const float V0X = 1.631, V0Y = 1.625, V0Z = 1.644; // Voltajes a 0 g [V]
const float SX  = 0.328, SY  = 0.334, SZ  = 0.323; // Sensibilidades [V/g]
const float UMBRAL_SISMO = 0.40;                   // Umbral de aceleracion [g]
const int   CONFIRMAR = 200;                       // 200 muestras * 10 ms = 2 s seguidos
const float AJUSTE_REPOSO = 0.0003;                // Seguimiento lento en vigilancia normal
const float AJUSTE_GRACIA = 0.05;                  // Reajuste rapido durante tiempo de gracia
const unsigned long GRACIA_BOTON = 5000;           // Pausa tras silenciar alarma [ms]
const unsigned long GRACIA_ACTUADOR = 2000;        // Pausa tras mover ventilador/servo [ms]

// Gas (MQ-135 con histeresis en G = R0/Rs)
const unsigned long CALENTAMIENTO = 30000;         // 30 s iniciales de estabilizacion
const float G_ALERTA_ON = 1.8, G_ALERTA_OFF = 1.4;
const float G_EMERG_ON  = 3.5, G_EMERG_OFF  = 3.0;

// Lluvia (caudalimetro calibrado con jeringa + Funduino que sube al mojarse)
const float K_FLUJO = 83.6;                        // Constante experimental [Hz / (L/min)]
const float VOLUMEN_CIERRE = 0.100;                // 100 mL = 0.100 L
const int   SEGUNDOS_SIN_LLUVIA = 10;              // Espera en 0 pulsos tras superar 100 mL
const int   ANGULO_CERRADO = 90;
const int   UMBRAL_MOJADO = 300, UMBRAL_SECO = 100;

// ===================== VARIABLES GLOBALES =====================
// Sismo
float reposoX = 0, reposoY = 0, reposoZ = 0;
float ventana[50];                                 // Ventana movil de 0.5 s (50 * 10 ms)
int posVentana = 0, contadorSismo = 0;
float nivelSismo = 0;
bool alarmaSismo = false, enGracia = false;
int botonAnterior = LOW;
unsigned long tSismo = 0, tBoton = 0, inicioGracia = 0, duracionGracia = 0;

// Gas
float lecturaGas = 0, baseGas = 0, G = 0, G_max = 0, sumaBaseGas = 0;
int cuentaBaseGas = 0, estadoGas = 0, velVentilador = 0; // estado: 0=ok, 1=alerta, 2=emerg
bool gasListo = false;
unsigned long tGas = 0, inicioGas = 0;

// Lluvia
Servo tapa;
volatile unsigned int pulsos = 0;                  // Incrementada por interrupcion
float caudal = 0, volumen = 0;
int segundosSinFlujo = 0, lecturaFunduino = 0, anguloTapa = 0;
bool mojado = false, estuvoMojado = false;
unsigned long tLluvia = 0;

// Buzzer y monitor serial
int modoBuzzer = 0;                                // 0=apagado, 1=sismo, 2=gas
unsigned long tBuzzer = 0, tImprimir = 0;

// ===================== FUNCIONES AUXILIARES =====================
void contarPulso() { pulsos++; }

// Lee un eje del acelerometro en g; doble lectura con retardo para estabilizar el ADC al cambiar de canal
float leerG(int pin, float v0, float s) {
  analogRead(pin);
  delayMicroseconds(50);
  float v = analogRead(pin) * VREF / 1023.0;
  return (v - v0) / s;
}

// Limpia el promedio movil y el contador de confirmacion del sismo
void limpiarVentanaSismo() {
  for (int i = 0; i < 50; i++) ventana[i] = 0;
  posVentana = 0;
  nivelSismo = 0;
  contadorSismo = 0;
}

// Promedia 1 s con la maqueta quieta para fijar el vector de gravedad en reposo
void tomarReposo() {
  float sx = 0, sy = 0, sz = 0;
  for (int i = 0; i < 100; i++) {
    sx += leerG(PIN_X, V0X, SX);
    sy += leerG(PIN_Y, V0Y, SY);
    sz += leerG(PIN_Z, V0Z, SZ);
    delay(10);
  }
  reposoX = sx / 100.0;
  reposoY = sy / 100.0;
  reposoZ = sz / 100.0;
  limpiarVentanaSismo();
  tSismo = millis();
}

// Activa una pausa en la deteccion de sismos (conserva la mas larga si ya habia una activa)
void darGracia(unsigned long ahora, unsigned long ms) {
  if (enGracia && (ahora - inicioGracia) < duracionGracia) {
    unsigned long falta = duracionGracia - (ahora - inicioGracia);
    if (falta > ms) ms = falta;
  }
  enGracia = true;
  inicioGracia = ahora;
  duracionGracia = ms;
  limpiarVentanaSismo();
}

// Actualiza la pantalla OLED I2C en tiempo real
void actualizarOled() {
  if (!oledDisponible) return;

  display.clearDisplay();

  // Encabezado superior limpio (sin fillRect masivo para no provocar caidas de voltaje en la alimentacion)
  bool hayAlarma = alarmaSismo || (estadoGas == 2);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(hayAlarma ? 4 : 16, 1);
  if (alarmaSismo) {
    display.print(F("! ALERTA TERREMOTO !"));
  } else if (estadoGas == 2) {
    display.print(F("! EMERGENCIA: GAS !"));
  } else if (estadoGas == 1) {
    display.print(F("AVISO: FUGA DE GAS"));
  } else if (mojado) {
    display.print(F("ESTADO: LLOVIENDO"));
  } else {
    display.print(F("CASA SEGURA - OK"));
  }
  display.drawFastHLine(0, 10, 128, SH110X_WHITE);

  // Linea 1: SISMO
  display.setCursor(0, 14);
  display.print(F("SIS: "));
  if (alarmaSismo)      display.print(F("!ALARMA! "));
  else if (enGracia)    display.print(F("PAUSA   "));
  else                  display.print(F("OK      "));
  display.print(nivelSismo, 3);
  display.print(F("g"));

  // Linea 2: GAS
  display.setCursor(0, 26);
  display.print(F("GAS: "));
  if (!gasListo) {
    display.print(F("CALENTANDO..."));
  } else {
    if (estadoGas == 2)      display.print(F("!EMERG! "));
    else if (estadoGas == 1) display.print(F("AVISO   "));
    else                     display.print(F("OK      "));
    display.print(F("G="));
    display.print(G, 2);
  }

  // Linea 3: LLUVIA
  display.setCursor(0, 38);
  display.print(F("AGUA: "));
  display.print((int)(volumen * 1000.0));
  display.print(F("mL "));
  display.print(mojado ? F("(MOJADO)") : F("(SECO)"));

  // Linea 4: ACTUADORES
  display.setCursor(0, 50);
  display.print(F("TAPA:"));
  display.print(anguloTapa >= 80 ? F("CERR(90)") : F("ABIE(0*)"));
  display.print(F(" V:"));
  display.print(velVentilador > 0 ? F("100%") : F("OFF"));

  // Barra de estado inferior decorativa
  display.drawFastHLine(0, 62, 128, SH110X_WHITE);

  display.display();
}

// ===================== SETUP =====================
void setup() {
  Serial.begin(115200);

  // Inicializacion de Pantalla OLED I2C (Direccion 0x3C o 0x3D)
  Wire.begin();
  Wire.setClock(400000); // 400 kHz Fast I2C (transmision rapida de ~25 ms)
  if (display.begin(0x3C, true)) {
    oledDisponible = true;
  } else if (display.begin(0x3D, true)) {
    oledDisponible = true;
  }

  pinMode(PIN_LED, OUTPUT);        digitalWrite(PIN_LED, LOW);
  pinMode(PIN_BUZZER, OUTPUT);     digitalWrite(PIN_BUZZER, LOW);
  pinMode(PIN_VENTILADOR, OUTPUT); analogWrite(PIN_VENTILADOR, 0);
  pinMode(PIN_BOTON, INPUT);

  tapa.attach(PIN_SERVO);
  tapa.write(0);

  pinMode(PIN_FLUJO, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLUJO), contarPulso, RISING);

  // Pintar la pantalla OLED con su carga real antes de calibrar reposo
  if (oledDisponible) {
    actualizarOled();
  }
  delay(400); // Esperar que la alimentacion se estabilice con la pantalla encendida

  Serial.println("Casa segura: calibrando reposo (1 s), no mueva la maqueta...");
  tomarReposo();

  noInterrupts();
  pulsos = 0;
  interrupts();

  unsigned long ahora = millis();
  tSismo = tGas = inicioGas = tLluvia = tImprimir = tOled = ahora;
  enGracia = false;
  inicioGracia = 0;
  duracionGracia = 0;
  Serial.println("Listo. Calentando MQ-135 (30 s)...");
}

// ===================== LOOP PRINCIPAL =====================
void loop() {
  unsigned long ahora = millis();

  // --- 0. COMANDOS POR MONITOR SERIAL ---
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == 'b' || cmd == 'B') {
      baseGas = lecturaGas;
      gasListo = true;
      G_max = 0;
      Serial.print(">> Nueva base MQ-135: "); Serial.println(baseGas, 1);
    } else if (cmd == 'r' || cmd == 'R') {
      G_max = 0;
      Serial.println(">> G_max reiniciado.");
    } else if (cmd == 'z' || cmd == 'Z') {
      Serial.println(">> Recalibrando reposo del acelerometro (1 s)...");
      tomarReposo();
      Serial.println(">> Reposo listo.");
    }
  }

  // --- 1. SISMO (muestreo cada 10 ms) ---
  if (enGracia && ahora - inicioGracia >= duracionGracia) {
    enGracia = false;
    limpiarVentanaSismo(); // Arranca vigilancia limpia desde N = 0.000
  }

  if (ahora - tSismo >= 10) {
    tSismo = ahora;
    float dx = leerG(PIN_X, V0X, SX) - reposoX;
    float dy = leerG(PIN_Y, V0Y, SY) - reposoY;
    float dz = leerG(PIN_Z, V0Z, SZ) - reposoZ;
    float v = sqrt(dx * dx + dy * dy + dz * dz);

    // En gracia reajusta el reposo rapido; vigilando lo hace muy lento
    if (!alarmaSismo) {
      float paso = enGracia ? AJUSTE_GRACIA : AJUSTE_REPOSO;
      reposoX += paso * dx;
      reposoY += paso * dy;
      reposoZ += paso * dz;
    }

    // Promedio movil de los ultimos 0.5 s (suma directa para evitar deriva)
    ventana[posVentana] = v;
    posVentana = (posVentana + 1) % 50;
    float suma = 0;
    for (int i = 0; i < 50; i++) suma += ventana[i];
    nivelSismo = suma / 50.0;

    if (!enGracia) {
      if (nivelSismo > UMBRAL_SISMO) {
        if (contadorSismo < CONFIRMAR) contadorSismo++;
      } else if (contadorSismo > 0) {
        contadorSismo--;
      }

      if (contadorSismo == CONFIRMAR && !alarmaSismo) {
        alarmaSismo = true;
        digitalWrite(PIN_LED, HIGH);
        // Apagar ventilador inmediatamente si ocurre un sismo
        if (velVentilador != 0) {
          velVentilador = 0;
          analogWrite(PIN_VENTILADOR, 0);
        }
        Serial.println(">> SISMO: alarma activa. Presione el boton en sitio seguro.");
      }
    }
  }

  // Boton de sitio seguro (flanco de subida con antirrebote de 50 ms)
  int boton = digitalRead(PIN_BOTON);
  if (boton == HIGH && botonAnterior == LOW && ahora - tBoton > 50) {
    tBoton = ahora;
    if (alarmaSismo) {
      alarmaSismo = false;
      digitalWrite(PIN_LED, LOW);
      darGracia(ahora, GRACIA_BOTON);
      Serial.println(">> SISMO: persona a salvo. Alarma apagada (gracia 5 s).");
    }
  }
  botonAnterior = boton;

  // --- 2. GAS MQ-135 (muestreo cada 500 ms) ---
  if (ahora - tGas >= 500) {
    tGas = ahora;

    // Descarta primera lectura tras cambiar de canal y promedia 10 muestras
    analogRead(PIN_MQ);
    delayMicroseconds(50);
    long suma = 0;
    for (int i = 0; i < 10; i++) suma += analogRead(PIN_MQ);
    lecturaGas = suma / 10.0;

    if (!gasListo) {
      unsigned long pasado = ahora - inicioGas;
      if (pasado < CALENTAMIENTO) {
        if (pasado >= CALENTAMIENTO - 10000) { // Promedia ultimos 10 s como aire limpio
          sumaBaseGas += lecturaGas;
          cuentaBaseGas++;
        }
      } else {
        baseGas = (cuentaBaseGas > 0) ? (sumaBaseGas / cuentaBaseGas) : lecturaGas;
        gasListo = true;
        Serial.print(">> GAS listo. Base N_aire = "); Serial.println(baseGas, 1);
      }
    } else {
      // Relacion G = R0 / Rs (si el ADC satura en 1023, mantiene G alto por seguridad)
      if (lecturaGas >= 1022.5) G = 50.0;
      else if (baseGas > 0)     G = ((1023.0 - baseGas) / baseGas) * (lecturaGas / (1023.0 - lecturaGas));
      else                      G = 0;
      if (G > G_max) G_max = G;

      // Maquina de estados con histeresis
      int anterior = estadoGas;
      if (estadoGas == 0) {
        if (G >= G_EMERG_ON) estadoGas = 2;
        else if (G >= G_ALERTA_ON) estadoGas = 1;
      } else if (estadoGas == 1) {
        if (G >= G_EMERG_ON) estadoGas = 2;
        else if (G < G_ALERTA_OFF) estadoGas = 0;
      } else {
        if (G < G_ALERTA_OFF) estadoGas = 0;
        else if (G < G_EMERG_OFF) estadoGas = 1;
      }

      if (estadoGas != anterior) {
        if (estadoGas == 0) Serial.println(">> GAS: normal");
        if (estadoGas == 1) Serial.println(">> GAS: ALERTA (ventilador al 50%)");
        if (estadoGas == 2) Serial.println(">> GAS: EMERGENCIA (ventilador 100% + buzzer)");
      }

      // El ventilador SOLO se activa si hay gas y NO hay sismo ni lluvia (100% potencia para arrancar el motor)
      int vel = 0;
      if (!alarmaSismo && !mojado && (anguloTapa == 0)) {
        vel = (estadoGas >= 1) ? 255 : 0;
      }
      if (vel != velVentilador) {
        velVentilador = vel;
        analogWrite(PIN_VENTILADOR, velVentilador);
        darGracia(ahora, GRACIA_ACTUADOR); // Evita falso sismo por arranque del ventilador
      }
    }
  }

  // --- 3. LLUVIA: CAUDALIMETRO + FUNDUINO + SERVO (ventana de 1 s) ---
  if (ahora - tLluvia >= 1000) {
    tLluvia = ahora;

    // Copia segura de los pulsos del ultimo segundo sin perder interrupciones
    noInterrupts();
    unsigned int pulsosSeg = pulsos;
    pulsos = 0;
    interrupts();

    // Doble lectura del Funduino con retardo para estabilizar el canal ADC
    analogRead(PIN_FUNDUINO);
    delayMicroseconds(50);
    lecturaFunduino = analogRead(PIN_FUNDUINO);

    caudal = pulsosSeg / K_FLUJO;
    volumen += caudal / 60.0;
    if (pulsosSeg > 0) segundosSinFlujo = 0;
    else if (segundosSinFlujo < 9999) segundosSinFlujo++;

    // Deteccion de humedad con histeresis
    if (lecturaFunduino >= UMBRAL_MOJADO) {
      if (!mojado) {
        // En el instante en que cae la primera gota, otorgar gracia para filtrar
        // cualquier transitorio electrico o contacto inicial en la placa
        darGracia(ahora, GRACIA_ACTUADOR);
      }
      mojado = true;
      estuvoMojado = true;
      // Apagar ventilador inmediatamente ante deteccion de lluvia
      if (velVentilador != 0) {
        velVentilador = 0;
        analogWrite(PIN_VENTILADOR, 0);
      }
      tFinGas = 0; // Cancelar purga si llueve
    } else if (lecturaFunduino <= UMBRAL_SECO) {
      mojado = false;
    }

    // Si estuvo mojado y se seco -> abre tapa y reinicia ciclo
    if (estuvoMojado && !mojado) {
      if (anguloTapa != 0) {
        tapa.write(0);
        anguloTapa = 0;
        darGracia(ahora, GRACIA_ACTUADOR);
      }
      volumen = 0;
      segundosSinFlujo = 0;
      estuvoMojado = false;
      Serial.println(">> LLUVIA: seco. Tapa abierta (0°) y volumen reiniciado.");
    }
    // Si supero 100 mL, lleva 10 s sin flujo y esta mojado -> cierra tapa
    else if (volumen > VOLUMEN_CIERRE && segundosSinFlujo >= SEGUNDOS_SIN_LLUVIA && mojado && anguloTapa != ANGULO_CERRADO) {
      tapa.write(ANGULO_CERRADO);
      anguloTapa = ANGULO_CERRADO;
      darGracia(ahora, GRACIA_ACTUADOR);
      Serial.println(">> LLUVIA: reserva llena y sin flujo. Tapa cerrada (90°).");
    }
  }

  // --- 4. BUZZER COMPARTIDO (Prioridad: Sismo > Gas Emergencia > Apagado) ---
  int modo = alarmaSismo ? 1 : (estadoGas == 2 ? 2 : 0);
  if (modo != modoBuzzer) {
    noTone(PIN_BUZZER);
    digitalWrite(PIN_BUZZER, (modo == 2) ? HIGH : LOW); // Si es buzzer pasivo, usar tone(PIN_BUZZER, 1200)
    modoBuzzer = modo;
    if (modo == 1) {
      tone(PIN_BUZZER, 520, 120); // Primer pitido inmediato
      tBuzzer = ahora;
    }
  } else if (modo == 1 && ahora - tBuzzer >= 1000) {
    tBuzzer = ahora;
    tone(PIN_BUZZER, 520, 120);
  }

  // --- 5. TELEMETRIA POR MONITOR SERIAL (cada 1 s) ---
  if (ahora - tImprimir >= 1000) {
    tImprimir = ahora;

    Serial.print("Sismo: ");   Serial.print(alarmaSismo ? "ALARMA" : (enGracia ? "gracia" : "ok"));
    Serial.print(" N=");       Serial.print(nivelSismo, 3);
    Serial.print(" | Gas: ");
    if (!gasListo) {
      Serial.print("calentando");
    } else {
      Serial.print(estadoGas == 2 ? "EMERG" : (estadoGas == 1 ? "ALERTA" : "ok"));
      Serial.print(" G=");     Serial.print(G, 2);
      Serial.print(" (max ");  Serial.print(G_max, 2); Serial.print(")");
    }
    Serial.print(" | Lluvia: V="); Serial.print(volumen * 1000.0, 0);
    Serial.print("mL F=");         Serial.print(lecturaFunduino);
    Serial.print(mojado ? "(MOJ)" : "(SEC)");
    Serial.print(" tapa=");        Serial.print(anguloTapa);
    Serial.print("° vent=");       Serial.println(velVentilador > 0 ? 100 : 0);
  }

  // --- 6. PANTALLA OLED I2C (actualizacion cada 500 ms) ---
  if (ahora - tOled >= 500) {
    tOled = ahora;
    actualizarOled();
  }
}