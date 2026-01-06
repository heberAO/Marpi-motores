import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

# Configuración básica
st.set_page_config(page_title="Marpi Motores", page_icon="⚡")

# --- INTERFAZ ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SISTEMA MARPI ELECTRICIDAD")

# Campos fuera del formulario para evitar que se pierdan mensajes
fecha = st.date_input("Fecha", date.today())
tag = st.text_input("Tag del Motor")
responsable = st.text_input("Responsable")
descripcion = st.text_area("Descripción")

if st.button("GUARDAR REGISTRO Y GENERAR PDF"):
    if not tag or not responsable:
        st.warning("⚠️ Por favor completa el Tag y el Responsable.")
    else:
        # 1. INTENTO DE GUARDADO EN GOOGLE
        try:
            with st.spinner("Guardando en Google Sheets..."):
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
                st.success("✅ REGISTRO GUARDADO EN EXCEL")
        except Exception as e:
            st.error(f"❌ ERROR AL GUARDAR EN EXCEL: {e}")

        # 2. GENERACIÓN DE QR Y PDF (Siempre se genera, aunque falle el Excel)
        try:
            # QR
            info_qr = f"TAG: {tag}\nRESP: {responsable}\nFECHA: {fecha}"
            img_qr = qrcode.make(info_qr)
            buf_qr = BytesIO()
            img_qr.save(buf_qr, format="PNG")
            
            # PDF (Simplificado para que no falle)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "INFORME DE REPARACION - MARPI", ln=True, align='C')
            pdf.set_font("Arial", '', 12)
            pdf.ln(10)
            pdf.cell(0, 10, f"Fecha: {fecha}", ln=True)
            pdf.cell(0, 10, f"Tag: {tag}", ln=True)
            pdf.cell(0, 10, f"Responsable: {responsable}", ln=True)
            pdf.multi_cell(0, 10, f"Descripcion: {descripcion}")
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            
            st.download_button("📥 DESCARGAR PDF", pdf_bytes, f"Informe_{tag}.pdf")
            st.image(buf_qr.getvalue(), width=150, caption="Código QR para el motor")
            
        except Exception as e_pdf:
            st.error(f"Error al crear PDF: {e_pdf}")
