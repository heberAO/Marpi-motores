import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os

# 1. INICIALIZACIÓN
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0
if 'guardado' not in st.session_state:
    st.session_state.guardado = False

st.set_page_config(page_title="Marpi Motores - Registro Continuo", page_icon="⚡", layout="wide")

# --- LÓGICA DE PERSISTENCIA ---
# Función para cargar datos al session_state
def cargar_datos_motor(datos):
    st.session_state[f"pot_{st.session_state.form_id}"] = str(datos.get('Potencia', ''))
    st.session_state[f"ten_{st.session_state.form_id}"] = str(datos.get('Tension', ''))
    st.session_state[f"corr_{st.session_state.form_id}"] = str(datos.get('Corriente', ''))
    st.session_state[f"rpm_{st.session_state.form_id}"] = str(datos.get('RPM', ''))

with st.sidebar:
    st.header("⚙️ Menú Marpi")
    modo = st.radio("Seleccione una opción:", ["📝 Nueva Carga / Continuar", "🔍 Historial Completo"])

if modo == "📝 Nueva Carga / Continuar":
    st.title("SISTEMA DE REGISTRO MARPI ELEC.")
    
    with st.container():
        st.subheader("📋 Identificación del Motor")
        col_tag, col_fecha, col_resp = st.columns([2, 1, 1])
        
        with col_tag:
            tag = st.text_input("Tag / ID Motor", key=f"ins_tag_{st.session_state.form_id}").strip().upper()
            if st.button("🔎 Buscar y Cargar Datos Previos"):
                if tag:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_completo = conn.read(ttl=0)
                    motor_existente = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
                    
                    if not motor_existente.empty:
                        cargar_datos_motor(motor_existente.iloc[-1])
                        st.success(f"✅ Datos cargados del motor {tag}. Listo para nueva reparación.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Motor nuevo. Complete los datos por primera vez.")
                else:
                    st.error("Ingrese un Tag.")

        with col_fecha:
            fecha = st.date_input("Fecha Hoy", date.today(), format="DD/MM/YYYY")
        with col_resp:
            responsable = st.text_input("Técnico", key=f"ins_resp_{st.session_state.form_id}")

    st.divider()
    
    # --- DATOS TÉCNICOS (Se autocompletan si el motor ya existe) ---
    st.subheader("🏷️ Datos de Placa")
    c1, c2, c3, c4 = st.columns(4)
    potencia = c1.text_input("Potencia (HP/kW)", key=f"pot_{st.session_state.form_id}")
    tension = c2.text_input("Tensión (V)", key=f"ten_{st.session_state.form_id}")
    corriente = c3.text_input("Corriente (A)", key=f"corr_{st.session_state.form_id}")
    rpm = c4.text_input("RPM", key=f"rpm_{st.session_state.form_id}")

    # --- NUEVA REPARACIÓN ---
    st.subheader("🛠️ Nueva Intervención")
    m1, m2, m3 = st.columns(3)
    res_tierra = m1.text_input("Res. Tierra (MΩ)", key=f"rt_{st.session_state.form_id}")
    res_bobinas = m2.text_input("Res. Bobinas (Ω)", key=f"rb_{st.session_state.form_id}")
    res_interna = m3.text_input("Res. Interna (Ω)", key=f"ri_{st.session_state.form_id}")
    
    descripcion = st.text_area("Detalle de la reparación actual", placeholder="¿Qué se le hizo hoy al motor?")
    externo = st.text_area("Trabajos de terceros (opcional)")

    if st.button("💾 GUARDAR NUEVA ENTRADA AL HISTORIAL"):
        if tag and responsable:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_previo = conn.read(ttl=0)
                nuevo_log = pd.DataFrame([{
                    "Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag,
                    "Potencia": potencia, "Tension": tension, "Corriente": corriente, "RPM": rpm,
                    "Res_Tierra": res_tierra, "Res_Bobinas": res_bobinas, "Res_interna": res_interna,
                    "Descripcion": descripcion, "Externo": externo
                }])
                df_final = pd.concat([df_previo, nuevo_log], ignore_index=True)
                conn.update(data=df_final)
                st.session_state.guardado = True
                st.balloons()
                st.success(f"✅ Se agregó una nueva reparación al historial del motor {tag}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Faltan datos obligatorios (Tag o Técnico).")

    # --- QR ÚNICO ---
    if st.session_state.guardado:
        qr_text = f"MARPI - MOTOR: {tag}\nVer historial en sistema con este ID."
        qr = qrcode.make(qr_text)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf, caption="Este QR identifica al motor para siempre", width=150)
        if st.button("🔄 Cargar otro motor"):
            st.session_state.form_id += 1
            st.session_state.guardado = False
            st.rerun()

elif modo == "🔍 Historial Completo":
    st.title("🔍 Hoja de Vida del Motor")
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    tag_buscar = st.text_input("Tag a consultar:").strip().upper()
    if tag_buscar:
        historia = df[df['Tag'].astype(str).str.upper() == tag_buscar]
        if not historia.empty:
            st.write(f"### Cronología de {tag_buscar}")
            st.table(historia[['Fecha', 'Responsable', 'Descripcion', 'Res_Tierra']].sort_index(ascending=False))
        else:
            st.warning("Sin registros.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

st.markdown("---")
st.caption("Sistema Marpi Electricidad ⚡")





















































































