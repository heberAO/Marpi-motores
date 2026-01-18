import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF
import base64

def generar_pdf(datos, tag_motor):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Logo (opcional)
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 30)
            
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, 'INFORME TÉCNICO MARPI', 0, 1, 'R')
        pdf.ln(10)
        
        # Datos del Equipo
        pdf.set_fill_color(230, 233, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DETALLES DEL MOTOR: {tag_motor}", 1, 1, 'L', True)
        
        pdf.set_font("Arial", '', 10)
        # Aquí usamos datos.get porque 'datos' ahora será un diccionario de la fila
        texto_linea1 = f"Fecha: {datos.get('Fecha','-')} | Técnico: {datos.get('Responsable','-')}"
        pdf.cell(0, 8, texto_linea1, 1, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DESCRIPCIÓN DE LA TAREA:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "ESTADO / OBSERVACIONES:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Taller_Externo','-')), border=1)

        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error en PDF: {e}")
        return None

# --- 1. CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="Marpi Motores", layout="wide")

if "form_count" not in st.session_state:
    st.session_state.form_count = 0
if "mostrar_form" not in st.session_state:
    st.session_state.mostrar_form = False

def activar_formulario():
    st.session_state.mostrar_form = True

# --- 2. LÓGICA DE ESCANEO QR ---
query_params = st.query_params
query_tag = query_params.get("tag", "")
default_index = 1 if query_tag else 0

# --- 3. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    df_completo = pd.DataFrame()

# --- 4. INTERFAZ: MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    st.divider()
    # Nombres simplificados para evitar errores de tildes o emojis
    modo = st.radio(
        "SELECCIONE UNA FUNCIÓN:",
        ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"],
        index=default_index
    )

# --- 5. FUNCIÓN GENERAR PDF ---
def generar_pdf(df_historial, tag_motor):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 30)
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, 'INFORME TECNICO DE MOTORES', 0, 1, 'R')
        pdf.ln(10)
        # Resumen rápido
        fijos = df_historial.iloc[0]
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f" DATOS DEL EQUIPO: {fijos['Tag']}", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, f"Potencia: {fijos.get('Potencia','-')} | RPM: {fijos.get('RPM','-')} | Serie: {fijos.get('N_Serie','-')}", 1, 1)
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error en PDF: {e}")
        return None

# --- 6. CAJONES DE NAVEGACIÓN ---

if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial de Motor")
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    
    with st.form(key=f"alta_motor_{st.session_state.form_count}"):
        col_id1, col_id2, col_id3, col_id4, col_id5 = st.columns(5)
        t = col_id1.text_input("TAG/ID MOTOR").upper()
        p = col_id2.text_input("Potencia (HP/kW)")
        r = col_id3.selectbox("RPM", ["-", "750", "1500", "3000"])
        f = col_id4.text_input("Frame / Carcasa")
        sn = col_id5.text_input("N° de Serie")
        
        st.subheader("🔍 Mediciones Iniciales")
        m1, m2, m3 = st.columns(3)
        with m1:
            rt_tu, rt_tv, rt_tw = st.text_input("T-U"), st.text_input("T-V"), st.text_input("T-W")
        with m2:
            rb_uv, rb_vw, rb_uw = st.text_input("U-V"), st.text_input("V-W"), st.text_input("U-W")
        with m3:
            ri_u, ri_v, ri_w = st.text_input("U1-U2"), st.text_input("V1-V2"), st.text_input("W1-W2")
            
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción inicial / Trabajos")
        ext = st.text_area("Trabajos Externos")
        
        if st.form_submit_button("💾 GUARDAR EN BASE DE DATOS"):
            if t and resp:
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f,
                    "N_Serie": sn, "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext,
                    "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw,
                    "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                    "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"✅ Motor {t} guardado correctamente.")
                st.session_state.form_count += 1
                st.rerun()
            else:
                st.error("⚠️ Tag y Técnico son obligatorios.")

