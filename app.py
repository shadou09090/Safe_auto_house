"""
Casa Segura - Panel de Control & Telemetría en Tiempo Real
Arduino Mega 2560 - Arquitectura Robusta y Anti-bloqueos.
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import re
import threading
import collections
import atexit
from datetime import datetime
import serial
import serial.tools.list_ports

# Configuración de página
st.set_page_config(
    page_title="Casa Segura | Panel de Control",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILOS CSS (DISEÑO BLANCO Y AZUL LIMPIO CON CONTRASTE MÁXIMO)
# ==============================================================================
st.markdown("""
<style>
    /* Estructura general */
    .stApp {
        background-color: #F1F5F9;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        color: #0F172A;
    }

    /* Pestañas (Tabs) con texto negro, grande y 100% visible */
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        color: #000000 !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        padding: 10px 18px !important;
        background-color: #E2E8F0 !important;
        border-radius: 8px 8px 0 0 !important;
        margin-right: 6px !important;
        border: 1px solid #CBD5E1 !important;
        border-bottom: none !important;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"] p,
    [data-testid="stTabs"] button[data-baseweb="tab"] div,
    [data-testid="stTabs"] button[data-baseweb="tab"] span {
        color: #000000 !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        color: #000000 !important;
        background-color: #FFFFFF !important;
        border-top: 4px solid #1D4ED8 !important;
        border-left: 1.5px solid #94A3B8 !important;
        border-right: 1.5px solid #94A3B8 !important;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] p,
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] div,
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] span {
        color: #000000 !important;
        font-size: 1.18rem !important;
        font-weight: 900 !important;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        background-color: #DBEAFE !important;
    }

    /* Encabezado superior */
    .hero-banner {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #3B82F6 100%);
        color: #FFFFFF;
        padding: 22px 28px;
        border-radius: 14px;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(30, 58, 138, 0.2);
    }
    .hero-banner h1 {
        color: #FFFFFF !important;
        font-size: 1.85rem;
        font-weight: 800;
        margin: 0 0 6px 0;
    }
    .hero-banner p {
        color: #DBEAFE !important;
        font-size: 0.98rem;
        margin: 0;
    }

    /* Título de cada tarjeta */
    .card-title {
        color: #0F172A;
        font-size: 1.25rem;
        font-weight: 800;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 8px;
    }

    /* Explicación simple */
    .simple-desc {
        background-color: #EFF6FF;
        border-left: 4px solid #2563EB;
        padding: 10px 14px;
        border-radius: 6px;
        color: #1E3A8A;
        font-size: 0.88rem;
        margin-bottom: 14px;
        line-height: 1.45;
        font-weight: 500;
    }

    /* Caja de Métrica con Alto Contraste */
    .metric-box {
        background-color: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        padding: 12px 14px;
        text-align: center;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .metric-box-label {
        font-size: 0.82rem;
        font-weight: 800;
        color: #334155;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .metric-box-val {
        font-size: 1.95rem;
        font-weight: 900;
        color: #0F172A;
        line-height: 1.1;
    }
    .metric-box-val.highlight {
        color: #1D4ED8;
    }

    /* Estado en texto grande */
    .status-pill {
        display: block;
        text-align: center;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 0.92rem;
        letter-spacing: 0.5px;
        margin-bottom: 14px;
    }
    .pill-ok {
        background-color: #DBEAFE;
        color: #1E40AF;
        border: 1.5px solid #93C5FD;
    }
    .pill-warning {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1.5px solid #FCD34D;
    }
    .pill-danger {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1.5px solid #FCA5A5;
        animation: pulse 1s infinite alternate;
    }

    /* Fila de componente o actuador */
    .device-row {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 9px 12px;
        margin-top: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.88rem;
    }
    .device-name {
        font-weight: 700;
        color: #1E293B;
    }
    .device-active {
        color: #1E40AF;
        font-weight: 800;
        background: #DBEAFE;
        padding: 3px 10px;
        border-radius: 6px;
        border: 1px solid #93C5FD;
    }
    .device-inactive {
        color: #475569;
        font-weight: 600;
        background: #F1F5F9;
        padding: 3px 10px;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
    }

    /* Alerta de puerto bloqueado */
    .port-warning-box {
        background: #FFFBEB;
        border: 2px solid #F59E0B;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        color: #92400E;
    }
    .port-warning-box h4 {
        margin: 0 0 6px 0;
        color: #B45309;
        font-size: 1.1rem;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# GESTOR ROBUSTO DE HARDWARE (SINGLETON CON CACHE-RESOURCE)
# ==============================================================================
class HardwareBridge:
    def __init__(self):
        self.serial_port = None
        self.port_name = "COM8"
        self.baudrate = 115200
        self.is_connected = False
        self.port_busy_by_clion = False
        self.simulation_mode = False
        self.connection_enabled = True
        self.running = True

        # Datos en tiempo real
        self.data_lock = threading.Lock()
        self.current = {
            "timestamp": datetime.now(),
            # Sismo
            "sismo_estado": "ok",      # ok, gracia, ALARMA
            "sismo_nivel": 0.010,      # g
            "act_led": False,          # Pin 53
            "act_buzzer_sismo": False, # Pin 3
            # Gas
            "gas_estado": "calentando",# calentando, ok, ALERTA, EMERG
            "gas_g": 1.05,
            "gas_g_max": 1.10,
            "act_ventilador": 0,       # 0%, 50%, 100%
            "act_buzzer_gas": False,   # Pin 3
            # Lluvia
            "lluvia_volumen": 0.0,     # mL
            "lluvia_funduino": 0,      # Humedad
            "lluvia_mojado": False,
            "lluvia_tapa": 0,          # 0° (Abierta) o 90° (Cerrada)
            "raw_line": ""
        }

        self.history = collections.deque(maxlen=60)
        self.logs = collections.deque(maxlen=50)

        # Iniciar hilo de conexión en segundo plano
        self.thread = threading.Thread(target=self._auto_manager_thread, daemon=True)
        self.thread.start()

    def log_msg(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")

    def close_port(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.is_connected = False

    def _auto_manager_thread(self):
        """Monitorea continuamente la conexión y recupera el puerto automáticamente."""
        while self.running:
            if not self.connection_enabled:
                self.close_port()
                time.sleep(0.5)
                continue

            if self.simulation_mode:
                self._run_simulation_step()
                time.sleep(1.0)
                continue

            # Si no está conectado, intentar abrir el puerto
            if not self.is_connected:
                ports = [p.device for p in serial.tools.list_ports.comports()]
                target_port = self.port_name if self.port_name in ports else (ports[0] if ports else None)

                if target_port:
                    try:
                        self.serial_port = serial.Serial(target_port, self.baudrate, timeout=1.0)
                        self.is_connected = True
                        self.port_busy_by_clion = False
                        self.port_name = target_port
                        self.log_msg(f"Conectado exitosamente a {target_port}.")
                    except serial.SerialException as e:
                        err_str = str(e)
                        if "Acceso denegado" in err_str or "PermissionError" in err_str or "Access is denied" in err_str:
                            self.port_busy_by_clion = True
                        else:
                            self.port_busy_by_clion = False
                        self.is_connected = False
                        time.sleep(1.5)
                        continue
                    except Exception:
                        self.is_connected = False
                        time.sleep(1.5)
                        continue
                else:
                    time.sleep(1.5)
                    continue

            # Si está conectado, leer líneas continuas
            try:
                line = self.serial_port.readline().decode('utf-8', errors='ignore')
                if line:
                    self._parse_line(line)
            except Exception as e:
                self.close_port()
                self.log_msg(f"Reconectando puerto: {e}")
                time.sleep(1.0)

    def _parse_line(self, line: str):
        line = line.strip()
        if not line:
            return

        if line.startswith(">>") or line.startswith("Casa segura") or line.startswith("Listo"):
            self.log_msg(line)
            return

        # Sismo: ok N=0.031 | Gas: ALERTA G=1.70 (max 25.94) | Lluvia: V=0mL F=2(SEC) tapa=0°
        s_match = re.search(r"Sismo:\s*([A-Za-z]+)\s*N=([0-9.]+)", line)
        g_match = re.search(r"Gas:\s*([A-Za-z]+)(?:\s*G=([0-9.]+)\s*\(max\s*([0-9.]+)\))?", line)
        l_match = re.search(r"Lluvia:\s*V=([0-9.]+)mL\s*F=([0-9]+)\(([A-Z]+)\)\s*tapa=([0-9]+)", line)

        if s_match:
            with self.data_lock:
                now = datetime.now()
                self.current["timestamp"] = now
                self.current["raw_line"] = line

                # Sismo
                s_est = s_match.group(1).strip()
                self.current["sismo_estado"] = s_est
                self.current["sismo_nivel"] = float(s_match.group(2))
                self.current["act_led"] = (s_est.upper() == "ALARMA")
                self.current["act_buzzer_sismo"] = (s_est.upper() == "ALARMA")

                # Gas
                if g_match:
                    g_est = g_match.group(1).strip()
                    self.current["gas_estado"] = g_est
                    if g_match.group(2) is not None:
                        self.current["gas_g"] = float(g_match.group(2))
                        self.current["gas_g_max"] = float(g_match.group(3))
                    else:
                        self.current["gas_g"] = 0.0

                    if g_est.upper() == "EMERG":
                        self.current["act_ventilador"] = 100
                        self.current["act_buzzer_gas"] = True
                    elif g_est.upper() == "ALERTA":
                        self.current["act_ventilador"] = 100
                        self.current["act_buzzer_gas"] = False
                    else:
                        self.current["act_ventilador"] = 0
                        self.current["act_buzzer_gas"] = False

                # Lluvia
                if l_match:
                    self.current["lluvia_volumen"] = float(l_match.group(1))
                    self.current["lluvia_funduino"] = int(l_match.group(2))
                    self.current["lluvia_mojado"] = (l_match.group(3).upper() == "MOJ")
                    self.current["lluvia_tapa"] = int(l_match.group(4))

                # Lectura directa del ventilador desde Arduino (incluye los 5s de purga)
                vent_match = re.search(r"vent=(\d+)", line)
                if vent_match:
                    self.current["act_ventilador"] = int(vent_match.group(1))

                # Regla: El ventilador SOLO se activa si hay gas y NO hay sismo ni lluvia
                s_activo = (s_est.upper() == "ALARMA")
                lluvia_activa = self.current["lluvia_mojado"] or (self.current["lluvia_tapa"] != 0)
                if s_activo or lluvia_activa:
                    self.current["act_ventilador"] = 0

                # Historial
                self.history.append({
                    "time": now.strftime("%H:%M:%S"),
                    "sismo": self.current["sismo_nivel"],
                    "gas": self.current["gas_g"],
                    "agua_ml": self.current["lluvia_volumen"]
                })

    def _run_simulation_step(self):
        with self.data_lock:
            now = datetime.now()
            s_val = round(0.02 + 0.015 * np.random.rand(), 3)
            g_val = round(1.10 + 0.20 * np.random.rand(), 2)
            self.current["timestamp"] = now
            self.current["sismo_estado"] = "ok"
            self.current["sismo_nivel"] = s_val
            self.current["gas_estado"] = "ok"
            self.current["gas_g"] = g_val
            self.current["act_ventilador"] = 0
            self.current["act_led"] = False
            self.current["act_buzzer_sismo"] = False
            self.current["act_buzzer_gas"] = False
            self.current["lluvia_volumen"] = 0.0
            self.current["lluvia_tapa"] = 0
            self.current["raw_line"] = f"Sismo: ok N={s_val} | Gas: ok G={g_val} | Lluvia: V=0mL F=10(SEC) tapa=0°"
            self.history.append({
                "time": now.strftime("%H:%M:%S"),
                "sismo": s_val,
                "gas": g_val,
                "agua_ml": 0.0
            })

    def send_cmd(self, cmd: str):
        if self.is_connected and self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(cmd.encode('utf-8'))
                self.log_msg(f"Comando enviado: '{cmd}'")
                return True
            except Exception as e:
                self.log_msg(f"Error enviando comando: {e}")
        return False


# ==============================================================================
# INICIALIZACIÓN CON CACHE_RESOURCE (UNA SOLA INSTANCIA NUNCA CONFLICTIVA)
# ==============================================================================
@st.cache_resource
def get_hardware_bridge():
    return HardwareBridge()

bridge = get_hardware_bridge()

# Liberar el puerto si Python o Streamlit se cierran
def on_app_exit():
    bridge.close_port()

atexit.register(on_app_exit)


# ==============================================================================
# BARRA LATERAL SENCILLA
# ==============================================================================
with st.sidebar:
    st.markdown("### 🔌 Conexión con Arduino")

    ports = [p.device for p in serial.tools.list_ports.comports()]
    if not ports:
        ports = ["COM8"]

    chosen_port = st.selectbox("Puerto Detectado:", options=ports, index=ports.index("COM8") if "COM8" in ports else 0)
    if chosen_port != bridge.port_name:
        bridge.port_name = chosen_port
        bridge.close_port()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Reconectar", use_container_width=True):
            bridge.close_port()
            bridge.port_busy_by_clion = False
            st.rerun()

    with col_btn2:
        if st.button("⏹️ Desconectar", use_container_width=True):
            bridge.connection_enabled = False
            bridge.close_port()
            st.rerun()

    conn_toggle = st.toggle("🔌 Conexión activa", value=bridge.connection_enabled, help="Desactiva esto temporalmente si vas a subir código nuevo desde CLion para liberar el puerto COM8.")
    if conn_toggle != bridge.connection_enabled:
        bridge.connection_enabled = conn_toggle
        if not conn_toggle:
            bridge.close_port()
        st.rerun()

    if not bridge.connection_enabled:
        st.info("⏸️ **Conexión en pausa**: Puerto COM8 libre para subir código desde CLion.")
    elif bridge.is_connected:
        st.success(f"🟢 **Conectado a {bridge.port_name}** (115200 bps)")
    elif bridge.port_busy_by_clion:
        st.warning("⚠️ **Puerto ocupado por CLion**")
    else:
        st.info("🟡 Conectando automáticamente...")

    st.markdown("---")
    st.markdown("### 🛠️ Botones de Control")
    st.caption("Enviar órdenes rápidas al Arduino:")

    if st.button("🌬️ Calibrar Sensor de Gas ('b')", use_container_width=True):
        bridge.send_cmd('b')
        st.toast("Comando 'b' enviado (nueva base de aire limpio)")

    if st.button("🔄 Reiniciar Máximo de Gas ('r')", use_container_width=True):
        bridge.send_cmd('r')
        st.toast("Comando 'r' enviado (G_max reiniciado)")

    if st.button("📍 Calibrar Reposo de Sismo ('z')", use_container_width=True):
        bridge.send_cmd('z')
        st.toast("Comando 'z' enviado (acelerómetro en reposo)")

    st.markdown("---")
    sim_check = st.toggle("Modo Simulación (Sin cables)", value=bridge.simulation_mode)
    if sim_check != bridge.simulation_mode:
        bridge.simulation_mode = sim_check
        st.rerun()


# ==============================================================================
# ENCABEZADO PRINCIPAL
# ==============================================================================
st.markdown("""
<div class="hero-banner">
    <h1>🏠 Casa Segura — Panel de Monitoreo</h1>
    <p>Supervisa en tiempo real los sensores de seguridad y los dispositivos de protección de la maqueta.</p>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# CONTENIDO EN VIVO (ACTUALIZA CADA SEGUNDO)
# ==============================================================================
@st.fragment(run_every=1.0)
def show_dashboard():
    with bridge.data_lock:
        d = dict(bridge.current)
        hist = list(bridge.history)
        logs = list(bridge.logs)

    # ALERTA CLARA SI EL PUERTO ESTÁ BLOQUEADO POR CLION
    if bridge.port_busy_by_clion and bridge.connection_enabled:
        st.markdown(f"""
        <div class="port-warning-box">
            <h4>⚠️ ¡El puerto {bridge.port_name} está ocupado por CLion!</h4>
            <p style="margin: 0 0 8px 0;">
                Actualmente tienes abierta la pestaña <b>"Upload and Monitor"</b> en CLion. En Windows, un puerto solo puede ser leído por un programa a la vez.
            </p>
            <p style="margin: 0; font-weight: 700;">
                👉 Para ver los datos en esta página: Ve a CLion y <u>cierra la pestaña "Upload and Monitor"</u> (haciendo clic en la <b>X</b> de la pestaña). Luego presiona el botón <b>🔄 Reconectar</b> a la izquierda.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 3 TARJETAS PRINCIPALES: SISMO, GAS Y LLUVIA
    col1, col2, col3 = st.columns(3)

    # ---------------- 1. SISMO ----------------
    with col1:
        with st.container(border=True):
            st.markdown("""
            <div class="card-title">🌋 Detector de Terremotos</div>
            <div class="simple-desc">
                <b>¿Qué hace?</b> Mide si la casa vibra. Si el temblor es fuerte y dura más de 2 segundos, enciende la alarma.
            </div>
            """, unsafe_allow_html=True)

            s_est = d["sismo_estado"].upper()
            if s_est == "ALARMA":
                st.markdown('<div class="status-pill pill-danger">🚨 ¡ALERTA DE TERREMOTO!</div>', unsafe_allow_html=True)
            elif s_est == "GRACIA":
                st.markdown('<div class="status-pill pill-warning">⏳ PAUSA (PERSONA A SALVO)</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-pill pill-ok">✅ ESTABLE (SIN TEMBLOR)</div>', unsafe_allow_html=True)

            # Métricas con alto contraste
            m1, m2 = st.columns(2)
            with m1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-label">Vibración Actual</div>
                    <div class="metric-box-val highlight">{d['sismo_nivel']:.3f} g</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown("""
                <div class="metric-box">
                    <div class="metric-box-label">Límite Alarma</div>
                    <div class="metric-box-val" style="color: #DC2626;">0.400 g</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='font-size:0.85rem; font-weight:800; color:#334155; margin: 10px 0 6px 0;'>DISPOSITIVOS ACTIVOS:</div>", unsafe_allow_html=True)
            
            led_txt = "🔴 ENCENDIDO" if d["act_led"] else "⚪ Apagado"
            led_cls = "device-active" if d["act_led"] else "device-inactive"
            st.markdown(f'<div class="device-row"><span class="device-name">Foco LED Rojo (Luz de aviso)</span><span class="{led_cls}">{led_txt}</span></div>', unsafe_allow_html=True)

            buzz_txt = "🔊 SONANDO" if d["act_buzzer_sismo"] else "🔇 En silencio"
            buzz_cls = "device-active" if d["act_buzzer_sismo"] else "device-inactive"
            st.markdown(f'<div class="device-row"><span class="device-name">Sirena Buzzer (Sonido)</span><span class="{buzz_cls}">{buzz_txt}</span></div>', unsafe_allow_html=True)

            st.markdown('<div class="device-row"><span class="device-name">Botón de Sitio Seguro</span><span class="device-inactive">Listo para pulsar</span></div>', unsafe_allow_html=True)

    # ---------------- 2. GAS ----------------
    with col2:
        with st.container(border=True):
            st.markdown("""
            <div class="card-title">💨 Detector de Gas y Humo</div>
            <div class="simple-desc">
                <b>¿Qué hace?</b> Mide gas en el aire. Si hay fuga leve enciende el ventilador a media potencia; si es grave va al 100% y suena alarma.
            </div>
            """, unsafe_allow_html=True)

            g_est = d["gas_estado"].upper()
            if g_est == "EMERG":
                st.markdown('<div class="status-pill pill-danger">🔥 ¡EMERGENCIA: FUGA GRAVE!</div>', unsafe_allow_html=True)
            elif g_est == "ALERTA":
                st.markdown('<div class="status-pill pill-warning">⚠️ AVISO: GAS DETECTADO</div>', unsafe_allow_html=True)
            elif g_est == "CALENTANDO":
                st.markdown('<div class="status-pill pill-ok">⏳ Calentando sensor (30s)...</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-pill pill-ok">✅ AIRE LIMPIO Y SEGURO</div>', unsafe_allow_html=True)

            # Métricas con alto contraste
            gm1, gm2 = st.columns(2)
            with gm1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-label">Nivel de Gas (G)</div>
                    <div class="metric-box-val highlight">{d['gas_g']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with gm2:
                st.markdown("""
                <div class="metric-box">
                    <div class="metric-box-label">Límite Alarma</div>
                    <div class="metric-box-val" style="color: #DC2626;">3.50</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="font-size: 0.80rem; color: #475569; text-align: center; margin: -6px 0 10px 0; font-weight: 600;">
                Aviso leve: <b>≥ 1.80</b> | Alarma grave: <b>≥ 3.50</b> | Pico: <b>{d['gas_g_max']:.2f}</b>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='font-size:0.85rem; font-weight:800; color:#334155; margin: 10px 0 6px 0;'>DISPOSITIVOS ACTIVOS:</div>", unsafe_allow_html=True)
            
            vent_val = d["act_ventilador"]
            if vent_val == 100:
                if d["gas_estado"].upper() in ["ALERTA", "EMERG"]:
                    vent_txt = "🌀 100% (Extrayendo gas)"
                else:
                    vent_txt = "🌀 100% (Purga 5s post-gas)"
                vent_cls = "device-active"
            elif vent_val == 50:
                vent_txt = "🌀 50% (Media potencia)"
                vent_cls = "device-active"
            else:
                vent_txt = "⚪ Apagado (0%)"
                vent_cls = "device-inactive"
            st.markdown(f'<div class="device-row"><span class="device-name">Ventilador Extractor</span><span class="{vent_cls}">{vent_txt}</span></div>', unsafe_allow_html=True)

            buzz_g_txt = "🔊 ALARMA CONTINUA" if d["act_buzzer_gas"] else "🔇 En silencio"
            buzz_g_cls = "device-active" if d["act_buzzer_gas"] else "device-inactive"
            st.markdown(f'<div class="device-row"><span class="device-name">Sirena Buzzer por Gas</span><span class="{buzz_g_cls}">{buzz_g_txt}</span></div>', unsafe_allow_html=True)

            st.markdown('<div class="device-row"><span class="device-name">Sensor Químico MQ-135</span><span class="device-inactive">Vigilando aire</span></div>', unsafe_allow_html=True)

    # ---------------- 3. LLUVIA Y TECHO ----------------
    with col3:
        with st.container(border=True):
            st.markdown("""
            <div class="card-title">🌧️ Control de Lluvia y Techo</div>
            <div class="simple-desc">
                <b>¿Qué hace?</b> Mide cuánta agua cae. Si caen más de 100 mL de agua, un servomotor cierra el techo automáticamente para no inundar.
            </div>
            """, unsafe_allow_html=True)

            if d["lluvia_tapa"] >= 80:
                st.markdown('<div class="status-pill pill-warning">🔒 TECHO CERRADO (90°)</div>', unsafe_allow_html=True)
            elif d["lluvia_mojado"]:
                st.markdown('<div class="status-pill pill-warning" style="background:#DBEAFE; color:#1E40AF; border-color:#93C5FD;">💧 LLUEVE / TECHO ABIERTO</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-pill pill-ok">☀️ SECO / TECHO ABIERTO (0°)</div>', unsafe_allow_html=True)

            # Métricas con alto contraste
            lm1, lm2 = st.columns(2)
            with lm1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-label">Agua Caída</div>
                    <div class="metric-box-val highlight">{d['lluvia_volumen']:.0f} mL</div>
                </div>
                """, unsafe_allow_html=True)
            with lm2:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-label">Sensor de Gotas</div>
                    <div class="metric-box-val" style="color: #0284C7;">{d['lluvia_funduino']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='font-size:0.85rem; font-weight:800; color:#334155; margin: 10px 0 6px 0;'>DISPOSITIVOS ACTIVOS:</div>", unsafe_allow_html=True)

            tapa_txt = "🔒 CERRADO (90°)" if d["lluvia_tapa"] >= 80 else "🔓 ABIERTO (0°)"
            tapa_cls = "device-active" if d["lluvia_tapa"] >= 80 else "device-inactive"
            st.markdown(f'<div class="device-row"><span class="device-name">Motor del Techo (Servo)</span><span class="{tapa_cls}">{tapa_txt}</span></div>', unsafe_allow_html=True)

            moj_txt = "💧 Hay agua encima" if d["lluvia_mojado"] else "☀️ Superficie seca"
            moj_cls = "device-active" if d["lluvia_mojado"] else "device-inactive"
            st.markdown(f'<div class="device-row"><span class="device-name">Placa de Gotas (Funduino)</span><span class="{moj_cls}">{moj_txt}</span></div>', unsafe_allow_html=True)

            st.markdown('<div class="device-row"><span class="device-name">Medidor de Flujo de Agua</span><span class="device-inactive">Contando gotas</span></div>', unsafe_allow_html=True)

    # ---------------- GRÁFICAS SENCILLAS ----------------
    st.markdown("### 📈 Historial en Tiempo Real")
    if len(hist) > 1:
        df = pd.DataFrame(hist).set_index("time")
        gt1, gt2, gt3 = st.tabs(["🌋 Vibración (Sismo)", "💨 Gas en el Aire", "🌧️ Agua Acumulada"])
        with gt1:
            st.line_chart(df[["sismo"]], color="#2563EB")
        with gt2:
            st.line_chart(df[["gas"]], color="#1E3A8A")
        with gt3:
            st.line_chart(df[["agua_ml"]], color="#3B82F6")
    else:
        st.info("Esperando datos para dibujar los gráficos...")

    # ---------------- REGISTRO DE TEXTO DIRECTO ----------------
    with st.expander("📄 Ver datos crudos del Arduino", expanded=False):
        st.write("**Último mensaje recibido:**")
        st.code(d["raw_line"] if d["raw_line"] else "Esperando conexión con el Arduino...")
        if logs:
            st.text_area("Registro de avisos:", value="\n".join(reversed(logs)), height=120, disabled=True)


show_dashboard()
