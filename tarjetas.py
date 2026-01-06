import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

# Configuración de página
st.set_page_config(page_title="Marpi Motores", page_icon="⚡")

# --- MOSTRAR LOGO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SISTEMA MARPI ELECTRICIDAD")
st.markdown("---")

# --- CAMPOS DE ENTRADA ---
col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("Fecha de Reparación", date.today())
    responsable = st.text_input("Responsable del Trabajo")
with col2:
    tag = st.text_input("Tag / Número de Motor")

descripcion = st.text_area("Descripción de la Reparación / Repuestos")

# --- BOTÓN PRINCIPAL ---
if st.button("GUARDAR REGISTRO Y GENERAR PDF"):
    if not tag or not responsable:
        st.error("⚠️ El Tag y el Responsable son obligatorios.")
    else:
        # 1. GUARDAR EN GOOGLE SHEETS
        try:
            with st.spinner("Guardando en base de datos..."):
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_existente = conn.read(ttl=0)
                
                nuevo_registro = pd.DataFrame([{
                    "Fecha": str(fecha),
                    "Responsable": responsable,
                    "Tag": tag,
                    "Descripcion": descripcion
                }])
                
                df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                conn.update(data=df_final)
                st.success("✅ Datos guardados en Google Sheets")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

        # 2. GENERAR QR
       qr_data = (
            f"⚡ MARPI ELECTRICIDAD ⚡\n"
            f"--------------------------\n"
            f"FECHA: {fecha}\n"
            f"MOTOR (TAG): {tag}\n"
            f"RESPONSABLE: {responsable}\n"
            f"REPARACIÓN: {descripcion}"
        )
        
        img_qr = qrcode.make(qr_data)
        buf_qr = BytesIO()
        img_qr.save(buf_qr, format="PNG")
        # 3. GENERAR PDF
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Logo en el PDF
            if os.path.exists("logo.png"):
                pdf.image("logo.png", x=10, y=8, w=30)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "INFORME TÉCNICO DE REPARACIÓN", ln=True, align='C')
            pdf.ln(15)
            
            # Datos en tabla
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(40, 10, "Fecha:", 1)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f" {fecha}", 1, ln=True)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(40, 10, "Motor (Tag):", 1)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f" {tag}", 1, ln=True)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(40, 10, "Responsable:", 1)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f" {responsable}", 1, ln=True)
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Detalles de la reparación:", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 8, descripcion, border=1)
            
            # Insertar QR
            pdf.ln(10)
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 10, "Código QR de trazabilidad:", ln=False, align='C')
            pdf.ln(10)
            # Guardar QR temporal para el PDF
            with open("temp_qr.png", "wb") as f_temp:
                f_temp.write(buf_qr.getvalue())
            pdf.image("temp_qr.png", x=85, y=pdf.get_y(), w=40)
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            
            # Botón de descarga
            st.download_button(
                label="📥 DESCARGAR INFORME PDF",
                data=pdf_output,
                file_name=f"Reparacion_{tag}.pdf",
                mime="application/pdf"
            )
            
            st.image(buf_qr.getvalue(), width=150, caption="QR generado para el motor")

        except Exception as e_pdf:
            st.error(f"Error al generar PDF: {e_pdf}")

