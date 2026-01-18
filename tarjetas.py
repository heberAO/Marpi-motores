import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse  # Para el QR sin errores

# --- 1. FUNCIÓN PDF (Mantiene tus campos) ---
def generar_pdf_reporte(datos, tag_motor, tipo_trabajo="INFORME TÉCNICO"):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 30)
        
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, f'{tipo_trabajo}', 0, 1, 'R')
        pdf.ln(10)
        
        pdf.set_fill_color(230, 233, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 8, f"Fecha: {datos.get('Fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos.get('Responsable','-')}", 1, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DESCRIPCIÓN Y MEDICIONES:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "ESTADO FINAL / OBSERVACIONES:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Taller_Externo','-')), border=1)

        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

# --- 2. CONFIGURACIÓN INICIAL (DEBE IR AQUÍ ARRIBA) ---
st.set_page_config(page_title="Marpi Motores", layout="wide")

# Inicializamos variables de estado
if "tag_fijo" not in st.session_state: st.session_state.tag_fijo = ""
if "modo_manual" not in st.session_state: st.session_state.modo_manual = False

# --- 3. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    df_completo = pd.DataFrame()

# --- 4. LÓGICA DE REDIRECCIÓN QR ---
query_params = st.query_params
qr_tag = query_params.get("tag", "")

# Si el QR trae un motor y el usuario no ha cambiado de pestaña manualmente
if qr_tag and not st.session_state.modo_manual:
    indice_inicio = 1 # Posición de "Historial y QR"
else:
    indice_inicio = 0

# --- 5. UN SOLO MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    
    modo = st.radio(
        "SELECCIONE:", 
        ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"],
        index=indice_inicio
    )
    
    # Si el usuario hace click en el menú, bloqueamos la redirección del QR para que pueda navegar
    if st.sidebar.button("Resetear Navegación"):
        st.session_state.modo_manual = True
        st.query_params.clear()
        st.rerun()

# --- 5. SECCIONES (CON TUS CAMPOS ORIGINALES) ---

if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
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
        
        if st.form_submit_button("💾 GUARDAR REGISTRO"):
            if t and resp:
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f, "N_Serie": sn,
                    "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext,
                    "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw, "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                    "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"✅ Registro Guardado para {t}"); st.rerun()
            else:
                st.warning("Por favor, completa el TAG y el Responsable.")

elif modo == "Historial y QR":
    st.title("🔍 Historial por TAG o N° de Serie")
    if not df_completo.empty:
        # Buscador dual: TAG + N_Serie
        df_completo['Busqueda'] = df_completo['Tag'].astype(str) + " | SN: " + df_completo['N_Serie'].astype(str)
        lista_busqueda = [""] + sorted(list(df_completo['Busqueda'].unique()))
        
        # Si venimos de QR
        indice_qr = 0
        if qr_tag:
            # Buscamos si el qr_tag coincide con algún motor
            for i, item in enumerate(lista_busqueda):
                if qr_tag in item:
                    indice_qr = i
                    break

        seleccion = st.selectbox("Buscar por TAG o N° de Serie:", lista_busqueda, index=indice_qr)
        
        if seleccion:
            # Extraemos el TAG puro de la selección
            buscado = seleccion.split(" | ")[0]
            st.session_state.tag_fijo = buscado
            
            # --- QR ---
            url_app = f"https://marpi-motores.streamlit.app/?tag={buscado}"
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
            
            c1, c2 = st.columns([1,3])
            c1.image(qr_api, caption=f"QR {buscado}")
            c2.subheader(f"🚜 Ficha Técnica: {buscado}")
            
            # --- HISTORIAL ---
            hist_m = df_completo[df_completo['Tag'] == buscado].copy()
            for idx, fila in hist_m.iterrows():
                with st.expander(f"📅 {fila.get('Fecha','-')} - {fila.get('Responsable','-')}"):
                    st.write(f"**Trabajo:** {fila.get('Descripcion','-')}")
                    st.write(f"**Observaciones:** {fila.get('Taller_Externo','-')}")
                    pdf_b = generar_pdf_reporte(fila.to_dict(), buscado)
                    if pdf_b:
                        st.download_button("📄 Bajar PDF", pdf_b, f"Informe_{idx}.pdf", key=f"h_{idx}")

elif modo == "Relubricacion":
    st.title("🛢️ Cargar Nueva Lubricación")
    with st.form("relub"):
        t_r = st.text_input("TAG DEL MOTOR", value=st.session_state.tag_fijo).upper()
        resp_r = st.text_input("Técnico")
        c1, c2 = st.columns(2)
        grasa = st.selectbox("Grasa Utilizada", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
        cant = st.text_input("Cantidad Total (Gramos)")
        obs = st.text_area("Puntos lubricados / Observaciones")
        
        if st.form_submit_button("💾 GUARDAR LUBRICACIÓN"):
            if t_r and resp_r:
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_r, "Responsable": resp_r,
                    "Descripcion": f"LUBRICACIÓN: {grasa} - Cantidad: {cant}g",
                    "Taller_Externo": obs
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                st.success("✅ Lubricación guardada"); st.rerun()

elif modo == "Mediciones de Campo":
    st.title("⚡ Cargar Nuevo Megado (Campo)")
    with st.form("campo"):
        t_c = st.text_input("TAG MOTOR", value=st.session_state.tag_fijo).upper()
        resp_c = st.text_input("Técnico")
        volt = st.selectbox("Voltaje aplicado", ["500V", "1000V", "2500V"])
        
        st.markdown("### 🟢 Valores de Aislación")
        c1, c2, c3 = st.columns(3)
        m_u = c1.text_input("Fase U (MΩ)")
        m_v = c2.text_input("Fase V (MΩ)")
        m_w = c3.text_input("Fase W (MΩ)")
        
        if st.form_submit_button("💾 GUARDAR MEDICIÓN"):
            if t_c and resp_c:
                detalle = f"MEGADO {volt}. Lecturas: U:{m_u} / V:{m_v} / W:{m_w}"
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_c, "Responsable": resp_c,
                    "Descripcion": detalle, "Taller_Externo": "Medición de aislación en campo"
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                st.success("✅ Megado guardado"); st.rerun()
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")





























































































































































































































































































