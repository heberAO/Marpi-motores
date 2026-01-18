import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse

# --- 1. CONFIGURACIÓN Y CREDENCIALES ---
st.set_page_config(page_title="MARPI Motores", layout="wide")
PASSWORD_MARPI = "MARPI2026"

# --- 2. CONEXIÓN A BASE DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
df_completo = conn.read(ttl=0)

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
        pdf.ln(10)
        
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
        pdf.cell(0, 8, " DETALLE TÉCNICO REGISTRADO:", 1, 1, 'L', True)
        
        pdf.set_font("Arial", '', 9)
        if "|" in desc_full:
            for p in desc_full.split(" | "):
                pdf.cell(0, 6, f" > {p.strip()}", border='LR', ln=1)
            pdf.cell(0, 0, "", border='T', ln=1)
        else:
            pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)
        
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except:
        return None

# --- 4. BARRA LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    st.title("⚙️ Menú MARPI")
    modo = st.radio("Seleccione:", ["Historial y QR", "Nuevo Registro", "Relubricacion", "Mediciones de Campo"])

# --- 5. LÓGICA DE ACCESO ---
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

# --- 6. SECCIONES ---
if modo == "Historial y QR":
    st.title("🔍 Consulta de Motores")
    qr_tag = st.query_params.get("tag", "").upper()
    if not df_completo.empty:
        # CORRECCIÓN AQUÍ: Convertimos a string para que sorted no falle
        tags_raw = [str(x) for x in df_completo['Tag'].dropna().unique()]
        opciones = [""] + sorted(tags_raw)
        
        idx = opciones.index(qr_tag) if qr_tag in opciones else 0
        seleccion = st.selectbox("Busca por TAG:", opciones, index=idx)
        if seleccion:
            st.session_state.tag_fijo = seleccion
            hist = df_completo[df_completo['Tag'].astype(str) == seleccion].iloc[::-1]
            for i, fila in hist.iterrows():
                with st.expander(f"📅 {fila['Fecha']} - {str(fila['Descripcion'])[:40]}..."):
                    st.write(fila['Descripcion'])
                    pdf = generar_pdf_reporte(fila.to_dict(), seleccion)
                    if pdf: st.download_button("📄 PDF", pdf, f"{seleccion}_{i}.pdf", key=f"btn_{i}")

elif modo == "Nuevo Registro":
    st.title("📝 Registro Inicial de Motor")
    with st.form("alta"):
        c1, c2, c3, c4, c5 = st.columns(5)
        t = c1.text_input("TAG MOTOR", value=st.session_state.get('tag_fijo','')).upper()
        p = c2.text_input("Potencia")
        r = c3.selectbox("RPM", ["-", "750", "1500", "3000"])
        f = c4.text_input("Carcasa")
        sn = c5.text_input("N° Serie")
        st.subheader("🔍 Mediciones de Resistencia")
        m1, m2, m3 = st.columns(3)
        rt_tu, rt_tv, rt_tw = m1.text_input("T-U"), m1.text_input("T-V"), m1.text_input("T-W")
        rb_uv, rb_vw, rb_uw = m2.text_input("U-V"), m2.text_input("V-W"), m2.text_input("U-W")
        ri_u, ri_v, ri_w = m3.text_input("U1-U2"), m3.text_input("V1-V2"), m3.text_input("W1-W2")
        resp = st.text_input("Técnico")
        desc = st.text_area("Descripción")
        if st.form_submit_button("💾 GUARDAR"):
            detalle = f"MOT: {p}HP, {r}RPM. RES: TU:{rt_tu}, TV:{rt_tv}, TW:{rt_tw} | UV:{rb_uv}, VW:{rb_vw}, UW:{rb_uw} | U12:{ri_u}, V12:{ri_v}, W12:{ri_w} | {desc}"
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, "Responsable": resp, "Descripcion": detalle}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            st.success("Guardado")

elif modo == "Relubricacion":
    st.title("🛢️ Registro de Lubricación")
    with st.form("relub"):
        t = st.text_input("TAG", value=st.session_state.get('tag_fijo','')).upper()
        c1, c2 = st.columns(2)
        la, gla = c1.text_input("Rod. LA"), c1.text_input("Gramos LA")
        loa, gloa = c2.text_input("Rod. LOA"), c2.text_input("Gramos LOA")
        resp = st.text_input("Técnico")
        if st.form_submit_button("💾 GUARDAR"):
            detalle = f"LUBRICACIÓN: LA:{la} ({gla}g), LOA:{loa} ({gloa}g)"
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Responsable": resp, "Descripcion": detalle}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            st.success("Guardado")

elif modo == "Mediciones de Campo":
    st.title("⚡ Protocolo de 15 Mediciones")
    with st.form("megado"):
        t = st.text_input("TAG MOTOR", value=st.session_state.get('tag_fijo', '')).upper()
        resp = st.text_input("Técnico")
        st.subheader("1. Megado a Tierra (Ω)")
        c1, c2, c3 = st.columns(3); tv1, tu1, tw1 = c1.text_input("T-V1"), c2.text_input("T-U1"), c3.text_input("T-W1")
        st.subheader("2. Megado entre Bobinas (Ω)")
        c4, c5, c6 = st.columns(3); wv1, wu1, vu1 = c4.text_input("W1-V1"), c5.text_input("W1-U1"), c6.text_input("V1-U1")
        st.subheader("3. Resistencias Internas (Ω)")
        c7, c8, c9 = st.columns(3); u12, v12, w12 = c7.text_input("U1-U2"), c8
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")







































































































































































































































































































































