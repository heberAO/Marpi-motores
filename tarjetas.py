import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF

# --- 1. FUNCIÓN GENERAR PDF PROFESIONAL ---
def generar_pdf(df_historial, tag_motor):
    pdf = FPDF()
    pdf.add_page()
    # --- INICIALIZAR MEMORIA (Cerca de tus importaciones) ---
if 'mostrar_form' not in st.session_state:
    st.session_state.mostrar_form = False

def activar_formulario():
    st.session_state.mostrar_form = True
    
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
        # Encabezado de Registro
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, f"FECHA: {row.get('Fecha', '')} | TÉCNICO: {row.get('Responsable', '')}", 1, 1, 'L', True)
        
        # Estado
        pdf.cell(40, 8, "ESTADO FINAL:", 1, 0, 'L')
        estado = str(row.get('Estado', 'OPERATIVO'))
        if "OPERATIVO" in estado: pdf.set_text_color(0, 128, 0)
        else: pdf.set_text_color(200, 0, 0)
        pdf.cell(150, 8, estado, 1, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        # --- DATOS DE PLACA (Antes de las mediciones) ---
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 8, f"POTENCIA: {row.get('Potencia', '-')} HP/kW", 1, 0, 'L')
        pdf.cell(95, 8, f"VELOCIDAD: {row.get('RPM', '-')} RPM", 1, 1, 'L')
        pdf.ln(2)
    
        # --- TABLA DE MEDICIONES TÉCNICAS POR FASE ---
        pdf.ln(2)
        pdf.set_fill_color(230, 240, 255)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(63.3, 7, "RES. A TIERRA (M Ohms)", 1, 0, 'C', True)
        pdf.cell(63.3, 7, "RES. ENTRE BOBINAS (Ohms)", 1, 0, 'C', True)
        pdf.cell(63.4, 7, "RES. INTERNA (Ohms)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 8)
        # Fila 1
        pdf.cell(20, 7, "T-U", 1, 0, 'C'); pdf.cell(43.3, 7, str(row.get('RT_TU','-')), 1, 0, 'C')
        pdf.cell(20, 7, "U-V", 1, 0, 'C'); pdf.cell(43.3, 7, str(row.get('RB_UV','-')), 1, 0, 'C')
        pdf.cell(25, 7, "U1-U2", 1, 0, 'C'); pdf.cell(38.4, 7, str(row.get('RI_U','-')), 1, 1, 'C')
        # Fila 2
        pdf.cell(20, 7, "T-V", 1, 0, 'C'); pdf.cell(43.3, 7, str(row.get('RT_TV','-')), 1, 0, 'C')
        pdf.cell(20, 7, "V-W", 1, 0, 'C'); pdf.cell(43.3, 7, str(row.get('RB_VW','-')), 1, 0, 'C')
        pdf.cell(25, 7, "V1-V2", 1, 0, 'C'); pdf.cell(38.4, 7, str(row.get('RI_V','-')), 1, 1, 'C')
        # Fila 3
        pdf.cell(20, 7, "T-W", 1, 0, 'C'); pdf.cell(43.3, 7, str(row.get('RT_TW','-')), 1, 0, 'C')
        pdf.cell(20, 7, "U-W", 1, 0, 'C'); pdf.cell(43.3, 7, str(row.get('RB_UW','-')), 1, 0, 'C')
        pdf.cell(25, 7, "W1-W2", 1, 0, 'C'); pdf.cell(38.4, 7, str(row.get('RI_W','-')), 1, 1, 'C')
        
        # Descripciones
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 7, "ACCIONES REALIZADAS:", "LTR", 1, 'L')
        pdf.set_font("Arial", '', 9)
        pdf.multi_cell(0, 6, str(row.get('Descripcion', 'N/A')), "LRB", 'L')
        
        # Taller Externo
        ext = str(row.get('Taller_Externo', ''))
        if ext and ext != 'None' and ext != '':
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 7, "TRABAJOS EXTERNOS:", "LR", 1, 'L')
            pdf.set_font("Arial", 'I', 9)
            pdf.multi_cell(0, 6, ext, "LRB", 'L')
        
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 2. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

# Detectar TAG desde URL (QR)
query_tag = st.query_params.get("tag", "")

# Conexión
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except:
    st.error("Error al conectar con la base de datos.")
    df_completo = pd.DataFrame()

# Logo
if os.path.exists("logo.png"):
    st.image("logo.png", width=120)

# Función para cambiar el estado
def abrir_formulario():
    st.session_state.mostrar_form = True
