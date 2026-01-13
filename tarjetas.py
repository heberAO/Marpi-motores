import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

# Inicializar variables de estado
if 'guardado' not in st.session_state:
    st.session_state.guardado = False

# 2. DETECTAR QR (Parámetros de URL)
query_tag = st.query_params.get("tag", "")

# 3. MOSTRAR LOGO
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

# 4. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    st.error("Error de conexión con la base de datos.")
    df_completo = pd.DataFrame()

# 5. MENÚ LATERAL
with st.sidebar:
    st.header("⚙️ Menú Marpi")
    # Si viene de QR, selecciona Historial (index 1), sino Registro (index 0)
    default_index = 1 if query_tag else 0
    modo = st.radio("Seleccione:", ["📝 Registro", "🔍 Historial / QR"], index=default_index)

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro":
    st.title("📝 Nueva Reparación / Continuar")
    
    tag = st.text_input("Tag / ID Motor", value=query_tag).strip().upper()
    
    # Buscar datos previos
    datos_previa = {"Pot": "", "Ten": "", "RPM": ""}
    if tag and not df_completo.empty:
        historia = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
        if not historia.empty:
            ultimo = historia.iloc[-1]
            datos_previa = {
                "Pot": str(ultimo.get('Potencia', '')),
                "Ten": str(ultimo.get('Tension', '')),
                "RPM": str(ultimo.get('RPM', ''))
            }
            st.success(f"✅ Motor {tag} encontrado. Datos cargados.")

    with st.form("form_reparacion"):
        c1, c2 = st.columns(2)
        with c1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("Fecha", date.today())
            descripcion = st.text_area("Detalles de la reparación")
        
        with c2:
            st.markdown("**Datos Técnicos**")
            pot = st.text_input("Potencia (HP/kW)", value=datos_previa["Pot"])
            ten = st.text_input("Tensión (V)", value=datos_previa["Ten"])
            rpm = st.text_input("RPM", value=datos_previa["RPM"])
            st.markdown("**Mediciones**")
            rt = st.text_input("Res. Tierra (Ω)")
            rb = st.text_input("Res. E.Bobina (Ω)")
            ri = st.text_input("Res. Interna (Ω)")

        enviar = st.form_submit_button("💾 GUARDAR REGISTRO")

    if enviar:
        if tag and responsable:
            nuevo_log = pd.DataFrame([{
                "Fecha": fecha.strftime("%d/%m/%Y"), 
                "Responsable": responsable, 
                "Tag": tag,
                "Potencia": pot, 
                "Tension": ten, 
                "RPM": rpm,
                "Res_Tierra": rt, 
                "Res_Bobinas": rb, 
                "Res_Interna": ri,
                "Descripcion": descripcion
            }])
            df_final = pd.concat([df_completo, nuevo_log], ignore_index=True)
            conn.update(data=df_final)
            st.session_state.guardado = True
            st.balloons()
            st.success(f"✅ Guardado exitosamente para el motor {tag}")
        else:
            st.error("⚠️ El Tag y el Responsable son obligatorios.")

    if tag:
        st.divider()
        mi_url = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
        link_final = f"{mi_url}?tag={tag}"
        qr_gen = qrcode.make(link_final)
        buf = BytesIO()
        qr_gen.save(buf, format="PNG")
        st.image(buf, width=150, caption=f"QR de acceso: {tag}")

# --- MODO 2: HISTORIAL ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida del Motor")
    
    id_ver = st.text_input("Ingrese ID a consultar:", value=query_tag).strip().upper()
    
    if id_ver:
        if not df_completo.empty:
            res = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
            if not res.empty:
                st.subheader(f"Historial de {id_ver}")
                st.dataframe(res.sort_index(ascending=False), use_container_width=True)
            else:
                st.warning(f"No hay registros para el motor: {id_ver}")
        else:
            st.error("La base de datos está vacía.")

st.markdown("---")
st.caption("Sistema diseñado y desarrollado por **Heber Ortiz** | Marpi Electricidad ⚡")

























































































































