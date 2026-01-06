import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

st.set_page_config(page_title="Marpi Motores", page_icon="⚡")

# --- LOGO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SISTEMA MARPI ELECTRICIDAD")

# --- FUNCIÓN PARA GUARDAR ---
def guardar_datos(fecha, responsable, tag, descripcion):
    try:
        # Conexión estándar (toma los datos solo de Secrets)
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        df_existente = conn.read(ttl=0)
        
        nuevo_dato = pd.DataFrame([{
            "Fecha": str(fecha),
            "Responsable": responsable,
            "Tag": tag,
            "Descripcion": descripcion
        }])
        
        df_final = pd.concat([df_existente, nuevo_dato], ignore_index=True)
        conn.update(data=df_final)
        return True
    except Exception as e:
        st.error(f"❌ Error al conectar: {e}")
        return False

# --- FORMULARIO ---
fecha = st.date_input("Fecha", date.today())
tag = st.text_input("Tag del Motor")
responsable = st.text_input("Responsable")
descripcion = st.text_area("Descripción")

if st.button("GUARDAR REGISTRO Y GENERAR PDF"):
    if not tag or not responsable:
        st.warning("⚠️ Completa Tag y Responsable")
    else:
        if guardar_datos(fecha, responsable, tag, descripcion):
            st.success("✅ REGISTRO GUARDADO EN EXCEL")
            
            # Generar QR y PDF
            info_qr = f"TAG: {tag}\nRESP: {responsable}\nFECHA: {fecha}"
            img_qr = qrcode.make(info_qr)
            buf_qr = BytesIO()
            img_qr.save(buf_qr, format="PNG")
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "INFORME MARPI", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Fecha: {fecha}", ln=True)
            pdf.cell(0, 10, f"Tag: {tag}", ln=True)
            pdf.cell(0, 10, f"Responsable: {responsable}", ln=True)
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            st.download_button("📥 DESCARGAR PDF", pdf_bytes, f"Informe_{tag}.pdf")
            st.image(buf_qr.getvalue(), width=150)





