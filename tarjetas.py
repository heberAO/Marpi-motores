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

# --- 5. MENÚ LATERAL ---
opciones_menu = ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"]

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    
    # Si no existe la opción en memoria, usamos el índice del QR
    if "seleccion_manual" not in st.session_state:
        st.session_state.seleccion_manual = opciones_menu[indice_inicio]

    # El radio se alimenta de la variable 'seleccion_manual'
    modo = st.radio(
        "SELECCIONE:", 
        opciones_menu,
        index=opciones_menu.index(st.session_state.seleccion_manual)
    )
    # Actualizamos la memoria con lo que el usuario toque físicamente
    st.session_state.seleccion_manual = modo
    
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
        
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, "Responsable": resp, "Descripcion": desc, "Taller_Externo": obs}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            
            # LIMPIEZA DE CAMPOS
            st.session_state.tag_fijo = "" 
            st.success("✅ Registro guardado con éxito")
            st.rerun() # Esto limpia el formulario automáticamente
  
elif modo == "Historial y QR":
    st.title("🔍 Consulta y Gestión de Motores")
    
    if not df_completo.empty:
        # 1. Lista para el buscador (TAG + Serie)
        df_completo['Busqueda_Combo'] = (
            df_completo['Tag'].astype(str) + " | SN: " + df_completo['N_Serie'].astype(str)
        )
        opciones = [""] + sorted(df_completo['Busqueda_Combo'].unique().tolist())
        
        # 2. Detección de QR
        query_tag = st.query_params.get("tag", "").upper()
        idx_q = 0
        if query_tag:
            for i, op in enumerate(opciones):
                if op.startswith(query_tag + " |"):
                    idx_q = i
                    break
        
        seleccion = st.selectbox("Busca por TAG o N° de Serie:", opciones, index=idx_q)
        
        if seleccion:
            # Extraemos el TAG puro
            buscado = seleccion.split(" | ")[0].strip()
            st.session_state.tag_fijo = buscado
            
           # --- BOTONES DE ACCIÓN RÁPIDA ---
            st.subheader("➕ ¿Qué deseas cargar para este motor?")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                if st.button("🛠️ Nueva Reparación"):
                    st.session_state.seleccion_manual = "Nuevo Registro"
                    st.rerun()
            with c2:
                if st.button("🛢️ Nueva Lubricación"):
                    st.session_state.seleccion_manual = "Relubricacion"
                    st.rerun()
            with c3:
                if st.button("⚡ Nuevo Megado"):
                    st.session_state.seleccion_manual = "Mediciones de Campo"
                    st.rerun()
            # --- QR Y DATOS ---
            col_qr, col_info = st.columns([1, 2])
            url_app = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?tag={buscado}"
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
            
            with col_qr:
                st.image(qr_api, caption=f"QR de {buscado}")
            with col_info:
                st.subheader(f"🚜 Equipo seleccionado: {buscado}")
                st.write(f"**Link directo:** {url_app}")
            
            st.divider()

# --- HISTORIAL Y PDF ---
            st.subheader("📜 Historial de Intervenciones")
            hist_m = df_completo[df_completo['Tag'] == buscado].copy()
            
            # Corregido: le agregamos el ] al final
            hist_m = hist_m.iloc[::-1] 

            for idx, fila in hist_m.iterrows():
                intervencion = str(fila.get('Descripcion', '-'))[:40]
                with st.expander(f"📅 {fila.get('Fecha','-')} - {intervencion}..."):
                    st.write(f"**Responsable:** {fila.get('Responsable','-')}")
                    st.write(f"**Detalle completo:** {fila.get('Descripcion','-')}")
                    
                    # Generar PDF
                    pdf_archivo = generar_pdf_reporte(fila.to_dict(), buscado)
                    
                    if pdf_archivo:
                        st.download_button(
                            label="📄 Descargar Informe PDF",
                            data=pdf_archivo,
                            file_name=f"Reporte_{buscado}_{idx}.pdf",
                            key=f"btn_pdf_{idx}"
                        )
elif modo == "Relubricacion":
    st.title("🛢️ Gestión de Relubricación Detallada")
    with st.form("relub"):
        t_r = st.text_input("TAG DEL MOTOR", value=st.session_state.tag_fijo).upper()
        sn_r = st.text_input("N° de Serie")
        resp_r = st.text_input("Responsable de Tarea")
        
        st.subheader("🔧 Datos de Rodamientos")
        c1, c2 = st.columns(2)
        with c1:
            rod_la = st.text_input("Rodamiento LA")
            gr_la = st.text_input("Gramos LA")
        with c2:
            rod_loa = st.text_input("Rodamiento LOA")
            gr_loa = st.text_input("Gramos LOA")
            
        grasa = st.selectbox("Tipo de Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
        obs = st.text_area("Observaciones del estado de rodamientos")
        
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Responsable": resp, "Descripcion": f"LUBRICACIÓN: {det}"}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            
            # LIMPIEZA DE CAMPOS
            st.session_state.tag_fijo = ""
            st.success("✅ Lubricación registrada")
            st.rerun()
elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo Completas")
    with st.form("campo"):
        t_c = st.text_input("TAG MOTOR", value=st.session_state.tag_fijo).upper()
        sn_c = st.text_input("N° SERIE")
        resp_c = st.text_input("Técnico")
        volt = st.selectbox("Voltaje de Prueba", ["500V", "1000V", "2500V"])
        
        st.subheader("📊 Valores de Resistencia de Aislación")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Aislación Motor (MΩ)**")
            ri_u = st.text_input("U1-U2 / Masa")
            ri_v = st.text_input("V1-V2 / Masa")
            ri_w = st.text_input("W1-W2 / Masa")
        with col2:
            st.markdown("**Continuidad Bobinados (Ω)**")
            rt_tu = st.text_input("T-U (Bobinado)")
            rt_tv = st.text_input("T-V (Bobinado)")
            rt_tw = st.text_input("T-W (Bobinado)")
            
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Responsable": resp, "Descripcion": f"MEGADO: {val}"}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            
            # LIMPIEZA DE CAMPOS
            st.session_state.tag_fijo = ""
            st.success("✅ Medición guardada")
            st.rerun()
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")














































































































































































































































































































