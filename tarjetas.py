import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF

# 1. FUNCIÓN PARA GENERAR EL PDF ORGANIZADO POR ÁREAS
def generar_pdf(df_historial, tag_motor):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado y Logo
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 8, 33)
    
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(0, 51, 102) # Azul oscuro
    pdf.cell(0, 10, 'INFORME TÉCNICO DE MANTENIMIENTO', 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"ID MOTOR / TAG: {tag_motor}", 0, 1, 'C')
    pdf.ln(10)
    
    # Ordenamos: lo más nuevo primero
    df_ordenado = df_historial.sort_index(ascending=False)
    
    for _, row in df_ordenado.iterrows():
        # --- SECCIÓN: INFORMACIÓN GENERAL ---
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, f"REGISTRO DE FECHA: {row.get('Fecha', '')} | RESPONSABLE: {row.get('Responsable', '')}", 1, 1, 'L', True)
        
        # --- SECCIÓN: ESTADO DEL MOTOR (Resaltado) ---
        estado = str(row.get('Estado', 'OPERATIVO'))
        if estado == "OPERATIVO": pdf.set_text_color(0, 128, 0) # Verde
        elif estado == "EN OBSERVACIÓN": pdf.set_text_color(255, 128, 0) # Naranja
        else: pdf.set_text_color(255, 0, 0) # Rojo
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"ESTADO FINAL: {estado}", 1, 1, 'C')
        pdf.set_text_color(0, 0, 0)
        
        # --- SECCIÓN: MEDICIONES ELÉCTRICAS (En cuadros) ---
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(63, 7, "Res. Tierra", 1, 0, 'C')
        pdf.cell(63, 7, "Res. Bobinas", 1, 0, 'C')
        pdf.cell(64, 7, "Res. Interna", 1, 1, 'C')
        
        pdf.set_font("Arial", '', 9)
        pdf.cell(63, 7, f"{row.get('Res_Tierra', '-')} M Ohms", 1, 0, 'C')
        pdf.cell(63, 7, f"{row.get('Res_Bobinas', '-')} Ohms", 1, 0, 'C')
        pdf.cell(64, 7, f"{row.get('Res_Interna', '-')} Ohms", 1, 1, 'C')
        
        # --- SECCIÓN: ACCIONES REALIZADAS (Descripción multilínea) ---
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 7, "DESCRIPCIÓN DE REPARACIONES Y ACCIONES:", "LR", 1, 'L')
        pdf.set_font("Arial", '', 9)
        desc = str(row.get('Descripcion', 'Sin descripción detallada.'))
        pdf.multi_cell(0, 7, desc, "LRB", 'L')
        
        pdf.ln(10) # Espacio entre registros

    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, f"Documento oficial de Marpi Electricidad - Generado el {date.today().strftime('%d/%m/%Y')}", 0, 0, 'C')
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# 2. CONFIGURACIÓN STREAMLIT
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

query_tag = st.query_params.get("tag", "")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    df_completo = pd.DataFrame()

with st.sidebar:
    st.header("⚙️ Menú Marpi")
    modo = st.radio("Seleccione:", ["📝 Registro", "🔍 Historial / QR"], index=1 if query_tag else 0)

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro":
    st.title("📝 Registro de Reparación")
    tag = st.text_input("Tag / ID Motor", value=query_tag).strip().upper()
    
    with st.form("form_reparacion"):
        c1, c2 = st.columns(2)
        with c1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("Fecha", date.today())
            estado_motor = st.selectbox("Estado Final del Motor", ["OPERATIVO", "REEMPLAZO"])
            descripcion = st.text_area("Descripción de la Reparación (Acciones Realizadas)")
            externo = st.text_area("Reparacion Taller Externo")
        with c2:
            st.markdown("**Datos de Placa y Mediciones**")
            pot = st.text_input("Potencia")
            ten = st.text_input("Tensión")
            rt = st.text_input("Res. Tierra (MΩ)")
            rb = st.text_input("Res. Bobinas (Ω)")
            ri = st.text_input("Res. Interna (Ω)")
            
        enviar = st.form_submit_button("💾 GUARDAR")

    if enviar and tag and responsable:
        nuevo = pd.DataFrame([{
            "Fecha": fecha.strftime("%d/%m/%Y"), 
            "Responsable": responsable, 
            "Tag": tag, 
            "Estado": estado_motor, # <--- Nueva columna
            "Potencia": pot, 
            "Res_Tierra": rt, 
            "Res_Bobinas": rb, 
            "Res_Interna": ri, 
            "Descripcion": descripcion
            "Taller_Externo": taller_externo
        }])
        df_final = pd.concat([df_completo, nuevo], ignore_index=True)
        conn.update(data=df_final)
        st.success("✅ Registro Guardado.")
        st.rerun()

# --- MODO 2: HISTORIAL ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida")
    id_ver = st.text_input("ID Motor:", value=query_tag).strip().upper()
    
    if id_ver and not df_completo.empty:
        res = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        if not res.empty:
            st.subheader(f"Historial de {id_ver}")
            st.dataframe(res.sort_index(ascending=False), use_container_width=True)
            
            pdf_bytes = generar_pdf(res, id_ver)
            st.download_button(label="📥 Descargar Informe PDF Profesional", data=pdf_bytes, file_name=f"Informe_{id_ver}.pdf", mime="application/pdf")
            
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
































































































































