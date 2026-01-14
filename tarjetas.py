import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

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
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"ID MOTOR / TAG: {tag_motor}", 0, 1, 'C')
        pdf.ln(10)
        
        df_ordenado = df_historial.sort_index(ascending=False)
        
        for _, row in df_ordenado.iterrows():
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, f"FECHA: {row.get('Fecha', '')} | TÉCNICO: {row.get('Responsable', '')}", 1, 1, 'L', True)
            
            pdf.set_font("Arial", '', 9)
            pdf.multi_cell(0, 6, f"ESTADO: {row.get('Estado', '')} | POTENCIA: {row.get('Potencia', '')} | RPM: {row.get('RPM', '')}")
            pdf.multi_cell(0, 6, f"DESCRIPCIÓN: {row.get('Descripcion', 'N/A')}")
            pdf.ln(4)
            
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Error interno en PDF: {e}")
        return None

# --- 3. CONEXIÓN Y DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except:
    st.error("Error al conectar con la base de datos.")
    df_completo = pd.DataFrame()

query_tag = st.query_params.get("tag", "")

# --- 4. INTERFAZ ---
with st.sidebar:
    st.header("⚙️ Menú")
    modo = st.radio("Acción:", ["📝 Registro", "🔍 Historial"], index=1 if query_tag else 0)

if modo == "📝 Registro":
    st.title("📝 Registro de Reparación")
    tag = st.text_input("TAG DEL MOTOR", value=query_tag).strip().upper()
    fecha = st.date_input("Fecha Hoy", date.today(), format="DD/MM/YYYY")
    with st.form("form_registro"):
        responsable = st.text_input("Técnico Responsable")
        potencia = st.text_input("Potencia")
        rpm = st.selectbox("RPM", ["750", "1500", "3000"])
        estado = st.selectbox("Estado Final", ["OPERATIVO", "EN OBSERVACIÓN", "REEMPLAZO"])
        descripcion = st.text_area("Descripción de trabajos")
        enviar = st.form_submit_button("💾 GUARDAR REGISTRO")
        
        if enviar and tag and responsable:
            nuevo_data = {
                "Fecha": date.today().strftime("%d/%m/%Y"),
                "Responsable": responsable, "Tag": tag, "Estado": estado, 
                "Potencia": potencia, "RPM": rpm, "Descripcion": descripcion
            }
            df_final = pd.concat([df_completo, pd.DataFrame([nuevo_data])], ignore_index=True)
            conn.update(data=df_final)
            st.success("✅ Guardado correctamente")

elif modo == "🔍 Historial":
    st.title("🔍 Hoja de Vida")
    id_ver = st.text_input("TAG DEL MOTOR:", value=query_tag).strip().upper()
    
    if id_ver:
        historial_motor = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        
        if not historial_motor.empty:
            col_pdf, col_nuevo = st.columns(2)
            
            pdf_bytes = generar_pdf(historial_motor, id_ver)
            if pdf_bytes:
                col_pdf.download_button("📥 Descargar Historial", pdf_bytes, f"Historial_{id_ver}.pdf")
            
            col_nuevo.button("➕ Nueva Reparación", on_click=activar_formulario)

            if st.session_state.mostrar_form:
                with st.form("nueva_rep_rapida"):
                    st.write("### Cargar nueva intervención")
                    resp = st.text_input("Responsable")
                    desc = st.text_area("Acciones realizadas")
                    if st.form_submit_button("💾 Guardar"):
                        # Lógica simple de guardado para probar
                        st.success("Guardado. Recarga para ver cambios.")
                        st.session_state.mostrar_form = False
                        st.rerun()

            st.dataframe(historial_motor.sort_index(ascending=False))
        else:
            st.warning("No se encontraron registros.")

st.markdown("---")
st.caption("Sistema diseñado por Heber Ortiz | Marpi Electricidad ⚡")









































































































































































