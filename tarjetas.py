import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF # <--- Nueva librería para PDF

# 1. FUNCIÓN PARA GENERAR EL PDF
def generar_pdf(df_historial, tag_motor):
    pdf = FPDF()
    pdf.add_page()
    
    # Logo si existe
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 8, 30)
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'INFORME TÉCNICO DE MANTENIMIENTO', 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Motor Tag: {tag_motor}", 0, 1, 'C')
    pdf.ln(10)
    
    # Tabla de datos
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(25, 10, "Fecha", 1, 0, 'C', True)
    pdf.cell(35, 10, "Técnico", 1, 0, 'C', True)
    pdf.cell(20, 10, "Pot.", 1, 0, 'C', True)
    pdf.cell(110, 10, "Descripción del Trabajo", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 9)
    for _, row in df_historial.iterrows():
        # Limpiamos los datos para evitar errores de caracteres
        fecha = str(row.get('Fecha', ''))
        tec = str(row.get('Responsable', ''))[:15]
        pot = str(row.get('Potencia', ''))
        desc = str(row.get('Descripcion', '')).replace('\n', ' ')[:70]
        
        pdf.cell(25, 10, fecha, 1)
        pdf.cell(35, 10, tec, 1)
        pdf.cell(20, 10, pot, 1)
        pdf.cell(110, 10, desc, 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# 2. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

if 'guardado' not in st.session_state:
    st.session_state.guardado = False

query_tag = st.query_params.get("tag", "")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    df_completo = pd.DataFrame()

with st.sidebar:
    st.header("⚙️ Menú Marpi")
    default_index = 1 if query_tag else 0
    modo = st.radio("Seleccione:", ["📝 Registro", "🔍 Historial / QR"], index=default_index)

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro":
    st.title("📝 Registro de Reparación")
    tag = st.text_input("Tag / ID Motor", value=query_tag).strip().upper()
    
    datos_previa = {"Pot": "", "Ten": "", "RPM": ""}
    if tag and not df_completo.empty:
        historia = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
        if not historia.empty:
            ultimo = historia.iloc[-1]
            datos_previa = {"Pot": str(ultimo.get('Potencia', '')), "Ten": str(ultimo.get('Tension', '')), "RPM": str(ultimo.get('RPM', ''))}

    with st.form("form_reparacion"):
        c1, c2 = st.columns(2)
        with c1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("Fecha", date.today())
            descripcion = st.text_area("Detalles del trabajo")
        with c2:
            pot = st.text_input("Potencia", value=datos_previa["Pot"])
            ten = st.text_input("Tensión", value=datos_previa["Ten"])
            rpm = st.text_input("RPM", value=datos_previa["RPM"])
            rt = st.text_input("Res. Tierra (Ω)")
            rb = st.text_input("Res. E.Bobina (Ω)")
            ri = st.text_input("Res. Interna (Ω)")
        enviar = st.form_submit_button("💾 GUARDAR")

    if enviar and tag and responsable:
        nuevo = pd.DataFrame([{"Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag, "Potencia": pot, "Tension": ten, "RPM": rpm, "Res_Tierra": rt, "Res_Bobinas": rb, "Res_Interna": ri, "Descripcion": descripcion}])
        df_final = pd.concat([df_completo, nuevo], ignore_index=True)
        conn.update(data=df_final)
        st.success("✅ Guardado.")
        st.rerun()

    if tag:
        mi_url = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
        link = f"{mi_url}?tag={tag}"
        qr_gen = qrcode.make(link)
        buf = BytesIO()
        qr_gen.save(buf, format="PNG")
        st.image(buf, width=150, caption=f"QR: {tag}")

# --- MODO 2: HISTORIAL ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida")
    id_ver = st.text_input("ID Motor:", value=query_tag).strip().upper()
    
    if id_ver and not df_completo.empty:
        res = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        if not res.empty:
            st.subheader(f"Historial de {id_ver}")
            st.dataframe(res.sort_index(ascending=False), use_container_width=True)
            
            # --- BOTÓN DE DESCARGA PDF ---
            try:
                pdf_bytes = generar_pdf(res, id_ver)
                st.download_button(
                    label="📥 Descargar Historial en PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_{id_ver}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")
        else:
            st.warning("Sin registros.")

st.markdown("---")
st.caption("Sistema diseñado y desarrollado por **Heber Ortiz** | Marpi Electricidad ⚡")


























































































































