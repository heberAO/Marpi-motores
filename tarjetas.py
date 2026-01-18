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
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")



































































































































































































































































































