elif modo == "Historial y QR":
    st.title("🔍 Consulta de Motor y QR")
    
    # --- PASO 1: RE-CARGAR LAS BASES PARA EVITAR EL ERROR ---
    try:
        # Aquí usamos los nombres de las hojas de tu Google Sheets
        # Asegúrate de que coincidan con los nombres de tus pestañas en el Excel
        base_motores = conn.read(worksheet="Motores", ttl=0) # O "Recepcion"
        movimientos = conn.read(worksheet="Movimientos", ttl=0) # O "Historial"
    except Exception as e:
        st.error(f"Error al conectar con las planillas: {e}")
        st.stop()

    # --- PASO 2: BUSCADOR ---
    if not base_motores.empty:
        lista_tags = [""] + list(base_motores['Tag'].unique())
        motor_buscado = st.selectbox("Seleccioná un Motor para ver su historial:", lista_tags)
        
        if motor_buscado != "":
            # Extraemos los datos de la ficha técnica
            fijos = base_motores[base_motores['Tag'] == motor_buscado].iloc[0]
            
            st.success(f"✅ Motor localizado: {motor_buscado}")
            
            # Panel de información rápida
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Potencia", fijos.get('Potencia', '-'))
            with col2:
                st.metric("N° Serie", fijos.get('N_Serie', '-'))
            with col3:
                st.metric("Ubicación", fijos.get('Ubicacion', '-'))

            st.divider()

            # --- PASO 3: MOSTRAR INTERVENCIONES ---
            st.subheader("📜 Historial de Intervenciones")
            
            # Filtramos en la tabla de movimientos
            historial = movimientos[movimientos['Tag'] == motor_buscado].copy()

            if not historial.empty:
                # Intentamos ordenar por fecha
                historial['Fecha_DT'] = pd.to_datetime(historial['Fecha'], dayfirst=True, errors='coerce')
                historial = historial.sort_values(by='Fecha_DT', ascending=False)

                for index, fila in historial.iterrows():
                    with st.expander(f"📅 {fila['Fecha']} - {fila['Responsable']}", expanded=False):
                        c_inf, c_btn = st.columns([3, 1])
                        with c_inf:
                            st.write(f"**Detalle:** {fila['Descripcion']}")
                            st.write(f"**Estado/Obs:** {fila.get('Taller_Externo', '-')}")
                        with c_btn:
                            # Generamos el PDF usando tu función corregida
                            pdf_bytes = generar_pdf(fila.to_dict(), motor_buscado)
                            if pdf_bytes:
                                st.download_button(
                                    label="📥 PDF",
                                    data=pdf_bytes,
                                    file_name=f"Reporte_{motor_buscado}_{index}.pdf",
                                    mime="application/pdf",
                                    key=f"qr_btn_{index}"
                                )
            else:
                st.info("Este motor no tiene registros de megado o engrase todavía.")
    else:
        st.warning("La base de datos de motores está vacía.")
