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

if 'mostrar_form' not in st.session_state:
    st.session_state.mostrar_form = False

def activar_formulario():
    st.session_state.mostrar_form = True

# --- 2. FUNCIÓN GENERAR PDF (CORREGIDA) ---
def generar_pdf(df_historial, tag_motor):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 33)
        
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, 'INFORME TÉCNICO DE MANTENIMIENTO', 0, 1, 'C')
        pdf.ln(10)
        
        # Datos fijos (Placa) del primer registro
        fijos = df_historial.iloc[0]
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"TAG: {tag_motor}  |  POTENCIA: {fijos.get('Potencia','-')}  |  RPM: {fijos.get('RPM','-')}", 1, 1, 'C')
        pdf.ln(5)

        for _, row in df_historial.sort_index(ascending=False).iterrows():
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, f"FECHA: {row.get('Fecha', '')} | TÉCNICO: {row.get('Responsable', '')}", 1, 1, 'L', True)
            
            # Mediciones
            pdf.set_font("Arial", '', 9)
            pdf.cell(0, 6, f"Res. Tierra: {row.get('RT_TU','-')}/{row.get('RT_TV','-')}/{row.get('RT_TW','-')} MΩ", 0, 1)
            pdf.cell(0, 6, f"Res. Bobinas: {row.get('RB_UV','-')}/{row.get('RB_VW','-')}/{row.get('RB_UW','-')} Ω", 0, 1)
            
            # Descripción y Externos
            pdf.multi_cell(0, 6, f"TRABAJOS: {row.get('Descripcion', 'N/A')}")
            ext = row.get('Taller_Externo', '')
            if ext and str(ext) != 'nan':
                pdf.multi_cell(0, 6, f"EXTERNOS: {ext}")
            pdf.ln(3)
            
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return None

# --- 3. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except:
    st.error("Error de conexión.")
    df_completo = pd.DataFrame()

query_tag = st.query_params.get("tag", "")

# --- 4. LÓGICA DE INTERFAZ ---
with st.sidebar:
    st.header("⚙️ Marpi Electricidad")
    modo = st.radio("Menú:", ["📝 Registro Nuevo", "🔍 Historial / QR"])

if modo == "📝 Registro Nuevo":
    st.title("📝 Alta de Motor")
    with st.form("alta_motor"):
        t = st.text_input("TAG/ID MOTOR").upper()
        p = st.text_input("Potencia (HP/kW)")
        r = st.selectbox("RPM", ["750", "1500", "3000"])
        f = st.text_input("Frame / Carcasa")
        resp = st.text_input("Técnico")
        desc = st.text_area("Descripción inicial")
        
        if st.form_submit_button("💾 REGISTRAR"):
            nueva_fila = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f, "Responsable": resp, "Descripcion": desc}
            df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
            conn.update(data=df_final)
            st.success("Motor registrado.")

elif modo == "🔍 Historial / QR":
    st.title("🔍 Historial de Motor")
    id_ver = st.text_input("ESCRIBIR TAG:", value=query_tag).strip().upper()
    
    if id_ver:
        historial = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        
        if not historial.empty:
            # Mostrar datos de placa actuales
            original = historial.iloc[0]
            st.subheader(f"Motor: {id_ver} | {original.get('Potencia','-')} | {original.get('RPM','-')} RPM")
            
            col_pdf, col_nuevo = st.columns(2)
            
            # Botón PDF
            pdf_bytes = generar_pdf(historial, id_ver)
            if pdf_bytes:
                col_pdf.download_button("📥 Informe PDF", pdf_bytes, f"{id_ver}.pdf")
            
            col_nuevo.button("➕ Cargar Reparación", on_click=activar_formulario)

            # FORMULARIO DE NUEVA REPARACIÓN
            if st.session_state.mostrar_form:
                with st.form("form_hist"):
                    st.write("### Nueva Intervención")
                    c1, c2 = st.columns(2)
                    f_rep = c1.date_input("Fecha", date.today())
                    t_resp = c2.text_input("Técnico")
                    
                    st.write("**Mediciones**")
                    m1, m2, m3 = st.columns(3)
                    rt = m1.text_input("Tierra (TU/TV/TW)")
                    rb = m2.text_input("Bobinas (UV/VW/UW)")
                    ri = m3.text_input("Interna (U/V/W)")
                    
                    desc_rep = st.text_area("Detalle del trabajo")
                    ext_rep = st.text_area("Taller Externo")
                    
                    if st.form_submit_button("💾 GUARDAR"):
                        # AQUÍ LA CLAVE: Copiamos los datos de placa del registro original
                        nueva_data = {
                            "Fecha": f_rep.strftime("%d/%m/%Y"),
                            "Tag": id_ver,
                            "Responsable": t_resp,
                            "Potencia": original.get('Potencia','-'),
                            "RPM": original.get('RPM','-'),
                            "Frame": original.get('Frame','-'),
                            "RT_TU": rt, "Descripcion": desc_rep, "Taller_Externo": ext_rep
                        }
                        df_final = pd.concat([df_completo, pd.DataFrame([nueva_data])], ignore_index=True)
                        conn.update(data=df_final)
                        st.session_state.mostrar_form = False
                        st.rerun()

            st.dataframe(historial.sort_index(ascending=False))
        else:
            st.warning("No existe el motor.")

st.markdown("---")
st.caption("Sistema diseñado por Heber Ortiz | Marpi Electricidad ⚡")












































































































































































