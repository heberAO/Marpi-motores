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

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.image("logo.png", width=150) if os.path.exists("logo.png") else None
    st.title("⚙️ Menú MARPI")
    modo = st.radio("Seleccione:", ["Historial y QR", "Nuevo Registro", "Relubricacion", "Mediciones de Campo"], index=0)

# --- 5. CANDADO DE SEGURIDAD ---
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
if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    with st.form("alta"):
        col1, col2, col3, col4, col5 = st.columns(5)
        t = col1.text_input("TAG/ID MOTOR").upper()
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
        ext = st.text_area("Observaciones Finales")
        
        if st.form_submit_button("💾 GUARDAR"):
            if t and resp:
                nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext}
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                st.success("✅ Registro guardado")
                st.rerun()

elif modo == "Historial y QR":
    st.title("🔍 Consulta y Gestión de Motores")
    if not df_completo.empty:
        df_completo['Busqueda_Combo'] = df_completo['Tag'].astype(str) + " | SN: " + df_completo['N_Serie'].astype(str)
        opciones = [""] + sorted(df_completo['Busqueda_Combo'].unique().tolist())
        
        idx_q = 0
        if qr_tag:
            for i, op in enumerate(opciones):
                if op.startswith(qr_tag + " |"):
                    idx_q = i
                    break
        
        seleccion = st.selectbox("Busca por TAG o N° de Serie:", opciones, index=idx_q)
        if seleccion:
            buscado = seleccion.split(" | ")[0].strip()
            st.session_state.tag_fijo = buscado
            
            col_qr, col_info = st.columns([1, 2])
            url_app = f"https://marpi-motores.streamlit.app/?tag={buscado}"
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
            
            with col_qr: st.image(qr_api, caption=f"QR de {buscado}")
            with col_info:
                st.subheader(f"🚜 Equipo: {buscado}")
                st.write(f"**URL:** {url_app}")

            st.divider()
            st.subheader("📜 Historial de Intervenciones")
            hist_m = df_completo[df_completo['Tag'] == buscado].iloc[::-1]
            for idx, fila in hist_m.iterrows():
                with st.expander(f"📅 {fila['Fecha']} - {str(fila['Descripcion'])[:40]}..."):
                    st.write(f"**Responsable:** {fila['Responsable']}")
                    st.write(f"**Detalle:** {fila['Descripcion']}")
                    pdf_archivo = generar_pdf_reporte(fila.to_dict(), buscado)
                    if pdf_archivo:
                        st.download_button("📄 Descargar PDF", data=pdf_archivo, file_name=f"Reporte_{buscado}.pdf", key=f"pdf_{idx}")

elif modo == "Relubricacion":
    st.title("🛢️ Gestión de Relubricación")
    with st.form("relub"):
        t_r = st.text_input("TAG DEL MOTOR", value=st.session_state.get('tag_fijo', '')).upper()
        resp_r = st.text_input("Responsable")
        rod_la = st.text_input("Rodamiento LA")
        gr_la = st.text_input("Gramos LA")
        rod_loa = st.text_input("Rodamiento LOA")
        gr_loa = st.text_input("Gramos LOA")
        grasa = st.selectbox("Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
        obs_r = st.text_area("Observaciones")
        
        if st.form_submit_button("💾 GUARDAR"):
            det_l = f"LUBRICACIÓN: LA:{rod_la}({gr_la}g), LOA:{rod_loa}({gr_loa}g). Grasa: {grasa}"
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_r, "Responsable": resp_r, "Descripcion": det_l, "Taller_Externo": obs_r}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            st.success("✅ Lubricación registrada")
            st.rerun()

elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo")
    if "cnt_meg" not in st.session_state: st.session_state.cnt_meg = 0
    
    with st.form(key=f"form_meg_{st.session_state.cnt_meg}"):
        c1, c2 = st.columns(2)
        t = c1.text_input("TAG MOTOR", value=st.session_state.get('tag_fijo', '')).upper()
        resp = c2.text_input("Técnico Responsable")
        sn = st.text_input("N° de Serie")
        
        st.subheader("📊 Megado a tierra")
        c1, c2, c3 = st.columns(3)
        tv1, tu1, tw1 = c1.text_input("T-V1 (Ω)"), c2.text_input("T-U1 (Ω)"), c3.text_input("T-W1 (Ω)")
        
        st.subheader("📊 Megado ente Bobinas")
        c4, c5, c6 = st.columns(3)
        wv1, wu1, vu1 = c4.text_input("W1-V1 (Ω)"), c5.text_input("W1-U1 (Ω)"), c6.text_input("V1-U1 (Ω)")

        st.subheader("📏 Resistencia internas")
        c7, c8, c9 = st.columns(3)
        u1u2, v1v2, w1w2 = c7.text_input("U1-U2 (Ω)"), c8.text_input("V1-V2 (Ω)"), c9.text_input("W1-W2 (Ω)")

        st.subheader("🔌 Megado de Línea")
        c10, c11, c12 = st.columns(3)
        tl1, tl2, tl3 = c10.text_input("T-L1 (MΩ)"), c11.text_input("T-L2 (MΩ)"), c12.text_input("T-L3 (MΩ)")
        
        c13, c1
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")

































































































































































































































































































































