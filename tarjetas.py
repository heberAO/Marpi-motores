import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse  # Para el QR sin errores

# --- 1. FUNCIÓN PDF (Mantiene tus campos) ---
def generar_pdf_reporte(datos, tag_motor):
    try:
        desc_full = str(datos.get('Descripcion', '')).upper()
        
        # 1. CREAR EL OBJETO PDF PRIMERO
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # 2. DEFINIR COLORES Y TÍTULO SEGÚN EL TRABAJO
        if "|" in desc_full or "RESISTENCIAS" in desc_full:
            color_rgb = (204, 102, 0) # Naranja para Megado
            tipo_label = "PROTOCOLO DE MEDICIONES ELÉCTRICAS"
        elif "LUBRICACIÓN" in desc_full or "LUBRICACION" in desc_full:
            color_rgb = (0, 102, 204) # Azul para Lubricación
            tipo_label = "REPORTE DE LUBRICACIÓN"
        else:
            color_rgb = (60, 60, 60) # Gris para Reparación
            tipo_label = "REPORTE TÉCNICO DE REPARACIÓN"

        # Encabezado con Logo
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 35)
        
        pdf.set_text_color(*color_rgb)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, tipo_label, 0, 1, 'R')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(12)
        
        # Tabla de Identificación del Equipo
        pdf.set_fill_color(*color_rgb)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 7, " FECHA:", 1, 0)
        pdf.set_font("Arial", '', 9)
        pdf.cell(55, 7, f" {datos.get('Fecha','-')}", 1, 0)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 7, " RESPONSABLE:", 1, 0)
        pdf.set_font("Arial", '', 9)
        pdf.cell(55, 7, f" {datos.get('Responsable','-')}", 1, 1)
        
        pdf.ln(5)

        # --- SECCIÓN DE DETALLE DE MEDICIONES ---
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " DETALLE TÉCNICO Y VALORES REGISTRADOS:", 1, 1, 'L', True)
        
        pdf.ln(2)
        
        # Aquí separamos las 15 mediciones para que salgan una debajo de otra
        if "|" in desc_full:
            partes = desc_full.split(" | ")
            pdf.set_font("Arial", '', 9) 
            for p in partes:
                # Usamos cell para cada línea para que quede como una lista prolija
                pdf.cell(0, 6, f" > {p.strip()}", border='LR', ln=1)
            pdf.cell(0, 0, "", border='T', ln=1) # Línea de cierre inferior
        else:
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)

        # --- SECCIÓN DE OBSERVACIONES ---
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, " OBSERVACIONES FINALIZADAS:", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, f"\n{datos.get('Taller_Externo','-')}\n", border=1)

        # Pie de página
        pdf.set_y(-25)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 10, f"Informe generado por Sistema Marpi - Equipo: {tag_motor}", 0, 0, 'C')
        
        return pdf.output(dest='S').encode('latin-1', 'replace')
        
    except Exception as e:
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
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("💾 GUARDAR"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Responsable": resp, "Descripcion": f"LUBRICACIÓN: {det}"}
            conn.update(data=pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True))
            
            # LIMPIEZA DE CAMPOS
            st.session_state.tag_fijo = ""
            st.success("✅ Lubricación registrada")
            st.rerun()
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

        btn_guardar = st.form_submit_button("💾 GUARDAR MEDICIONES")

        if btn_guardar:
            if t and resp:
                # AQUÍ ESTÁ EL CAMBIO: Juntamos las 15 variables en el detalle
                detalle = (
                    f"A TIERRA: T-V1:{tv1}, T-U1:{tu1}, T-W1:{tw1} | "
                    f"ENTRE BOBINAS: W1-V1:{wv1}, W1-U1:{wu1}, V1-U1:{vu1} | "
                    f"INTERNAS: U1-U2:{u1u2}, V1-V2:{v1v2}, W1-W2:{w1w2} | "
                    f"LINEA A TIERRA: T-L1:{tl1}, T-L2:{tl2}, T-L3:{tl3} | "
                    f"LINEA A LINEA: L1-L2:{l1l2}, L1-L3:{l1l3}, L2-L3:{l2l3}"
                )
                
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": t,
                    "Responsable": resp,
                    "Descripcion": detalle,
                    "Taller_Externo": f"N/S: {sn}. Mediciones completas cargadas desde App."
                }
                
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                
                st.session_state.tag_fijo = "" 
                st.session_state.cnt_meg += 1 
                st.success(f"✅ Guardado con éxito")
                st.rerun()
            else:
                st.error("⚠️ Falta completar TAG o Técnico")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")


























































































































































































































































































































