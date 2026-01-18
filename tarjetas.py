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
        
        st.subheader("🔍 Mediciones Iniciales")
        m1, m2, m3 = st.columns(3)
        with m1: rt_tu, rt_tv, rt_tw = st.text_input("T-U"), st.text_input("T-V"), st.text_input("T-W")
        with m2: rb_uv, rb_vw, rb_uw = st.text_input("U-V"), st.text_input("V-W"), st.text_input("U-W")
        with m3: ri_u, ri_v, ri_w = st.text_input("U1-U2"), st.text_input("V1-V2"), st.text_input("W1-W2")
        
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción Inicial")
        ext = st.text_area("Trabajos Externos")
        
        if st.form_submit_button("💾 GUARDAR ALTA"):
            if t and resp:
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f, "N_Serie": sn,
                    "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext,
                    "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw, "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                    "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"✅ Guardado {t}"); st.rerun()

elif modo == "Historial y QR":
    st.title("🔍 Historial y QR")
    
    # 1. DETECCIÓN AUTOMÁTICA DE PARÁMETROS (Para el escaneo)
    query_tag = st.query_params.get("tag", "")

    if not df_completo.empty:
        # Limpieza de lista de TAGs para evitar errores de ordenamiento
        tags_sucios = df_completo['Tag'].dropna().unique()
        lista_tags = [""] + sorted([str(t).strip().upper() for t in tags_sucios if str(t).strip() != ""])
        
        # Si el QR envió un TAG, lo buscamos en la lista
        indice_defecto = 0
        if query_tag and query_tag in lista_tags:
            indice_defecto = lista_tags.index(query_tag)
            st.success(f"Motor detectado por QR: {query_tag}")
        
        # El selectbox ahora se posiciona solo si viene del QR
        buscado = st.selectbox("Seleccioná un Motor:", lista_tags, index=indice_defecto)
        
        if buscado:
            st.session_state.tag_fijo = buscado 
            
            # --- GENERADOR DE QR ---
            url_real = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/" 
            url_final = f"{url_real}?tag={urllib.parse.quote(buscado)}"
            
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(url_final)}"
            
            col_qr, col_info = st.columns([1, 2])
            with col_qr:
                st.image(qr_api, caption=f"QR de {buscado}")
            with col_info:
                st.subheader(f"🚜 Equipo: {buscado}")
                st.info("Al escanear este código con un celular, se abrirá directamente el historial de este motor.")
                st.download_button("📥 Descargar QR", qr_api, file_name=f"QR_{buscado}.png")
            
            st.divider()

            # --- LISTADO HISTÓRICO ---
            hist_m = df_completo[df_completo['Tag'] == buscado].copy()
            # Ordenar fechas (de más reciente a más antigua)
            hist_m['Fecha_dt'] = pd.to_datetime(hist_m['Fecha'], dayfirst=True, errors='coerce')
            hist_m = hist_m.sort_values(by='Fecha_dt', ascending=False)

            for idx, fila in hist_m.iterrows():
                with st.expander(f"📅 {fila.get('Fecha','-')} - {fila.get('Responsable','-')}"):
                    c_txt, c_pdf = st.columns([3, 1])
                    with c_txt:
                        st.write(f"**Actividad:** {fila.get('Descripcion','-')}")
                        st.write(f"**Observaciones:** {fila.get('Taller_Externo','-')}")
                    with c_pdf:
                        pdf_b = generar_pdf_reporte(fila.to_dict(), buscado)
                        if pdf_b:
                            st.download_button("📄 PDF", pdf_b, f"Informe_{buscado}_{idx}.pdf", key=f"btn_h_{idx}")
    else:
        st.warning("La base de datos está vacía.")

elif modo == "Relubricacion":
    st.title("🛢️ Gestión de Relubricación")
    with st.form("relub"):
        t_r = st.text_input("TAG DEL MOTOR", value=st.session_state.tag_fijo).upper()
        sn_r = st.text_input("N° de Serie")
        resp_r = st.text_input("Responsable")
        c1, c2 = st.columns(2)
        rod_la = c1.text_input("Rodamiento LA")
        gr_la = c1.text_input("Gramos LA")
        rod_loa = c2.text_input("Rodamiento LOA")
        gr_loa = c2.text_input("Gramos LOA")
        grasa = st.selectbox("Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("💾 GUARDAR ENGRASE"):
            nueva = {
                "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_r, "N_Serie": sn_r, "Responsable": resp_r,
                "Descripcion": f"RELUBRICACIÓN: LA: {rod_la} ({gr_la}g) - LOA: {rod_loa} ({gr_loa}g)",
                "Taller_Externo": f"Grasa: {grasa}. {obs}"
            }
            df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_final)
            st.success("✅ Guardado")

elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo")
    with st.form("campo"):
        t_c = st.text_input("TAG MOTOR", value=st.session_state.tag_fijo).upper()
        sn_c = st.text_input("N° SERIE")
        resp_c = st.text_input("Técnico")
        volt = st.selectbox("Voltaje", ["500V", "1000V", "2500V"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🟢 Motor")
            rt_tu, rt_tv, rt_tw = st.text_input("T-U "), st.text_input("T-V "), st.text_input("T-W ")
        with col2:
            st.markdown("### 🔵 Línea")
            rl1, rl2, rl3 = st.text_input("T-L1"), st.text_input("T-L2"), st.text_input("T-L3")
        
        if st.form_submit_button("💾 GUARDAR MEGADO"):
            detalle = f"MEGADO {volt}. Mot:[T:{rt_tu}/{rt_tv}/{rt_tw}] - Lin:[T:{rl1}/{rl2}/{rl3}]"
            nueva = {
                "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_c, "N_Serie": sn_c, "Responsable": resp_c,
                "Descripcion": detalle, "Taller_Externo": "Medición en campo"
            }
            df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_final)
            st.success("✅ Guardado")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")



























































































































































































































































































