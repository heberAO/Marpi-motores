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
        frame = st.text_input("Frame")
        rpm = st.selectbox("RPM", ["-", "750", "1500", "3000"])
        estado = st.selectbox("Estado Final", ["OPERATIVO", "EN OBSERVACIÓN", "REEMPLAZO"])
        descripcion = st.text_area("Descripción de trabajos")
        externo = st.text_area("Taller Externo")
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
                    st.write(f"### 📝 Nueva Reparación para {id_ver}")
                    
                    # Fila 1: Datos de la Intervención
                    c1, c2 = st.columns(2)
                    with c1:
                        fecha_rep = st.date_input("Fecha del trabajo", date.today())
                    with c2:
                        resp = st.text_input("Técnico Responsable")
                    
                    # Fila 2: Mediciones Técnicas (Cruciales para el seguimiento)
                    st.markdown("**🔍 Mediciones Eléctricas**")
                    col_t, col_b, col_i = st.columns(3)
                    
                    with col_t:
                        st.caption("Tierra (MΩ)")
                        rt_tu = st.text_input("T-U", key="rtu_hist")
                        rt_tv = st.text_input("T-V", key="rtv_hist")
                        rt_tw = st.text_input("T-W", key="rtw_hist")
                    with col_b:
                        st.caption("Entre Bobinas (Ω)")
                        rb_uv = st.text_input("U-V", key="rb_uv_h")
                        rb_vw = st.text_input("V-W", key="rb_vw_h")
                        rb_uw = st.text_input("U-W", key="rb_uw_h")
                    with col_i:
                        st.caption("Interna (Ω)")
                        ri_u = st.text_input("U1-U2", key="riu_h")
                        ri_v = st.text_input("V1-V2", key="riv_h")
                        ri_w = st.text_input("W1-W2", key="riw_h")
                    
                    st.divider()
                    
                    # Fila 3: Resultados
                    est = st.selectbox("Estado de Salida", ["OPERATIVO", "EN OBSERVACIÓN", "REEMPLAZO"])
                    desc = st.text_area("Trabajos Realizados")
                    ext = st.text_area("Trabajos de Terceros / Tornería")
                    
                    # Botón de Guardado
                    if st.form_submit_button("💾 REGISTRAR INTERVENCIÓN"):
                        if resp and desc:
                            # Importante: Buscamos los datos fijos (Potencia/RPM) 
                            # del último registro para no perderlos en la fila nueva
                            ultimo_registro = historial_motor.iloc[-1]
                            
                            nueva_fila = {
                                "Fecha": fecha_rep.strftime("%d/%m/%Y"),
                                "Responsable": resp,
                                "Tag": id_ver,
                                "Estado": est,
                                # Datos de Placa (se mantienen del registro original)
                                "Potencia": ultimo_registro.get('Potencia', '-'),
                                "RPM": ultimo_registro.get('RPM', '-'),
                                "Frame": ultimo_registro.get('Frame', '-'),
                                # Nuevos datos técnicos
                                "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw,
                                "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                                "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w,
                                "Descripcion": desc,
                                "Taller_Externo": ext
                            }
                            
                            # Actualización en Google Sheets
                            df_nuevo = pd.DataFrame([nueva_fila])
                            df_final = pd.concat([df_completo, df_nuevo], ignore_index=True)
                            conn.update(data=df_final)
                            
                            st.success("✅ Historial actualizado correctamente.")
                            st.session_state.mostrar_form = False
                            st.rerun()
                        else:
                            st.warning("⚠️ Completa el nombre del Técnico y la Descripción.")

            st.dataframe(historial_motor.sort_index(ascending=False))
        else:
            st.warning("No se encontraron registros.")

st.markdown("---")
st.caption("Sistema diseñado por Heber Ortiz | Marpi Electricidad ⚡")











































































































































































