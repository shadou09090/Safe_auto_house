# 🏠 Casa Segura — Sistema Integrado de Monitoreo y Protección

Sistema embebido de seguridad y domótica para maqueta desarrollado sobre **Arduino Mega 2560**, con pantalla **OLED I2C (SH1106)** y un panel de control interactivo en tiempo real desarrollado en **Python (Streamlit)**.

---

## 🚀 Características Principales

1. **🌋 Detector Sísmico (ADXL335):**
   - Muestreo a 10 ms con filtro de promedio móvil (ventana de 0.5 s).
   - Umbral de alarma calibrado en **0.400 g** con confirmación de 2.0 s continuos para evitar falsos positivos.
   - Alarma con luz LED roja (Pin 53) y sirena buzzer intermitente (Pin 3).
   - Pulsador físico de "Sitio Seguro" (Pin 11) con tiempo de gracia y re-adaptación rápida de reposo.

2. **💨 Detector de Gas y Humo (MQ-135):**
   - Calibración automática de base de aire limpio ($R_0$) al arranque.
   - Máquina de estados con histéresis:
     - **Aviso:** $\ge 1.80$ (Ventilador al 100%).
     - **Emergencia:** $\ge 3.50$ (Ventilador al 100% + Alarma continua de Buzzer).
   - **Purga de 5 segundos:** El extractor permanece encendido durante **5 segundos adicionales** después de que el gas se disipa para limpiar completamente el aire.
   - **Interbloqueo de seguridad:** El ventilador se inhibe y apaga de inmediato si ocurre un sismo o lluvia.

3. **🌧️ Control de Lluvia y Techo Automatizado:**
   - Placa de gotas (Funduino en A5) con detección por histéresis.
   - Medidor de flujo de agua (Caudalímetro en Pin 18).
   - Servomotor (Pin 12) que cierra el techo (90°) cuando el volumen acumulado supera **100 mL** y cesa el flujo durante 10 segundos.
   - Reapertura automática (0°) y reinicio de contadores cuando la superficie se seca por completo.

4. **🖥️ Pantalla OLED Local (1.3" I2C SH1106):**
   - Conectada a los pines de hardware I2C del Mega (Pin 20 SDA, Pin 21 SCL) a 400 kHz.
   - Visualización instantánea de estados, lecturas numéricas y actuadores.

5. **📊 Panel de Control Web en Tiempo Real (Streamlit):**
   - Interfaz gráfica con diseño de alto contraste.
   - Historial y gráficas en vivo para sismo, gas y agua.
   - Botones interactivos para calibración rápida (`'b'`, `'r'`, `'z'`) sin necesidad de reprogramar.
   - Gestión inteligente del puerto serial para evitar bloqueos entre CLion y Python.

---

## 📌 Diagrama de Conexiones (Arduino Mega 2560)

| Módulo / Componente | Pin Arduino Mega | Tipo | Función |
| :--- | :--- | :--- | :--- |
| **ADXL335 (X, Y, Z)** | **A0, A1, A2** | Analógico | Sensor de aceleración / sismo |
| **MQ-135 (Gas)** | **A3** | Analógico | Sensor químico de gas y calidad de aire |
| **Funduino (Lluvia)** | **A5** | Analógico | Placa detectora de gotas de agua |
| **Caudalímetro Flujo** | **Pin 18** | Digital (Interrupción) | Medición de volumen y flujo |
| **Pulsador Sitio Seguro** | **Pin 11** | Digital (Pull-down) | Silenciar alarma sísmica |
| **Pantalla OLED SH1106** | **Pin 20 (SDA), 21 (SCL)** | I2C | Pantalla gráfica 128x64 |
| **Buzzer** | **Pin 3** | Digital / PWM | Alarma sonora compartida por prioridades |
| **Ventilador Extractor** | **Pin 5** | Salida PWM (MOSFET) | Evacuación de gases (100% potencia) |
| **Servomotor Techo** | **Pin 12** | Salida PWM | Mecanismo de apertura/cierre de techo |
| **LED Rojo** | **Pin 53** | Salida Digital | Luz de emergencia sísmica |

---

## 🛠️ Requisitos e Instalación

### Firmware (Arduino / PlatformIO)
1. Instalar [PlatformIO](https://platformio.org/) (en VS Code o CLion).
2. Compilar y subir el firmware al Arduino Mega conectado por USB:
   ```bash
   pio run -e megaatmega1280 -t upload
   ```

### Dashboard Web (Python)
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Iniciar el panel de control:
   ```bash
   run_dashboard.bat
   ```
   *O alternativamente vía terminal:*
   ```bash
   streamlit run app.py
   ```
3. Abrir en el navegador: `http://localhost:8501`.

---

## 👥 Autores
Proyecto realizado para el Laboratorio Final de Señales y Sistemas — Grupo 5.
