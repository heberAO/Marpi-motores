import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

# --- ¡PASO CLAVE PARA EL QR! ---
# Leemos el parámetro de la URL justo al empezar
parametros = st.query_params
query_tag = parametros.get("tag", "").upper()

if 'mostrar_form' not in st.session_state:
    st.session_state.mostrar_form = False

def activar_formulario():
    st.session_state.mostrar_form = True

# --- 2. FUNCIÓN GENERAR PDF ---
def generar_pdf(df_historial, tag_motor):
    try:
        pdf = FPDF()
        pdf.add_page()
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 33)
        
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, 'INFORME TÉCNICO DE MANTENIMIENTO', 0, 1, 'C')
        pdf.ln(5)
        
        fijos = df_historial.iloc[0]
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"TAG: {tag_motor}  |  POTENCIA: {fijos.get('Potencia','-')}  |  RPM: {fijos.get('RPM','-')}", 1, 1, 'C')
        pdf.ln(5)

        for _, row in df_historial.sort_index(ascending=False).iterrows():
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, f"FECHA: {row.get('Fecha', '')} | TÉCNICO: {row.get('Responsable', '')}", 1, 1, 'L', True)
            
            pdf.set_font("Arial", '', 9)
            pdf.cell(0, 6, f"Res. Tierra (MΩ): {row.get('RT_TU','-')} / {row.get('RT_TV','-')} / {row.get('RT_TW','-')}", 0, 1)
            pdf.cell(0, 6, f"Res. Bobinas (Ω): {row.get('RB_UV','-')} / {row.get('RB_VW','-')} / {row.get('RB_UW','-')}", 0, 1)
            pdf.cell(0, 6, f"Res. Interna (Ω): {row.get('RI_U','-')} / {row.get('RI_V','-')} / {row.get('RI_W','-')}", 0, 1)
            
            pdf.multi_cell(0, 6, f"TRABAJOS: {row.get('Descripcion', 'N/A')}")
            ext = row.get('Taller_Externo', '')
            if ext and str(ext) != 'nan':
                pdf.multi_cell(0, 6, f"EXTERNOS: {ext}")
            pdf.ln(3)
            
        return pdf.output(dest='S').encode('latin-1')
    except Exception:
        return None

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except:
    st.error("Error de conexión.")
    df_completo = pd.DataFrame()

# --- 4. INTERFAZ ---
with st.sidebar:
    st.header("⚡ Marpi Electricidad")
    # Si entramos por QR, forzamos que el menú se ponga en Historial
    inicio_modo = "🔍 Historial / QR" if query_tag else "📝 Registro Nuevo"
    modo = st.radio("Menú:", ["📝 Registro Nuevo", "🔍 Historial / QR"], index=1 if query_tag else 0)

# --- MODO REGISTRO NUEVO ---
if modo == "📝 Registro Nuevo":
    st.title("📝 Alta y Registro Inicial de Motor")
    with st.form("alta_motor_completa"):
        col_id1, col_id2, col_id3, col_id4 = st.columns(4)
        t = col_id1.text_input("TAG/ID MOTOR").upper()
        p = col_id2.text_input("Potencia (HP/kW)")
        r = col_id3.selectbox("RPM", ["-", "750", "1500", "3000"])
        f = col_id4.text_input("Frame / Carcasa")
        
        st.markdown("---")
        st.subheader("🔍 Mediciones Iniciales")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.write("**Tierra (MΩ)**")
            rt_tu = st.text_input("T-U")
            rt_tv = st.text_input("T-V")
            rt_tw = st.text_input("T-W")
        with m2:
            st.write("**Bobinas (Ω)**")
            rb_uv = st.text_input("U-V")
            rb_vw = st.text_input("V-W")
            rb_uw = st.text_input("U-W")
        with m3:
            st.write("**Interna (Ω)**")
            ri_u = st.text_input("U1-U2")
            ri_v = st.text_input("V1-V2")
            ri_w = st.text_input("W1-W2")
            
        st.markdown("---")
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción inicial / Trabajos")
        ext = st.text_area("Trabajos Externos")
        
        if st.form_submit_button("💾 REGISTRAR MOTOR"):
            if t and resp:
                nueva_fila = {
                    "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f,
                    "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext,
                    "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw,
                    "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                    "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"✅ Motor {t} registrado.")
            else:
                st.error("⚠️ Tag y Técnico son obligatorios.")

