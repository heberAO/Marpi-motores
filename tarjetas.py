import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse

# --- CONFIGURACIÓN Y CREDENCIALES ---
st.set_page_config(page_title="MARPI Motores", layout="wide")
PASSWORD_MARPI = "MARPI2026"

# --- 1. CONEXIÓN A BASE DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(ttl=0)

# --- 2. FUNCIÓN PDF (TU LÓGICA ORIGINAL) ---
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
        pdf.cell(0, 8, " DETALLE TÉCNICO Y VALORES:", 1, 1, 'L', True)
        
        pdf.set_font("Arial", '', 9)
        if "|" in desc_full:
            for p in desc_full.split(" | "):
                pdf.cell(0, 6, f" > {p.strip()}", border='LR', ln=1)
            pdf.cell(0, 0, "", border='T', ln=1)
        else:
            pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)

        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, " OBSERVACIONES FINALIZADAS:", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, f"\n{datos.get('Taller_Externo','-')}\n", border=1)
        
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except:
        return None

# --- 3. BARRA LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    st.title("⚙️ Menú MARPI")
    modo = st.radio("Seleccione:", ["Historial y QR", "Nuevo Registro", "Relubricacion", "Mediciones de Campo"])

# --- 4. SEGURIDAD ---
if modo in ["Nuevo Registro", "Relubricacion", "Mediciones de Campo"]:
    if not st.session_state.get("autorizado", False):
        st.title("🔒 Acceso Restringido")
        clave = st.text_input("Contraseña de Personal:", type="password")
        if st.button("Ingresar"):
            if clave == PASSWORD_MARPI:
                st.session_state.autorizado = True
                st.rerun()
            else: st.error("Clave Incorrecta")
        st.stop()

# --- 5. SECCIONES (TUS CAMPOS ORIGINALES REINSTALADOS) ---
if modo == "Historial y QR":
    st.title("🔍 Consulta y Gestión de Motores")
    qr_tag = st.query_params.get("tag", "").upper()
    if not df_completo.empty:
        df_completo['N_Serie'] = df_completo['N_Serie'].fillna("-")
        opciones = [""] + sorted(df_completo['Tag'].unique().tolist())
        idx_q = opciones.index(qr_tag) if qr_tag in opciones else 0
        seleccion = st.selectbox("Busca por TAG:", opciones, index=idx_q)
        
        if seleccion:
            st.session_state.tag_fijo = seleccion
            col_qr, col_info = st.columns([1, 2])
            url_app = f"https://marpi-motores.streamlit.app/?tag={seleccion}"
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
            with col_qr: st.image(qr_api)
            with col_info: st.subheader(f"Equipo: {seleccion}")
            
            st.divider()
            hist_m = df_completo[df_completo['Tag'] == seleccion].iloc[::-1]
            for idx, fila in hist_m.iterrows():
                with st.expander(f"📅 {fila['Fecha']} - {str(fila['Descripcion'])[:40]}..."):
                    st.write(f"**Responsable:** {fila['Responsable']}")
                    st.write(f"**Detalle:** {fila['Descripcion']}")
                    pdf_archivo = generar_pdf_reporte(fila.to_dict(), seleccion)
                    if pdf_archivo:
                        st.download_button("📄 Descargar PDF", data=pdf_archivo, file_name=f"Reporte_{seleccion}.pdf", key=f"btn_{idx}")

elif modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    with st.form("alta"):
        col1, col2, col3, col4, col5 = st.columns(5)
        t = col1.text_input("TAG/ID MOTOR", value=st.session_state.get('tag_fijo','')).upper()
        p = col2.text_input("Potencia")
        r = col3.selectbox("RPM", ["-", "750", "1500", "3000"])
        f = col4.text_input("Carcasa")
        sn = col5.text_input("N° de Serie")
        st.subheader("🔍 Mediciones Iniciales / Reparación")
        m1, m2, m3 = st.columns(3)
        with m1: rt_tu, rt_tv, rt_tw = st.text_input("T-U"), st.text_input("T-V"), st.text_input("T-W")
        with m2: rb_uv, rb_vw, rb_uw = st.text_input("U-V"), st.text_input("V-W"), st.text_input("U-W")
        with m3: ri_u, ri_v, ri_w = st.text_input("U1-U2"), st.text_input("V1-V2"), st.text_input("W1-W2")
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción de la Reparación/Trabajo")
        obs = st.text_area("Observaciones Finales")
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, "Responsable": resp, "Descripcion": desc, "Taller_Externo": obs}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            st.success("✅ Guardado")

elif modo == "Relubricacion":
    st.title("🛢️ Gestión de Relubricación")
    with st.form("relub"):
        t_r = st.text_input("TAG DEL MOTOR", value=st.session_state.get('tag_fijo','')).upper()
        resp_r = st.text_input("Responsable")
        c1, c2 = st.columns(2)
        rod_la = c1.text_input("Rodamiento LA")
        gr_la = c1.text_input("Gramos LA")
        rod_loa = c2.text_input("Rodamiento LOA
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")





































































































































































































































































































