# Menú lateral
with st.sidebar:
    st.header("⚙️ Menú")
    modo = st.radio("Acción:", ["📝 Registro", "🔍 Historial"], index=1 if query_tag else 0)

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro":
    st.title("📝 Registro de Reparación")
    
    fecha = st.date_input("Fecha Hoy", date.today(), format="DD/MM/YYYY")
    # 1. El TAG debe estar FUERA del formulario para que Streamlit pueda "reaccionar" al escribirlo
    tag = st.text_input("TAG DEL MOTOR", value=query_tag).strip().upper()
    
    # 2. BUSCAR DATOS PREVIOS
    datos_placa = {"pot": "", "rpm_idx": 1, "frame": ""} # Valores por defecto
    
    if tag and not df_completo.empty:
        historial_previo = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
        
        if not historial_previo.empty:
            ultimo = historial_previo.iloc[-1]
            st.info(f"✅ Cargando datos del motor {tag}")
            
            # 2. EXTRAER DATOS (Usa nombres exactos de tus columnas en Excel)
            datos_placa["pot"] = str(ultimo.get('Potencia', ''))
            datos_placa["frame"] = str(ultimo.get('Frame', '')) # <--- Lee el Frame del Excel
            
            rpm_viejo = str(ultimo.get('RPM', '1500'))
            lista_rpm = ["750", "1500", "3000"]
            if rpm_viejo in lista_rpm:
                datos_placa["rpm_idx"] = lista_rpm.index(rpm_viejo)

    # 3. EL FORMULARIO (Ahora con los valores precargados)
    with st.form("form_tecnico"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Res. Tierra (MΩ)**")
            rt_tu = st.text_input("T - U")
            rt_tv = st.text_input("T - V")
            rt_tw = st.text_input("T - W")
        with col2:
            st.markdown("**Res. Bobinas (MΩ)**")
            rb_uv = st.text_input("U - V")
            rb_vw = st.text_input("V - W")
            rb_uw = st.text_input("U - W")
        with col3:
            st.markdown("**Res. Interna (Ω)**")
            ri_u = st.text_input("U1 - U2")
            ri_v = st.text_input("V1 - V2")
            ri_w = st.text_input("W1 - W2")
        
        st.divider()
        c_inf1, c_inf2, c_inf3, c_inf4 = st.columns(4) # Añadí una 4ta columna
        
        responsable = c_inf1.text_input("Técnico Responsable")
        potencia = c_inf2.text_input("Potencia Motor", value=datos_placa["pot"])
        rpm = c_inf3.selectbox("RPM", ["750", "1500", "3000"], index=datos_placa["rpm_idx"])
        
        # CORRECCIÓN DEL ERROR: Ahora usamos datos_placa["frame"]
        frame_val = c_inf4.text_input("Frame", value=datos_placa["frame"])
        
        estado = st.selectbox("Estado Final", ["OPERATIVO", "EN OBSERVACIÓN", "REEMPLAZO"])
        descripcion = st.text_area("Descripción de trabajos realizados")
        taller_ext_val = st.text_area("Trabajos de terceros")
        
        enviar = st.form_submit_button("💾 GUARDAR REGISTRO")
    if enviar and tag and responsable:
        nuevo_data = {
            "Fecha": date.today().strftime("%d/%m/%Y"),
            "Responsable": responsable, "Tag": tag, "Estado": estado, "Potencia": potencia, "RPM": rpm,
            "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw,
            "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
            "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w,
            "Descripcion": descripcion, 
            "Taller_Externo": taller_ext_val,
        }
        df_nuevo = pd.DataFrame([nuevo_data])
        df_final = pd.concat([df_completo, df_nuevo], ignore_index=True)
        conn.update(data=df_final)
        st.success(f"✅ Motor {tag} guardado exitosamente.")
        
        # Mostrar QR para imprimir de una vez
        st.divider()
        mi_url = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
        link = f"{mi_url}?tag={tag}"
        qr_img = qrcode.make(link)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        st.image(buf, width=150, caption="QR generado para este motor")

elif modo == "🔍 Historial":
    st.title("🔍 Hoja de Vida y Nueva Reparación")
    id_ver = st.text_input("TAG DEL MOTOR:", value=query_tag).strip().upper()
    
    if id_ver:
        # 1. PRIMERO CREAMOS LA VARIABLE filtrando el dataframe
        historial_motor = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        
        if not historial_motor.empty:
            # 2. SOLO AQUÍ DENTRO PODEMOS USAR historial_motor
            st.subheader(f"Registros encontrados para: {id_ver}")
            
            # Preparamos el PDF (dentro del if, cuando estamos seguros de que existe)
            try:
                pdf_bytes = generar_pdf(historial_motor, id_ver)
                
                col_pdf, col_nuevo = st.columns(2)
                col_pdf.download_button("📥 Descargar Historial", pdf_bytes, f"Historial_{id_ver}.pdf")
                col_nuevo.button("➕ Nueva Reparación", on_click=abrir_formulario)
                
            except Exception as e:
                st.error(f"Error al preparar el PDF: {e}")

            # ... resto del código (formulario y tabla) ...
            st.dataframe(historial_motor.sort_index(ascending=False))
            
        else:
            st.warning(f"No hay registros para el motor {id_ver}")

st.markdown("---")
st.caption("Sistema diseñado y desarrollado por **Heber Ortiz** | Marpi Electricidad ⚡")




























































































































































