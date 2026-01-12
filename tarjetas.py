import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

# 1. INICIALIZACIÓN
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0
if 'guardado' not in st.session_state:
    st.session_state.guardado = False

st.set_page_config(page_title="Marpi Motores - Técnico", page_icon="⚡", layout="wide")

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    st.header("⚙️ Menú Marpi")
    modo = st.radio("Seleccione una opción:", ["📝 Nueva Carga", "🔍 Historial y Buscador"])

# --- LÓGICA DE NUEVA CARGA ---
if modo == "📝 Nueva Carga":
    st.title("SISTEMA DE REGISTRO MARPI ELEC.")
    
    with st.container():
        st.subheader("📋 Datos del Servicio")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            fecha = st.date_input("Fecha", date.today(), format="DD/MM/YYYY", key=f"f_nueva_{st.session_state.form_id}")
        
        with col_b:
            tag = st.text_input("Tag / ID Motor", key=f"ins_tag_{st.session_state.form_id}").strip().upper()
            if st.button("🔎 Buscar Historial de este Motor", key=f"btn_search_{st.session_state.form_id}"):
                if tag:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_completo = conn.read(ttl=0)
                    # Buscamos registros previos para precargar datos técnicos
                    motor_existente = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
                    
                    if not motor_existente.empty:
                        datos = motor_existente.iloc[-1]
                        st.session_state[f"pot_{st.session_state.form_id}"] = str(datos.get('Potencia', ''))
                        st.session_state[f"ten_{st.session_state.form_id}"] = str(datos.get('Tension', ''))
                        st.session_state[f"corr_{st.session_state.form_id}"] = str(datos.get('Corriente', ''))
                        st.session_state[f"rpm_{st.session_state.form_id}"] = str(datos.get('RPM', ''))
                        st.success(f"✅ Motor encontrado. {len(motor_existente)} reparaciones previas.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Motor nuevo (no hay datos previos).")
                else:
                    st.error("Escribe un Tag primero.")

        with col_c:
            responsable = st.text_input("Técnico Responsable", key=f"ins_resp_{st.session_state.form_id}")

    st.markdown("---")
    
    # --- SECCIÓN DATOS TÉCNICOS ---
    st.subheader("🏷️ Datos de Placa e Inspección")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        potencia = st.text_input("Potencia (HP/kW)", key=f"pot_{st.session_state.form_id}")
    with col_p2:
        tension = st.text_input("Tensión (V)", key=f"ten_{st.session_state.form_id}")
    with col_p3:
        corriente = st.text_input("Corriente (A)", key=f"corr_{st.session_state.form_id}")
    with col_p4:
        rpm = st.text_input("RPM", key=f"rpm_{st.session_state.form_id}")

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        res_tierra = st.text_input("Res. Tierra (MΩ)", key=f"rt_{st.session_state.form_id}")
    with col_m2:
        res_bobinas = st.text_input("Res. Bobinas (Ω)", key=f"rb_{st.session_state.form_id}")
    with col_m3:
        res_interna = st.text_input("Res. Interna (Ω)", key=f"ri_{st.session_state.form_id}")
    
    descripcion = st.text_area("Detalles de Reparación", key=f"desc_{st.session_state.form_id}")
    externo = st.text_area("Trabajos Externos", key=f"ext_{st.session_state.form_id}")

    # --- BOTONES DE ACCIÓN ---
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 GUARDAR Y GENERAR QR"):
            if not tag or not responsable:
                st.error("⚠️ Tag y Responsable son obligatorios.")
            else:
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_existente = conn.read(ttl=0)
                    nuevo = pd.DataFrame([{
                        "Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag,
                        "Potencia": potencia, "Tension": tension, "Corriente": corriente, "RPM": rpm,
                        "Res_Tierra": res_tierra, "Res_Bobinas": res_bobinas, "Res_interna": res_interna,
                        "Descripcion": descripcion, "Externo": externo
                    }])
                    df_final = pd.concat([df_existente, nuevo], ignore_index=True)
                    conn.update(data=df_final)
                    st.session_state.guardado = True
                    st.success("✅ Guardado en Historial.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    with col_btn2:
        if st.button("🧹 NUEVO REGISTRO"):
            st.session_state.form_id += 1
            st.session_state.guardado = False
            st.rerun()

    # --- MOSTRAR QR SI SE GUARDÓ ---
    if st.session_state.guardado:
        st.divider()
        qr_text = f"MARPI MOTOR ID: {tag}\nUlt. Rep: {fecha.strftime('%d/%m/%Y')}\nPot: {potencia}"
        qr = qrcode.make(qr_text)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf, caption=f"QR único para Motor {tag}", width=200)

# --- LÓGICA DE HISTORIAL (ENLACE DE DATOS) ---
elif modo == "🔍 Historial y Buscador":
    st.title("🔍 Historial por Motor (ID)")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        id_buscado = st.text_input("Ingrese el Tag para ver su historial:").strip().upper()
        
        if id_buscado:
            # Filtrar todas las reparaciones del mismo ID
            historial = df[df['Tag'].astype(str).str.upper() == id_buscado]
            if not historial.empty:
                st.subheader(f"Hoja de Vida: {id_buscado}")
                st.dataframe(historial.sort_index(ascending=False))
            else:
                st.warning("No hay registros para este ID.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

st.markdown("---")
st.caption("Sistema Marpi Electricidad ⚡")




















































































