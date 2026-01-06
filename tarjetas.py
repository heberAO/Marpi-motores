import streamlit as st
import qrcode
from io import BytesIO
from datetime import date
from fpdf import FPDF
import os

# Configuramos la página
st.set_page_config(page_title="Marpi Electricidad", page_icon="⚡")

# --- FUNCIONES ---

def crear_pdf(fecha, responsable, tag, descripcion, qr_buf):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. LOGO EN EL PDF (Asegúrate de que se llame logo.png)
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=10, y=8, w=33)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(200, 15, "MARPI ELECTRICIDAD", ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(100)
    pdf.cell(200, 10, "REGISTRO DE REPARACIÓN DE MOTORES", ln=True, align='C')
    pdf.ln(15)
    
    # Tabla de datos
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0)
    
    datos = [
        ("Fecha:", str(fecha)),
        ("Responsable:", responsable),
        ("Tag del Motor:", tag)
    ]
    
    for label, valor in datos:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(50, 10, label, 1)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f" {valor}", 1, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Descripción de la Reparación:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, descripcion, border=1)
    
    # QR al final del PDF
    pdf.ln(10)
    with open("temp_qr.png", "wb") as f:
        f.write(qr_buf.getbuffer())
    pdf.image("temp_qr.png", x=75, y=pdf.get_y(), w=50)
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ VISUAL ---

# Mostrar Logo en la Web
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("MARPI ELECTRICIDAD")
st.subheader("Registro de Reparación")

with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha", date.today())
        tag = st.text_input("Tag del motor")
    with col2:
        responsable = st.text_input("Responsable")
    
    descripcion = st.text_area("Descripción de la reparación")
    enviar = st.form_submit_button("Generar Informe y QR")

if enviar:
    if responsable and tag:
        # Aquí crearíamos el link si la app estuviera en la nube
        # Por ahora, el QR contiene los datos clave
        contenido_qr = f"MARPI ELECTRICIDAD\nTAG: {tag}\nFECHA: {fecha}\nRESP: {responsable}"
        
        qr = qrcode.make(contenido_qr)
        buf_qr = BytesIO()
        qr.save(buf_qr, format="PNG")
        
        pdf_final = crear_pdf(fecha, responsable, tag, descripcion, buf_qr)
        
        st.divider()
        st.success("✅ Informe generado exitosamente")
        
        c1, c2 = st.columns(2)
        with c1:
            st.image(buf_qr.getvalue(), width=200, caption="Código QR para el motor")
        with c2:
            st.write("### Descargas")
            st.download_button("📥 Descargar Informe PDF", pdf_final, f"Informe_{tag}.pdf")
    else:
        st.error("Faltan datos obligatorios.")