elif modo == "Relubricacion":
    # PASO A: El limpiador debe estar aquí, bien pegado al borde del 'elif'
    if "count_relub" not in st.session_state:
        st.session_state.count_relub = 0

    st.title("🛢️ Gestión de Relubricación")
    
    tab1, tab2 = st.tabs(["➕ Registrar Nuevo Engrase", "📋 Ver Historial"])
    
    with tab1:
        # PASO B: La key dinámica usando el contador
        with st.form(key=f"form_engrase_{st.session_state.count_relub}"):
            st.subheader("Datos del Trabajo")
            c1, c2 = st.columns(2)
            with c1:
                tag_relub = st.text_input("TAG DEL MOTOR").upper()
                resp_relub = st.text_input("Responsable")
            with c2:
                fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
                sn_relub = st.text_input("N° de Serie")

            st.divider()
            col_la, col_loa = st.columns(2)
            with col_la:
                st.markdown("**Lado Acople (LA)**")
                rod_la = st.text_input("Rodamiento LA")
                gr_la = st.text_input("Gramos LA")
            with col_loa:
                st.markdown("**Lado Opuesto (LOA)**")
                rod_loa = st.text_input("Rodamiento LOA")
                gr_loa = st.text_input("Gramos LOA")

            grasa = st.selectbox("Grasa Utilizada", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
            obs = st.text_area("Notas / Observaciones")
            
            btn_guardar = st.form_submit_button("💾 GUARDAR REGISTRO")

            if btn_guardar:
                if tag_relub and resp_relub:
                    # Armamos la fila
                    nueva_relub = {
                        "Fecha": f_relub.strftime("%d/%m/%Y"),
                        "Tag": tag_relub,
                        "N_Serie": sn_relub,
                        "Responsable": resp_relub,
                        "Descripcion": f"RELUBRICACIÓN: LA: {rod_la} ({gr_la}g) - LOA: {rod_loa} ({gr_loa}g)",
                        "Taller_Externo": f"Grasa: {grasa}. {obs}"
                    }
                    
                    # Guardamos
                    df_final = pd.concat([df_completo, pd.DataFrame([nueva_relub])], ignore_index=True)
                    conn.update(data=df_final)
                    
                    # PASO C: Sumamos 1 al contador para que el próximo formulario esté vacío
                    st.session_state.count_relub += 1
                    st.success(f"✅ ¡Engrase de {tag_relub} guardado y formulario limpio!")
                    st.balloons()
                    st.rerun() # Esto hace que la limpieza sea instantánea
                else:
                    st.error("⚠️ El TAG y el Responsable son obligatorios.")

    with tab2:
        
        st.subheader("🔍 Buscador de Lubricación")
        if not df_completo.empty:
            df_lub = df_completo[df_completo['Descripcion'].str.contains("RELUBRICACIÓN", na=False)].copy()
            busqueda_lub = st.text_input("Filtrar por TAG o SERIE:", key="search_lub").strip().upper()
            
            if busqueda_lub:
                cond_t = df_lub['Tag'].astype(str).str.upper().str.contains(busqueda_lub, na=False)
                cond_s = df_lub['N_Serie'].astype(str).str.upper().str.contains(busqueda_lub, na=False)
                df_lub = df_lub[cond_t | cond_s]

                st.dataframe(
                    df_engrase,
                    column_config={
                        "Fecha": st.column_config.DateColumn("📅 Fecha", format="DD/MM/YYYY"),
                        "Tag": st.column_config.TextColumn("🏷️ TAG"),
                        "Gramos_LA": st.column_config.TextColumn("⚖️ Gr. LA"),
                        "Gramos_LOA": st.column_config.TextColumn("⚖️ Gr. LOA"),
                        "Tipo_Grasa": st.column_config.TextColumn("🛢️ Grasa Usada")
                    },
                    hide_index=True
                )
            if not df_lub.empty:
                # Ordenar por fecha (más reciente arriba)
                df_lub['Fecha_dt'] = pd.to_datetime(df_lub['Fecha'], format='%d/%m/%Y', errors='coerce')
                df_lub = df_lub.sort_values(by='Fecha_dt', ascending=False)
                
                # Tabla limpia
                st.write(f"Mostrando {len(df_lub)} registros encontrados:")
                st.dataframe(
                    df_lub[['Fecha', 'Tag', 'Responsable', 'Descripcion']], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning(f"No se encontraron registros de engrase para: '{busqueda_lub}'")
        else:
            st.info("La base de datos está vacía.")

elif modo == "Mediciones de Campo":
    if "count_campo" not in st.session_state:
        st.session_state.count_campo = 0

    st.title("⚡ Mediciones de Aislamiento en Campo")
    st.info("Registrá los valores de Megado del motor y su línea de alimentación.")

    tab_reg, tab_hist = st.tabs(["📝 Registrar Medición", "📊 Historial de Megado"])

    with tab_reg:
        with st.form(key=f"form_campo_{st.session_state.count_campo}"):
            c1, c2 = st.columns(2)
            with c1:
                tag_campo = st.text_input("TAG DEL MOTOR", value=st.session_state.get('tag_seleccionado', '')).upper()
                sn_campo = st.text_input("N° DE SERIE", value=st.session_state.get('serie_seleccionada', ''))
            with c2:
                fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
                tecnico = st.text_input("Técnico / Responsable")

            st.divider()
            c_volt, c_est, c_equi = st.columns(3)
            with c_volt:
                voltaje = st.selectbox("Voltaje de Prueba", ["500V", "1000V", "2500V", "5000V"])
            with c_est:
                estado = st.selectbox("Estado de la Instalación", ["APTO PARA OPERAR", "RIESGO DE FALLA", "NO APTO"])
            with c_equi: 
                equi = st.selectbox("Equipo de Medición", ["FLUKE 1507", "KYORITSU 3005A", "OTRO"])

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🟢 Aislamiento Motor")
                m1, m2, m3 = st.columns(3)
                with m1:
                    rt_tu, rt_tv, rt_tw = st.text_input("T-U"), st.text_input("T-V"), st.text_input("T-W")
                with m2:
                    rb_uv, rb_vw, rb_uw = st.text_input("U-V"), st.text_input("V-W"), st.text_input("U-W")
                with m3:
                    ri_u, ri_v, ri_w = st.text_input("U1-U2"), st.text_input("V1-V2"), st.text_input("W1-W2")

            with col2:
                st.markdown("### 🔵 Aislamiento Línea")
                ml1, ml2 = st.columns(2)
                with ml1:
                    rt_tl1, rt_tl2, rt_tl3 = st.text_input("T-L1"), st.text_input("T-L2"), st.text_input("T-L3")
                with ml2:
                    rl_l1l2, rl_l1l3, rl_l2l3 = st.text_input("L1-L2"), st.text_input("L1-L3"), st.text_input("L2-L3")

            obs_campo = st.text_area("Observaciones del Entorno")
            
            # --- EL BOTÓN DEBE ESTAR DENTRO DEL FORM ---
            btn_campo = st.form_submit_button("💾 GUARDAR MEDICIÓN COMPLETA")

            if btn_campo:
                if tag_campo and tecnico:
                    detalle = (f"MEGADO: {equi} ({voltaje}). "
                               f"Mot:[T:{rt_tu}/{rt_tv}/{rt_tw} | F:{rb_uv}/{rb_vw}/{rb_uw} | B:{ri_u}/{ri_v}/{ri_w}] "
                               f"Lin:[T:{rt_tl1}/{rt_tl2}/{rt_tl3} | F:{rl_l1l2}/{rl_l1l3}/{rl_l2l3}]")
                    
                    nueva_med = {
                        "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                        "Tag": tag_campo,
                        "N_Serie": sn_campo,
                        "Responsable": tecnico,
                        "Descripcion": detalle,
                        "Taller_Externo": f"ESTADO: {estado}. Obs: {obs_campo}"
                    }
                    df_final = pd.concat([df_completo, pd.DataFrame([nueva_med])], ignore_index=True)
                    conn.update(data=df_final)
                    st.session_state.count_campo += 1
                    st.success("✅ Medición guardada correctamente.")
                    
                    pdf_bytes = generar_pdf_mantenimiento("Megado en Campo", nueva_med)
                    
                    st.download_button(
                        label="📥 Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"Megado_{tag_campo}_{fecha_hoy}.pdf",
                        mime="application/pdf"
                    )
                    st.info("👆 Descargá el reporte antes de realizar otra carga.")
                else:
                    st.error("⚠️ Tag y Responsable son obligatorios.")

    with tab_hist:
        st.subheader("📋 Registro Técnico de Campo")
        if not df_completo.empty:
            # Filtramos solo lo que es Megado
            df_m = df_completo[df_completo['Descripcion'].str.contains("MEGADO", na=False)].copy()
            
            # Buscador por TAG o por Responsable
            c_busc1, c_busc2 = st.columns(2)
            with c_busc1:
                busc_tag = st.text_input("🔍 Buscar por TAG:", key="b_tag").strip().upper()
            with c_busc2:
                busc_resp = st.text_input("👤 Buscar por Responsable:", key="b_resp")

            # Aplicar filtros
            if busc_tag:
                df_m = df_m[df_m['Tag'].astype(str).str.contains(busc_tag, na=False)]
            if busc_resp:
                df_m = df_m[df_m['Responsable'].astype(str).str.contains(busc_resp, case=False, na=False)]

            # VISTA MEJORADA CON COLORES
            st.dataframe(
                df_m[['Fecha', 'Tag', 'N_Serie', 'Responsable', 'Descripcion', 'Taller_Externo']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Fecha": st.column_config.TextColumn("📅 Fecha"),
                    "Tag": st.column_config.TextColumn("🏷️ Tag"),
                    "N_Serie": st.column_config.TextColumn("🔢 Serie"),
                    "Responsable": st.column_config.TextColumn("👤 Técnico"),
                    "Descripcion": st.column_config.TextColumn("⚡ Detalle de Fases"),
                    "Taller_Externo": st.column_config.TextColumn("🚩 Estado/Obs")
                }
            )
        else:
            st.warning("Aún no hay mediciones registradas.")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")














































































































































































































































































