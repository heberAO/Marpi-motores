import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse

# --- 1. FUNCIÓN PDF UNIFICADA ---
def generar_pdf_reporte(datos, tag_motor, tipo_trabajo="INFORME TÉCNICO"):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 30)
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, f'{tipo_trabajo}', 0, 1, 'R')
        pdf.ln(10)
        pdf.set_fill_color(230, 233, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 8, f"Fecha: {datos.get('Fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos.get('Responsable','-')}", 1, 1)
        pdf.cell(190, 8, f"Detalle: {datos.get('Descripcion','-')}", 1, 1)
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

# --- 2. CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="Marpi Motores", layout="wide")

# Inicializar memorias (Session State)
if "tag_fijo" not in st.session_state: st.session_state.tag_fijo = ""
if "serie_fija" not in st.session_state: st.session_state.serie_fija = ""

# --- 3. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    df_completo = pd.DataFrame()

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    modo = st.radio("MENÚ:", ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"])

# --- 5. SECCIONES ---

if modo == "Nuevo Registro":
    st.title("📝 Alta de Motor")
    with st.form("alta"):
        t = st.text_input("TAG MOTOR").upper()
        resp = st.text_input("Técnico")
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Responsable": resp, "Descripcion": "ALTA DE EQUIPO"}
            df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_final)
            st.success("Guardado"); st.rerun()

elif modo == "Historial y QR":
    st.title("🔍 Consulta y Generador de QR")
    if not df_completo.empty:
        lista_tags = [""] + sorted(list(df_completo['Tag'].unique()))
        buscado = st.selectbox("Seleccioná Motor:", lista_tags)
        
        if buscado:
            # Guardamos en memoria para las otras pestañas
            st.session_state.tag_fijo = buscado
            info = df_completo[df_completo['Tag'] == buscado].iloc[-1]
            st.session_state.serie_fija = info.get('N_Serie', '')

            st.header(f"🚜 Equipo: {buscado}")
            
            # --- GENERADOR DE QR (Sin librerías fallas) ---
            url_app = f"https://marpi-motores.streamlit.app/?tag={buscado}"
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
            
            c1, c2 = st.columns([1, 3])
            c1.image(qr_url, caption="QR del Motor")
            c2.write("Indique al personal que escanee este código para ver el historial.")
            
            # --- HISTORIAL ---
            st.subheader("📜 Historial")
            hist = df_completo[df_completo['Tag'] == buscado].copy()
            for idx, fila in hist.iterrows():
                with st.expander(f"📅 {fila['Fecha']} - {fila['Responsable']}"):
                    pdf_b = generar_pdf_reporte(fila.to_dict(), buscado)
                    st.download_button("📥 PDF", pdf_b, f"Informe_{idx}.pdf", key=f"h_{idx}")

elif modo == "Relubricacion":
    st.title("🛢️ Registro de Engrase")
    # El campo se autocompleta si buscaste antes en el Historial
    with st.form("relub"):
        tag_r = st.text_input("TAG MOTOR", value=st.session_state.tag_fijo).upper()
        gr_la = st.text_input("Gramos LA")
        gr_loa = st.text_input("Gramos LOA")
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": tag_r, "Descripcion": f"ENGRASE LA:{gr_la}g LOA:{gr_loa}g"}
            df_f = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_f)
            st.success("Registrado")

elif modo == "Mediciones de Campo":
    st.title("⚡ Megado de Campo")
    with st.form("campo"):
        tag_c = st.text_input("TAG MOTOR", value=st.session_state.tag_fijo).upper()
        res_m = st.text_input("Resultado MΩ")
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": tag_c, "Descripcion": f"MEGADO: {res_m} MΩ"}
            df_f = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_f)
            st.success("Registrado")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")




















































































































































































































































































