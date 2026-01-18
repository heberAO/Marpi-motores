import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse

# --- CONFIGURACIÓN Y CREDENCIALES ---
PASSWORD_MARPI = "MARPI2026"

# --- 1. CONEXIÓN A BASE DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(ttl=0)

# --- 2. LÓGICA DE URL (QR) ---
query_params = st.query_params
qr_tag = query_params.get("tag", "").upper()

# --- 3. FUNCIÓN PDF PROFESIONAL ---
def generar_pdf_reporte(datos, tag_motor):
    try:
        desc_full = str(datos.get('Descripcion', '')).upper()
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        if "|" in desc_full or "RESISTENCIAS" in desc_full:
            color_rgb, tipo_label = (204, 102, 0), "PROTOCOLO DE MEDICIONES ELÉCTRICAS"
        elif "LUBRICACIÓN" in desc_full or "LUBRICACION" in desc_full:
            color_rgb, tipo_label = (0, 102, 204), "REPORTE DE LUBRICACIÓN"
        else:
            color_rgb, tipo_label = (60, 60, 60), "REPORTE TÉCNICO DE REPARACIÓN"

        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 35)
        
        pdf.set_text_color(*color_rgb)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, tipo_label, 0, 1, 'R')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(12)
        
        pdf.set_fill_color(*color_rgb)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 7, " FECHA:", 1, 0); pdf.set_font("Arial", '', 9)
        pdf.cell(55, 7, f" {datos.get('Fecha','-')}", 1, 0)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 7, " RESPONSABLE:", 1, 0); pdf.set_font("Arial", '', 9)
        pdf.cell(55, 7, f" {datos.get('Responsable','-')}", 1, 1)
        
        pdf.ln(5)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " DETALLE TÉCNICO Y VALORES REGISTRADOS:", 1, 1, 'L', True)
        pdf.ln(2)
        
        if "|" in desc_full:
            partes = desc_full.split(" | ")
            pdf.set_font("Arial", '', 9) 
            for p in partes:
                pdf.cell(0, 6, f" > {p.strip()}", border='LR', ln=1)
            pdf.cell(0, 0, "", border='T', ln=1)
        else:
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)

        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, " OBSERVACIONES FINALIZADAS:", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, f"\n{datos.get('Taller_Externo','-')}\n", border=1)
        
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception: return None

# --- 4. BARRA LATERAL (MENÚ) ---
with st.sidebar:
    st.image("logo.png", width=150) if os.path.exists("logo.png") else None
    st.title("⚙️ Menú MARPI")
    
    # Manejo de navegación desde botones
    if "menu_option" not in st.session_state:
        st.session_state.menu_option = "Historial y QR"

    modo = st.sidebar.radio("Seleccione:", 
                            ["Historial y QR", "Nuevo Registro", "Relubricacion", "Mediciones de Campo"],
                            key="navegacion_radio")

# --- 5. LÓGICA DE PROTECCIÓN ---
if modo in ["Nuevo Registro", "Relubricacion", "Mediciones de Campo"]:
    if not st.session_state.get("autorizado", False):
        st.title("🔒 Acceso Restringido")
        st.info("Para cargar datos, ingrese la clave de personal de MARPI MOTORES.")
        clave = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            if clave == PASSWORD_MARPI:
                st.session_state.autorizado = True
                st.rerun()
            else: st.error("Clave Incorrecta")
        st.stop()

# --- 6. SECCIONES ---

if modo == "Historial y QR":
    st.title("🔍 Historial y Gestión de Motores")
    if not df_completo.empty:
        # Buscador combinado
        df_completo['Busqueda_Combo'] = df_completo['Tag'].astype(str) + " | SN: " + df_completo['N_Serie'].
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")


































































































































































































































































































