# --- MODO HISTORIAL / QR ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida del Motor")
    
    # El valor por defecto ahora es query_tag (lo que lee del QR)
    id_ver = st.text_input("ESCRIBIR TAG:", value=query_tag).strip().upper()
    
    if id_ver:
        historial = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        
        if not historial.empty:
            orig = historial.iloc[0]
            st.subheader(f"Motor: {id_ver} | {orig.get('Potencia','-')} | {orig.get('RPM','-')} RPM")
            
            col_pdf, col_qr, col_form = st.columns(3)
            
            # 1. PDF
            pdf_b = generar_pdf(historial, id_ver)
            if pdf_b:
                col_pdf.download_button("📥 Informe PDF", pdf_b, f"Informe_{id_ver}.pdf")
            
            # 2. QR ÚNICO
            url_base = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
            link_directo = f"{url_base}?tag={id_ver}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(link_directo)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img_qr.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            col_qr.image(byte_im, width=120, caption="QR Único")
            col_qr.download_button("💾 Guardar imagen QR", byte_im, f"QR_{id_ver}.png", "image/png")
            
            # 3. NUEVA REPARACIÓN
            col_form.button("➕ Cargar Nueva Reparación", on_click=activar_formulario)
            
            if st.session_state.mostrar_form:
                with st.form("nueva_rep"):
                    st.write("### 🛠️ Registrar Intervención")
                    f_rep = st.date_input("Fecha", date.today())
                    t_resp = st.text_input("Técnico")
                    
                    st.markdown("**Mediciones Actuales**")
                    col_t, col_b, col_i = st.columns(3)
                    with col_t:
                        rt1 = st.text_input("T-U (Tierra)")
                        rt2 = st.text_input("T-V (Tierra)")
                        rt3 = st.text_input("T-W (Tierra)")
                    with col_b:
                        rb1 = st.text_input("U-V (Bobina)")
                        rb2 = st.text_input("V-W (Bobina)")
                        rb3 = st.text_input("U-W (Bobina)")
                    with col_i:
                        ri1 = st.text_input("U1-U2 (Interna)")
                        ri2 = st.text_input("V1-V2 (Interna)")
                        ri3 = st.text_input("W1-W2 (Interna)")
                    
                    d_rep = st.text_area("Trabajos realizados")
                    e_rep = st.text_area("Taller externo")
                    
                    if st.form_submit_button("💾 GUARDAR EN HISTORIAL"):
                        nueva_data = {
                            "Fecha": f_rep.strftime("%d/%m/%Y"), "Tag": id_ver, "Responsable": t_resp,
                            "Potencia": orig.get('Potencia','-'), "RPM": orig.get('RPM', '-'),
                            "Frame": orig.get('Frame', '-'),
                            "RT_TU": rt1, "RT_TV": rt2, "RT_TW": rt3,
                            "RB_UV": rb1, "RB_VW": rb2, "RB_UW": rb3,
                            "RI_U": ri1, "RI_V": ri2, "RI_W": ri3,
                            "Descripcion": d_rep, "Taller_Externo": e_rep
                        }
                        df_final = pd.concat([df_completo, pd.DataFrame([nueva_data])], ignore_index=True)
                        conn.update(data=df_final)
                        st.session_state.mostrar_form = False
                        st.rerun()

            st.markdown("---")
            st.dataframe(historial.sort_index(ascending=False))
        else:
            st.warning(f"⚠️ El motor '{id_ver}' no existe en la base de datos.")
st.markdown("---")
st.caption("Sistema diseñado y desarollado por Heber Ortiz | Marpi Electricidad ⚡")


































































































































































































