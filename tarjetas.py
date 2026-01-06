import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Marpi Motores", page_icon="⚡")

# --- MOSTRAR LOGO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SISTEMA MARPI ELECTRICIDAD")
st.markdown("---")

# 2. CAMPOS DE ENTRADA
col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("Fecha de Reparación", date.today())
    responsable = st.text_input("Responsable del Trabajo")
with col2:
    tag = st.text_input("Tag / Número de Motor")

descripcion = st.text_area("Descripción de la Reparación / Repuestos")

# 3. FUNCIÓN PARA GUARDAR (Con limpieza de llave para evitar errores)
def guardar_datos(f, r, t, d):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = conn.read(ttl=0)
        
        nuevo_registro = pd.DataFrame([{
            "Fecha": str(f),
            "Responsable": r,
            "Tag": t,
            "Descripcion": d
        }])
        
        df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        conn.update(data=df_final)
        return True, "Ok"
    except Exception as e:
        return False, str(e)

# 4. BOTÓN PRINCIPAL
if st.button("GUARDAR REGISTRO Y GENERAR PDF"):
    if not tag or not responsable:
        st.error("⚠️ El Tag y el Responsable son obligatorios.")
    else:
        # --- PASO A: GUARDAR EN EXCEL ---
        exito, msj = guardar_datos(fecha, responsable, tag, descripcion)
        
        if exito:
            st.success("✅ Datos guardados en Google Sheets")

            # --- PASO B: GENERAR QR (CON DESCRIPCIÓN) ---
            qr_data = (
                f"⚡ MARPI ELECTRICIDAD ⚡\n"
                f"FECHA: {fecha}\n"
                f"TAG: {tag}\n"
                f"RESPONSABLE: {responsable}\n"
                f"REPARACION: {descripcion}"
            )
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            
            buf_qr = BytesIO()
            img_qr.save(buf_qr, format="PNG")

            # --- PASO C: GENERAR PDF ---
            try:
                pdf = FPDF()
                pdf.add_page()
                
                if os.path.exists("logo.png"):
                    pdf.image("logo.png", x=10, y=8, w=30)
                
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "INFORME TECNICO DE REPARACION", ln=True, align='C')
                pdf.ln(15)
                
                # Tabla de datos
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(40, 10, "Fecha:", 1)
                pdf.set_font("Arial", '', 12)
                pdf.cell(0, 10, f" {fecha}", 1, ln=True)
                
                pdf.cell(40, 10, "Motor (Tag):", 1)
                pdf.cell(0, 10, f" {tag}", 1, ln=True)
                
                pdf.cell(40, 10, "Responsable:", 1)
                pdf.cell(0, 10, f" {responsable}", 1, ln=True)
                
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "Detalles de la reparacion:", ln=True)
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 8, descripcion, border=1)
                
                # QR en el PDF
                with open("temp_qr.png", "wb") as f_temp:
                    f_temp.write(buf_qr.getvalue())
                
                pdf.ln(10)
                pdf.image("temp_qr.png", x=85, y=pdf.get_y(), w=40)
                
                pdf_output = pdf.output(dest='S').encode('latin-1')
                
                # Descarga y Visualización
                st.download_button(
                    label="📥 DESCARGAR INFORME PDF",
                    data=pdf_output,
                    file_name=f"Reparacion_{tag}.pdf",
                    mime="application/pdf"
                )
                
                st.image(buf_qr.getvalue(), width=200, caption="QR para el motor (Escanealo para probar)")
                
            except Exception as e_pdf:
                st.error(f"Error al crear PDF: {e_pdf}")
        else:
            st.error(f"❌ Error al guardar en Excel: {msj}")
            st.error(f"Error al generar PDF: {e_pdf}")


