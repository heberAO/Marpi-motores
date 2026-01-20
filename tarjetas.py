import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse
import re
import time

# --- FUNCIONES TÉCNICAS (SIN MODIFICAR) ---
def calcular_grasa_avanzado(codigo):
    try:
        s = str(codigo).split('.')[0]
        solo_numeros = re.sub(r'\D', '', s) 
        if len(solo_numeros) < 3: return 0.0
        serie_eje = int(solo_numeros[-2:])
        d = serie_eje * 5
        serie_tipo = int(solo_numeros[-3])
        if serie_tipo == 3:
            D = d * 2.2
            B = D * 0.25
        else:
            D = d * 1.8
            B = D * 0.22
        gramos = D * B * 0.005
        return round(gramos, 1)
    except:
        return 0.0

def generar_pdf_reporte(datos, tag_motor, tipo_trabajo="INFORME TÉCNICO"):
    try:
        datos_limpios = {str(k).replace(" ", "_").lower(): v for k, v in datos.items()}
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, f'{tipo_trabajo}', 0, 1, 'R')
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(95, 8, f"Fecha: {datos_limpios.get('fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos_limpios.get('responsable','-')}", 1, 1)
        
        if "LUBRICACION" in tipo_trabajo.upper():
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, " DETALLES DE LUBRICACIÓN:", 1, 1, 'L', True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(95, 8, f"Rod. LA: {datos_limpios.get('rodamiento_la','-')}", 1, 0)
            pdf.cell(95, 8, f"Gramos LA: {datos_limpios.get('gramos_la','0')} g", 1, 1)
            pdf.cell(95, 8, f"Rod. LOA: {datos_limpios.get('rodamiento_loa','-')}", 1, 0)
            pdf.cell(95, 8, f"Gramos LOA: {datos_limpios.get('gramos_loa','0')} g", 1, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DESCRIPCIÓN:", 0, 1)
        desc = datos_limpios.get('descripcion') or datos_limpios.get('intervencion') or '-'
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(desc), border=1)
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except:
        return None

# --- CONFIGURACIÓN Y ESTADOS ---
st.set_page_config(page_title="Marpi Motores", layout="wide")

if "form_id_lub" not in st.session_state: st.session_state.form_id_lub = 0
if "pdf_listo" not in st.session_state: st.session_state.pdf_listo = None
if "autorizado" not in st.session_state: st.session_state.autorizado = False
if "seleccion_manual" not in st.session_state: st.session_state.seleccion_manual = "Nuevo Registro"

def limpiar_lubricacion():
    st.session_state.form_id_lub += 1
    st.session_state.pdf_listo = None

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(ttl=0)

# --- NAVEGACIÓN ---
query_params = st.query_params
qr_tag = query_params.get("tag", "")

opciones_menu = ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"]
with st.sidebar:
    st.title("⚡ MARPI MOTORES")
    modo = st.radio("SELECCIONE:", opciones_menu, index=opciones_menu.index(st.session_state.seleccion_manual))
    st.session_state.seleccion_manual = modo

# --- PROTECCIÓN ---
if modo in ["Nuevo Registro", "Relubricacion", "Mediciones de Campo"] and not st.session_state.autorizado:
    st.title("🔒 Acceso Restringido")
    with st.form("login"):
        clave = st.text_input("Contraseña:", type="password")
        if st.form_submit_button("Entrar") and clave == "MARPI2026":
            st.session_state.autorizado = True
            st.rerun()
    st.stop()

# --- SECCIONES ---
if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    with st.form("alta"):
        t = st.text_input("TAG/ID MOTOR").upper()
        sn = st.text_input("N° de Serie")
        resp = st.text_input("Técnico Responsable")
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, "Responsable": resp}
            df_actualizado = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_actualizado)
            st.success("✅ Guardado")

elif modo == "Historial y QR":
    st.title("🔍 Consulta de Motores")
    tags = [""] + sorted(df_completo['Tag'].unique().tolist())
    sel = st.selectbox("Seleccione Motor", tags)
    if sel:
        url_app = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?tag={sel}"
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
        st.image(qr_api)
        st.write(df_completo[df_completo['Tag'] == sel])

elif modo == "Relubricacion":
    st.title("🛢️ Registro de Relubricación")
    
    df_lista = df_completo.fillna("-")
    lista_tags = [""] + sorted(df_lista['Tag'].unique().tolist())
    
    opcion_elegida = st.selectbox("Seleccione Motor", lista_tags, key=f"busc_lub_{st.session_state.form_id_lub}")
    
    motor = None
    c_la, c_loa = 0.0, 0.0
    if opcion_elegida != "":
        motor = df_lista[df_lista['Tag'] == opcion_elegida].iloc[-1]
        c_la = calcular_grasa_avanzado(motor['Rodamiento LA'])
        c_loa = calcular_grasa_avanzado(motor['Rodamiento LOA'])

    with st.form(key=f"form_lub_{st.session_state.form_id_lub}"):
        col1, col2 = st.columns(2)
        resp_r = col1.text_input("Responsable")
        rod_la = col1.text_input("Rod. LA", value=str(motor['Rodamiento LA']) if motor is not None else "")
        gr_la = col1.number_input("Gramos LA", value=float(c_la))
        
        tipo = col2.radio("Tipo", ["Preventiva", "Correctiva"])
        rod_loa = col2.text_input("Rod. LOA", value=str(motor['Rodamiento LOA']) if motor is not None else "")
        gr_loa = col2.number_input("Gramos LOA", value=float(c_loa))
        
        obs = st.text_area("Notas")
        if st.form_submit_button("💾 GUARDAR"):
            if not resp_r or not opcion_elegida:
                st.error("Faltan datos")
            else:
                try:
                    reg = {
                        "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": opcion_elegida,
                        "Responsable": resp_r, "Rodamiento LA": rod_la, "Gramos LA": gr_la,
                        "Rodamiento LOA": rod_loa, "Gramos LOA": gr_loa, "Descripcion": tipo, "Observaciones": obs
                    }
                    df_h = conn.read(worksheet="Sheet1", ttl=0)
                    conn.update(worksheet="Sheet1", data=pd.concat([df_h, pd.DataFrame([reg])], ignore_index=True))
                    st.session_state.pdf_listo = generar_pdf_reporte(reg, opcion_elegida, "REPORTE DE LUBRICACIÓN")
                    st.success("✅ Guardado")
                except Exception as e: st.error(e)

    if st.session_state.pdf_listo:
        st.download_button("📥 Descargar PDF", st.session_state.pdf_listo, f"Lub_{opcion_elegida}.pdf", "application/pdf", on_click=limpiar_lubricacion)

elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones")
    with st.form("megado"):
        t = st.text_input("TAG")
        resp = st.text_input("Responsable")
        if st.form_submit_button("💾 GUARDAR"):
            st.success("✅ Guardado")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")


























































































































































































































































































































































































































