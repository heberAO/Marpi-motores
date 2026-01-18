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

    st.title("⚡ Mediciones de Campo (Megado y Continuidad)")

    

    if "cnt_meg" not in st.session_state:

        st.session_state.cnt_meg = 0

        

    tag_inicial = st.session_state.get('tag_fijo', '')

    

    with st.form(key=f"form_completo_{st.session_state.cnt_meg}"):

        col_t, col_r = st.columns(2)

        t = col_t.text_input("TAG MOTOR", value=tag_inicial).upper()

        sn = st.text_input("N° de Serie")

        resp = col_r.text_input("Técnico Responsable")

        

        # --- BLOQUE 1 ---

        st.subheader("📊 Megado a tierra (Resistencia)")

        c1, c2, c3 = st.columns(3)

        tv1, tu1, tw1 = c1.text_input("T - V1 (Ω)"), c2.text_input("T - U1 (Ω)"), c3.text_input("T - W1 (Ω)")

        

        # --- BLOQUE 2 ---

        st.subheader("📊 Megado ente Bobinas (Resistencia)")

        c4, c5, c6 = st.columns(3)

        wv1, wu1, vu1 = c4.text_input("W1 - V1 (Ω)"), c5.text_input("W1 - U1 (Ω)"), c6.text_input("V1 - U1 (Ω)")



        # --- BLOQUE 3 ---

        st.subheader("📏 Resistencia internas")

        c7, c8, c9 = st.columns(3)

        u1u2, v1v2, w1w2 = c7.text_input("U1 - U2 (Ω)"), c8.text_input("V1 - V2 (Ω)"), c9.text_input("W1 - W2 (Ω)")



        # --- BLOQUE 4 ---

        st.subheader("🔌 Megado de Línea")

        c10, c11, c12 = st.columns(3)

        tl1, tl2, tl3 = c10.text_input("T - L1 (MΩ)"), c11.text_input("T - L2 (MΩ)"), c12.text_input("T - L3 (MΩ)")

        

        # --- BLOQUE 5 ---

        c13, c14, c15 = st.columns(3)

        l1l2, l1l3, l2l3 = c13.text_input("L1 - L2 (MΩ)"), c14.text_input("L1 - L3 (MΩ)"), c15.text_input("L2 - L3 (MΩ)")



        if btn_guardar:

            if t and resp:

                detalle = (

                    f"MEGADO A TIERRA: T-V1:{tv1}, T-U1:{tu1}, T-W1:{tw1} | "

                    f"MEGADO ENTRE BOBINAS: W1-V1:{wv1}, W1-U1:{wu1}, V1-U1:{vu1} | "

                    f"RESISTENCIAS INTERNAS: U1-U2:{u1u2}, V1-V2:{v1v2}, W1-W2:{w1w2} | "

                    f"MEGADO DE LÍNEA (TIERRA): T-L1:{tl1}, T-L2:{tl2}, T-L3:{tl3} | "

                    f"MEGADO DE LÍNEA (FASES): L1-L2:{l1l2}, L1-L3:{l1l3}, L2-L3:{l2l3}"

                )

                

                nueva = {

                    "Fecha": date.today().strftime("%d/%m/%Y"),

                    "Tag": t,

                    "Responsable": resp,

                    "Descripcion": detalle,

                    "Taller_Externo": f"N/S: {sn}. Mediciones completas registradas."

                }

                

                # Guardar en la base de datos

                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)

                conn.update(data=df_final)

                

                # Limpiar y reiniciar

                st.session_state.tag_fijo = ""

                st.session_state.cnt_meg += 1 

                st.success(f"✅ Informe de {t} generado correctamente")

                st.rerun()

            else:

                st.error("⚠️ Falta completar TAG o Técnico")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")








































































































































































































































































































































