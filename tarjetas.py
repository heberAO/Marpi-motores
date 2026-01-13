import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF # <--- Nueva librería para PDF

# 1. FUNCIÓN PARA GENERAR EL PDF
def generar_pdf(df_historial, tag_motor):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. ENCABEZADO Y LOGO
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 8, 33)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'INFORME TÉCNICO DE MANTENIMIENTO', 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"ID MOTOR / TAG: {tag_motor}", 0, 1, 'C')
    pdf.ln(10)
    
    # 2. ENCABEZADOS DE TABLA (Colores de Marpi)
    pdf.set_fill_color(40, 40, 40) # Fondo oscuro
    pdf.set_text_color(255, 255, 255) # Texto blanco
    pdf.set_font("Arial", 'B', 10)
    
    # Definimos anchos de columnas
    w_resp = 40
    w_desc = 110
    w_fecha = 35
    
    pdf.cell(w_resp, 10, "Responsable", 1, 0, 'C', True)
    pdf.cell(w_desc, 10, "Reparación / Descripción", 1, 0, 'C', True)
    pdf.cell(w_fecha, 10, "Fecha", 1, 1, 'C', True)
    
    # 3. CONTENIDO DE LA TABLA
    pdf.set_text_color(0, 0, 0) # Volver a texto negro
    pdf.set_font("Arial", '', 9)
    
    # Ordenamos por fecha (lo más nuevo primero) antes de imprimir
    df_ordenado = df_historial.sort_index(ascending=False)
    
    for _, row in df_ordenado.iterrows():
        resp = str(row.get('Responsable', ''))
        desc = str(row.get('Descripcion', ''))
        fec = str(row.get('Fecha', ''))
        
        # Guardamos la posición actual para la descripción multilínea
        x = pdf.get_x()
        y = pdf.get_y()
        
        # Columna Responsable
        pdf.multi_cell(w_resp, 10, resp, 1, 'C')
        
        # Columna Descripción (Ajusta el alto automáticamente)
        pdf.set_xy(x + w_resp, y)
        pdf.multi_cell(w_desc, 10, desc, 1, 'L')
        
        # Columna Fecha
        final_y = pdf.get_y() # Guardamos donde terminó la descripción
        pdf.set_xy(x + w_resp + w_desc, y)
        pdf.multi_cell(w_fecha, (final_y - y), fec, 1, 'C')
        
        pdf.set_xy(x, final_y) # Movemos el puntero al inicio de la siguiente fila
        
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, f"Documento generado el {date.today().strftime('%d/%m/%Y')} - Sistema Marpi Electricidad", 0, 0, 'C')
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# 2. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

if 'guardado' not in st.session_state:
    st.session_state.guardado = False

query_tag = st.query_params.get("tag", "")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    df_completo = pd.DataFrame()

with st.sidebar:
    st.header("⚙️ Menú Marpi")
    default_index = 1 if query_tag else 0
    modo = st.radio("Seleccione:", ["📝 Registro", "🔍 Historial / QR"], index=default_index)

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro":
    st.title("📝 Registro de Reparación")
    tag = st.text_input("Tag / ID Motor", value=query_tag).strip().upper()
    
    datos_previa = {"Pot": "", "Ten": "", "RPM": ""}
    if tag and not df_completo.empty:
        historia = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
        if not historia.empty:
            ultimo = historia.iloc[-1]
            datos_previa = {"Pot": str(ultimo.get('Potencia', '')), "Ten": str(ultimo.get('Tension', '')), "RPM": str(ultimo.get('RPM', ''))}

    with st.form("form_reparacion"):
        c1, c2 = st.columns(2)
        with c1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("Fecha", date.today())
            descripcion = st.text_area("Detalles del trabajo")
        with c2:
            pot = st.text_input("Potencia", value=datos_previa["Pot"])
            ten = st.text_input("Tensión", value=datos_previa["Ten"])
            rpm = st.text_input("RPM", value=datos_previa["RPM"])
            rt = st.text_input("Res. Tierra (Ω)")
            rb = st.text_input("Res. E.Bobina (Ω)")
            ri = st.text_input("Res. Interna (Ω)")
        enviar = st.form_submit_button("💾 GUARDAR")

    if enviar and tag and responsable:
        nuevo = pd.DataFrame([{"Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag, "Potencia": pot, "Tension": ten, "RPM": rpm, "Res_Tierra": rt, "Res_Bobinas": rb, "Res_Interna": ri, "Descripcion": descripcion}])
        df_final = pd.concat([df_completo, nuevo], ignore_index=True)
        conn.update(data=df_final)
        st.success("✅ Guardado.")
        st.rerun()

    if tag:
        mi_url = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
        link = f"{mi_url}?tag={tag}"
        qr_gen = qrcode.make(link)
        buf = BytesIO()
        qr_gen.save(buf, format="PNG")
        st.image(buf, width=150, caption=f"QR: {tag}")

# --- MODO 2: HISTORIAL ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida")
    id_ver = st.text_input("ID Motor:", value=query_tag).strip().upper()
    
    if id_ver and not df_completo.empty:
        res = df_completo[df_completo['Tag'].astype(str).str.upper() == id_ver]
        if not res.empty:
            st.subheader(f"Historial de {id_ver}")
            st.dataframe(res.sort_index(ascending=False), use_container_width=True)
            
            # --- BOTÓN DE DESCARGA PDF ---
            try:
                pdf_bytes = generar_pdf(res, id_ver)
                st.download_button(
                    label="📥 Descargar Historial en PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_{id_ver}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")
        else:
            st.warning("Sin registros.")

st.markdown("---")
st.caption("Sistema diseñado y desarrollado por **Heber Ortiz** | Marpi Electricidad ⚡")



























































































































