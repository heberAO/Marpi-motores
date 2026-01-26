import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
import re
import time
from io import BytesIO
from fpdf import FPDF

def calcular_grasa_avanzado(rodamiento):
    """Calcula gramos sugeridos según el modelo de rodamiento"""
    if not rodamiento or pd.isna(rodamiento):
        return 0
    try:
        # Extraer el diámetro exterior (D) del código del rodamiento (ej: 6314 -> 14)
        # Esta es una fórmula simplificada: Gramos = D * Ancho * 0.005
        # Para hacerlo simple, si es un rodamiento común:
        modelo = str(rodamiento)
        if "63" in modelo:
            return 20  # Valor base ejemplo
        elif "62" in modelo:
            return 15
        return 10 # Default
    except:
        return 0

fecha_hoy = date.today()

if 'pdf_listo' not in st.session_state:
    st.session_state.pdf_listo = None

def generar_pdf_reporte(datos, buscado):
    try:
        from fpdf import FPDF
        import io

        pdf = FPDF()
        pdf.add_page()
        
        # --- Encabezado Marpi ---
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"REPORTE TÉCNICO: {buscado}", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"Generado desde App Marpi Motores", ln=True, align='C')
        pdf.ln(10)

        # --- Información del Motor ---
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, " DATOS DEL EQUIPO", ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        
        # Usamos tus columnas: Potencia, Tension, RPM, N_Serie
        pdf.cell(95, 10, f"Potencia: {datos.get('Potencia', 'S/D')}")
        pdf.cell(95, 10, f"Tensión: {datos.get('Tension', 'S/D')}", ln=True)
        pdf.cell(95, 10, f"RPM: {datos.get('RPM', 'S/D')}")
        pdf.cell(95, 10, f"N° Serie: {datos.get('N_Serie', 'S/D')}", ln=True)
        pdf.ln(5)

        # --- Datos de la Intervención ---
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, " DETALLE DE LA TAREA", ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        
        # Usamos: Fecha, Tipo_Tarea, Responsable
        pdf.cell(95, 10, f"Fecha: {datos.get('Fecha', 'S/D')}")
        pdf.cell(95, 10, f"Tarea: {datos.get('Tipo_Tarea', 'S/D')}", ln=True)
        pdf.cell(0, 10, f"Responsable: {datos.get('Responsable', 'S/D')}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, "Descripción y Observaciones:", ln=True)
        pdf.set_font("Arial", '', 10)
        # Usamos 'Descripcion' (sin acento) y 'Observaciones'
        texto_desc = f"{datos.get('Descripcion', '')} \n{datos.get('Observaciones', '')}"
        pdf.multi_cell(0, 7, texto_desc)

        # --- Rodamientos y Lubricación ---
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, " RODAMIENTOS Y LUBRICACIÓN", ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(95, 10, f"Rod. LA: {datos.get('Rodamiento_LA', 'S/D')}")
        pdf.cell(95, 10, f"Rod. LOA: {datos.get('Rodamiento_LOA', 'S/D')}", ln=True)
        pdf.cell(0, 10, f"Grasa: {datos.get('Tipo_Grasa', 'S/D')} ({datos.get('Gramos_LA','0')}g / {datos.get('Gramos_LOA','0')}g)", ln=True)

        # Generar salida
        return pdf.output(dest='S').encode('latin-1', 'replace')

    except Exception as e:
        print(f"Error en PDF: {e}")
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

# --- 6. VALIDACIÓN DE CONTRASEÑA (VERSIÓN CORREGIDA) ---
if modo in ["Nuevo Registro", "Relubricacion", "Mediciones de Campo"]:
    if "autorizado" not in st.session_state:
        st.session_state.autorizado = False

    if not st.session_state.autorizado:
        st.title("🔒 Acceso Restringido")
        st.info("Esta sección es solo para personal de MARPI.")
        
        # Usamos un formulario para que el botón funcione mejor
        with st.form("login_marpi"):
            clave = st.text_input("Contraseña:", type="password")
            btn_entrar = st.form_submit_button("Validar Ingreso")
            
            if btn_entrar:
                if clave == "MARPI2026":
                    st.session_state.autorizado = True
                    st.success("✅ Acceso concedido")
                    st.rerun()
                else:
                    st.error("⚠️ Clave incorrecta")
        
        st.stop() # Detiene la ejecución para que no se vea el resto

# --- 5. SECCIONES (CON TUS CAMPOS ORIGINALES) ---
if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    with st.form(key=f"alta_motor_{st.session_state.form_key}"):
        # --- CAMPOS DE ENTRADA (Mismo diseño anterior) ---
        c1, c2, c3 = st.columns([2, 2, 1])
        t = c1.text_input("TAG/ID MOTOR").upper()
        sn = c2.text_input("N° de Serie").upper()
        resp = c3.text_input("Responsable")

        c4, c5, c6, c7, c8 = st.columns(5)
        p, v, cor = c4.text_input("Potencia"), c5.text_input("Tensión"), c6.text_input("Corriente")
        r = c7.selectbox("RPM", ["-", "750", "1000", "1500", "3000"])
        carc = c8.text_input("Carcasa/Frame")

        st.subheader("⚙️ Rodamientos de Placa")
        r1, r2 = st.columns(2)
        r_la, r_loa = r1.text_input("Rodamiento LA").upper(), r2.text_input("Rodamiento LOA").upper()
        # Dentro del formulario de Reparación
        tipo_rodamiento = st.selectbox(
            "Tipo de rodamientos instalados:",["Abierto (Sin sellos)","RS Sello de un solo lado", "2RS (Sello Caucho Sintetico - Hermético)", "ZZ (Blindaje Metálico)"])    

        st.subheader("⚡ Mediciones Eléctricas")
        m1, m2, m3 = st.columns(3)
        with m1: v_rt_tu, v_rt_tv, v_rt_tw = st.text_input("RT_TU"), st.text_input("RT_TV"), st.text_input("RT_TW")
        with m2: v_rb_uv, v_rb_vw, v_rb_uw = st.text_input("RB_UV"), st.text_input("RB_VW"), st.text_input("RB_UW")
        with m3: v_ri_u, v_ri_v, v_ri_w = st.text_input("RI_U"), st.text_input("RI_V"), st.text_input("RI_W")

        desc = st.text_area("Descripción")
        ext = st.text_area("Trabajos Taller Externo")
        
        btn_guardar = st.form_submit_button("💾 GUARDAR Y GENERAR PDF")

    if btn_guardar:
            if t and resp:
                # Armamos el diccionario con ABSOLUTAMENTE TODO
                if btn_guardar:
                    if t and resp:
                        nueva = {
                            "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                            "Tag": t,
                            "N_Serie": sn,
                            "Responsable": resp,
                            "Potencia": p, "Tension": v, "Corriente": cor,
                            "RPM": r, "Carcasa": carc,
                            "Rodamiento_LA": r_la, "Rodamiento_LOA": r_loa,
                            
                            # --- LAS 9 MEDICIONES DE ALTA ---
                            "RT_TU": v_rt_tu, "RT_TV": v_rt_tv, "RT_TW": v_rt_tw, # Tierra
                            "RB_UV": v_rb_uv, "RB_VW": v_rb_vw, "RB_UW": v_rb_uw, # Entre bobinas
                            "RI_U": v_ri_u, "RI_V": v_ri_v, "RI_W": v_ri_w,      # Resistencias
                            
                            "Descripcion": desc,
                            "Trabajos_Externos": ext
                        }
                
                # Guardar y generar...
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                st.session_state.pdf_buffer = generar_pdf_reporte(nueva, "PROTOCOLO DE ALTA Y REGISTRO")
                st.session_state.tag_actual = t
                st.session_state.form_key += 1
                
                if t and resp:  # Este es tu IF principal
            # ..# Guardar y generar...
                    df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                    conn.update(data=df_final)
                    st.session_state.pdf_buffer = generar_pdf_reporte(nueva, "PROTOCOLO DE ALTA Y REGISTRO")
                    st.session_state.tag_actual = t
                    st.session_state.form_key += 1.
                    st.success(f"✅ Motor {t} registrado con éxito.")
            
            # --- EFECTO DE ÉXITO CON LOGO DE MARPI ---
                    placeholder = st.empty() 
                    with placeholder.container():
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image("logo.png", use_container_width=True)
                            st.markdown("<h2 style='text-align: center; color: #007BFF;'>¡Registro Guardado en Marpi!</h2>", unsafe_allow_html=True)
                
                        st.balloons()
                        time.sleep(3)
                        placeholder.empty()
                    
                    # El rerun va afuera del placeholder pero adentro del IF
                    st.rerun()

                else:
                    st.error("⚠️ El TAG y el Responsable son obligatorios.")
  
elif modo == "Historial y QR":
    st.title("🔍 Consulta y Gestión de Motores")
    
    if not df_completo.empty:
        # 1. Preparamos la lista de búsqueda
        df_completo['Busqueda_Combo'] = (
            df_completo['Tag'].astype(str) + " | SN: " + df_completo['N_Serie'].astype(str)
        )
        opciones = [""] + sorted(df_completo['Busqueda_Combo'].unique().tolist())
        
        # 2. Detección automática por QR (lectura de URL)
        query_tag = st.query_params.get("tag", "").upper()
        idx_q = 0
        if query_tag:
            for i, op in enumerate(opciones):
                if op.startswith(query_tag + " |"):
                    idx_q = i
                    break
        
        seleccion = st.selectbox("Busca por TAG o N° de Serie:", opciones, index=idx_q)

        # Inicializamos variables para que la App no explote si no hay selección
        buscado = "" 
        historial_motor = pd.DataFrame()

        if seleccion:
            # Extraemos el TAG y filtramos los datos
            buscado = seleccion.split(" | ")[0].strip()
            st.session_state.tag_fijo = buscado
            historial_motor = df_completo[df_completo['Tag'] == buscado].copy()

            # --- PANEL SUPERIOR: QR Y DATOS DEL MOTOR ---
            with st.container(border=True):
                col_qr, col_info = st.columns([1, 2])
                url_app = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?tag={buscado}"
                qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url_app}"
                
                with col_qr:
                    st.image(qr_api, width=150)
                with col_info:
                    st.subheader(f"🚜 {buscado}")
                    st.caption(f"Número de Serie: {seleccion.split('SN: ')[1] if 'SN: ' in seleccion else 'S/D'}")
                    st.info(f"Link: {url_app}")

            # --- BOTONES DE ACCIÓN (Optimizado para Celular) ---
            st.subheader("➕ Cargar Nueva Tarea")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🛠️ Reparar", use_container_width=True):
                    st.session_state.seleccion_manual = "Nuevo Registro"
                    st.rerun()
            with c2:
                if st.button("🛢️ Engrasar", use_container_width=True):
                    st.session_state.seleccion_manual = "Relubricacion"
                    st.rerun()
            with c3:
                if st.button("⚡ Megar", use_container_width=True):
                    st.session_state.seleccion_manual = "Mediciones de Campo"
                    st.rerun()

            st.divider()
            # --- HISTORIAL (Vista de Acordeón para Celular) ---
        st.subheader("📜 Historial de Intervenciones")
        if not historial_motor.empty:
            # Mostramos lo más nuevo primero
            hist_m = historial_motor.iloc[::-1] 

            for idx, fila in hist_m.iterrows():
                # Usamos tus nombres: Fecha y Tipo_Tarea
                fecha = fila.get('Fecha','-')
                tarea = fila.get('Tipo_Tarea', 'General')
                responsable = fila.get('Responsable', 'S/D')
                # Usamos Descripcion (sin acento como en tu lista)
                desc_completa = str(fila.get('Descripcion', '-'))
                desc_corta = desc_completa[:30]
                
                with st.expander(f"📅 {fecha} - {tarea} ({desc_corta}...)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**👤 Responsable:** {responsable}")
                        st.write(f"**🏷️ Tag:** {fila.get('Tag','-')}")
                    with col2:
                        st.write(f"**⚙️ Rod. LA:** {fila.get('Rodamiento_LA','-')}")
                        st.write(f"**⚙️ Rod. LOA:** {fila.get('Rodamiento_LOA','-')}")

                    st.write(f"**📝 Descripción:** {desc_completa}")
                    st.write(f"**🗒️ Notas:** {fila.get('notas','-')}")
                    
                    if str(fila.get('Tipo_Grasa')) != 'nan':
                        st.write(f"🧪 **Grasa:** {fila.get('Tipo_Grasa')} ({fila.get('Gramos_LA', '0')}g / {fila.get('Gramos_LOA', '0')}g)")

                    # --- BOTÓN PARA EL PDF ---
                    try:
                        # Le pasamos la fila completa a la función del PDF
                        pdf_archivo = generar_pdf_reporte(fila.to_dict(), buscado)
                        if pdf_archivo:
                            st.download_button(
                                label="📄 Descargar Informe PDF",
                                data=pdf_archivo,
                                file_name=f"Reporte_{buscado}_{fecha}.pdf",
                                key=f"pdf_{idx}",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error("No se pudo generar el PDF.")
        else:
            st.warning("No hay intervenciones registradas para este motor.")

elif modo == "Relubricacion":
    st.title("🛢️ Lubricación Inteligente MARPI")
    
    if "cnt_lub" not in st.session_state:
        st.session_state.cnt_lub = 0
    # 1. Asegurar que la variable exista
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    df_lista = df_completo.copy()
    
    # 2. Buscador Simple por TAG
    # Limpiamos la lista de Tags para que no haya errores
    lista_tags = sorted([str(x) for x in df_lista['Tag'].unique() if str(x) not in ['nan', 'None', '']])
    
    tag_seleccionado = st.selectbox(
        "Seleccione el TAG del Motor", 
        options=[""] + lista_tags,
        key=f"busqueda_{st.session_state.form_id}"
    )
    # --- LÓGICA DE AVISO DE RODAMIENTOS (Rodamiento_LA y Rodamiento_LOA) ---
    if tag_seleccionado != "":
        # Extraemos la fila del motor
        info_motor = df_lista[df_lista['Tag'] == tag_seleccionado].iloc[0]
        
        # Leemos los valores y los pasamos a mayúsculas para no fallar en la comparación
        rod_la = str(info_motor.get('Rodamiento_LA', 'NO DEFINIDO')).upper()
        rod_loa = str(info_motor.get('Rodamiento_LOA', 'NO DEFINIDO')).upper()

        st.markdown("---")
        st.markdown(f"### ⚙️ Configuración de Rodamientos")
        
        # Mostramos los datos actuales al técnico
        col_la, col_loa = st.columns(2)
        col_la.metric("Lado Acople (LA)", rod_la)
        col_loa.metric("Lado Opuesto (LOA)", rod_loa)

        # Analizamos si alguno es sellado (2RS o ZZ)
        es_sellado_la = any(x in rod_la for x in ["2RS", "ZZ"])
        es_sellado_loa = any(x in rod_loa for x in ["2RS", "ZZ"])

        if es_sellado_la or es_sellado_loa:
            st.error("🚫 **AVISO DE SEGURIDAD: NO LUBRICAR**")
            if es_sellado_la and es_sellado_loa:
                st.write("Ambos rodamientos son **sellados de por vida**. Intentar lubricarlos puede dañar los sellos.")
            else:
                st.write(f"Al menos uno de los rodamientos ({rod_la if es_sellado_la else rod_loa}) es sellado.")
        
        elif "RS" in rod_la or "RS" in rod_loa:
            st.warning("⚠️ **ATENCIÓN: RODAMIENTO RS**")
            st.write("Sello de goma de un solo lado. Verifique si el punto de engrase está habilitado.")
        
        else:
            st.success("✅ **EQUIPO APTO PARA LUBRICACIÓN**")
            st.write("Los rodamientos registrados permiten el ingreso de grasa nueva.")
            
        st.markdown("---")

    # Variables de carga
    v_la, v_loa, v_serie = "", "", ""

    # 3. Búsqueda Directa (Sin filtros complejos)
    if tag_seleccionado != "":
        # Filtramos todas las filas de ese TAG
        datos_motor = df_lista[df_lista['Tag'] == tag_seleccionado]
        
        if not datos_motor.empty:
            # Buscamos el último Rodamiento_LA que NO esté vacío
            filtro_la = datos_motor['Rodamiento_LA'].replace(['', 'nan', 'None', '0', 0], pd.NA).dropna()
            if not filtro_la.empty:
                v_la = str(filtro_la.iloc[-1])
            
            # Buscamos el último Rodamiento_LOA que NO esté vacío
            filtro_loa = datos_motor['Rodamiento_LOA'].replace(['', 'nan', 'None', '0', 0], pd.NA).dropna()
            if not filtro_loa.empty:
                v_loa = str(filtro_loa.iloc[-1])

            # Buscamos el último N° de Serie
            filtro_s = datos_motor['N_Serie'].replace(['', 'nan', 'None'], pd.NA).dropna()
            if not filtro_s.empty:
                v_serie = str(filtro_s.iloc[-1])

            # EL CARTELITO VERDE (Para que sepas que lo encontró)
            st.success(f"✅ Motor: {tag_seleccionado} | LA: {v_la} | LOA: {v_loa}")
        else:
            st.warning("⚠️ No se encontraron datos para este TAG.")

    st.divider()

    # 4. Inputs de Rodamientos
    col1, col2 = st.columns(2)
    with col1:
        rod_la = st.text_input("Rodamiento LA", value=v_la, key=f"la_val_{st.session_state.form_id}").upper()
        gr_la_sug = calcular_grasa_avanzado(rod_la)
        st.metric("Sugerido LA", f"{gr_la_sug} g")

    with col2:
        rod_loa = st.text_input("Rodamiento LOA", value=v_loa, key=f"loa_val_{st.session_state.form_id}").upper()
        gr_loa_sug = calcular_grasa_avanzado(rod_loa)
        st.metric("Sugerido LOA", f"{gr_loa_sug} g")

    # 5. Formulario Final
    with st.form(key=f"form_lub_{st.session_state.form_id}"):
        serie_confirm = st.text_input("Confirmar N° de Serie", value=v_serie)
        tecnico = st.text_input("Técnico Responsable")
        
        c1, c2 = st.columns(2)
        gr_real_la = c1.number_input("Gramos Reales LA", value=float(gr_la_sug))
        gr_real_loa = c2.number_input("Gramos Reales LOA", value=float(gr_loa_sug))
        
        tipo_t = st.radio("Tarea", ["Preventivo", "Correctiva"])
        grasa_t = st.selectbox("Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus"])
        notas = st.text_area("Notas")
        
        if st.form_submit_button("💾 GUARDAR"):
            # Buscamos el TAG y el Responsable sin importar cómo se llamen en el formulario
            tag_actual = t if 't' in locals() else (tag_seleccionado if 'tag_seleccionado' in locals() else None)
            resp_actual = resp if 'resp' in locals() else (tecnico if 'tecnico' in locals() else None)

            if tag_actual and resp_actual:
                # 2. BUSCAMOS LOS DATOS DE PLACA EN EL HISTORIAL
                datos_tecnicos = df_completo[df_completo['Tag'] == tag_actual].tail(1).to_dict('records')
                info = datos_tecnicos[0] if datos_tecnicos else {}

                # 3. ARMAMOS EL DICCIONARIO 'nueva'
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": tag_actual,
                    "Responsable": resp_actual,
                    "Notas": notas,
                    "N_Serie": info.get("N_Serie", ""),
                    "Potencia": info.get("Potencia", ""),
                    "Tension": info.get("Tension", ""),
                    "RPM": info.get("RPM", ""),
                    "Carcasa": info.get("Carcasa", ""),
                    "Rodamiento_LA": info.get("Rodamiento_LA", ""),
                    "Rodamiento_LOA": info.get("Rodamiento_LOA", "")
                }
                
                # --- AGREGAR DATOS ESPECÍFICOS SEGÚN EL MODO ---
                if modo == "Mediciones de Campo":
                    nueva.update({
                        "RT_TV1": tv1, "RT_TU1": tu1, "RT_TW1": tw1,
                        "RB_WV1": wv1, "RB_WU1": wu1, "RB_VU1": vu1,
                        "RI_U1U2": u1u2, "RI_V1V2": v1v2, "RI_W1W2": w1w2,
                        "ML_L1": tl1, "ML_L2": tl2, "ML_L3": tl3,
                        "ML_L1L2": l1l2, "ML_L1L3": l1l3, "ML_L2L3": l2l3
                    })
                
                if modo == "Relubricacion":
                    nueva["Descripcion"] = f"LUBRICACIÓN: {grasa_t}. LA: {gr_real_la}g, LOA: {gr_real_loa}g."
                    nueva["notas"] = notas
                # 4. GUARDAR Y GENERAR PDF
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                
                st.session_state.pdf_buffer = generar_pdf_reporte(nueva, f"REPORTE DE {modo.upper()}")
                st.session_state.tag_buffer = tag_actual
                st.session_state.form_id += 1
                st.success(f"✅ Registro de {tag_actual} guardado con éxito")
                st.balloons()
                import time
                time.sleep(1.5) # Para que lleguen a ver el mensaje de éxito
                st.rerun()
            else:
                st.error("⚠️ Error: No se encontró el TAG o el Responsable. Verifique los campos.")

    # --- BOTÓN DE DESCARGA (CORREGIDO) ---
    if st.session_state.get("pdf_buffer") is not None:
        st.divider() # <--- Ves? Estos espacios son los que faltaban
        st.subheader("📥 Reporte Listo para Descargar")
        
        nombre_tag = st.session_state.get("tag_buffer", "Motor")
        
        st.download_button(
            label=f"Hacé clic aquí para descargar Reporte {nombre_tag}",
            data=st.session_state.pdf_buffer,
            file_name=f"Reporte_{nombre_tag}.pdf",
            mime="application/pdf"
        )
        
        if st.button("Limpiar y hacer otro registro"):
            st.session_state.pdf_buffer = None
            st.session_state.tag_buffer = None
            st.rerun()
                
elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo (Megado y Continuidad)")
    fecha_hoy = date.today()
    
    if "cnt_meg" not in st.session_state:
        st.session_state.cnt_meg = 0
        
    tag_inicial = st.session_state.get('tag_fijo', '')

    with st.form(f"form_megado_{st.session_state.cnt_meg}"):
        # --- FILA 1: IDENTIFICACIÓN ---
        col1, col2, col3 = st.columns(3)
        with col1:
            t = st.text_input("TAG del Motor:", value=tag_inicial).upper()
        with col2:
            # Buscamos el N° de Serie si el TAG ya existe en el sistema
            n_serie_sugerido = ""
            if t:
                busqueda_sn = df_completo[df_completo['Tag'] == t].tail(1)
                if not busqueda_sn.empty:
                    n_serie_sugerido = str(busqueda_sn['N_Serie'].values[0])
            
            n_serie = st.text_input("Número de Motor (Serie):", value=n_serie_sugerido)
        with col3:
            resp = st.text_input("Responsable:")

        # --- FILA 2: EQUIPO DE MEDICIÓN ---
        col_eq1, col_eq2 = st.columns(2)
        with col_eq1:
            # Lista de tus equipos de megado (puedes agregar los que quieras)
            lista_equipos = ["Megger MTR 105", "Fluke 1507", "Hipot Tester", "Otro"]
            equipo_megado = st.selectbox("Equipo de Megado utilizado:", lista_equipos)
        with col_eq2:
            tension_prueba = st.selectbox("Tensión de Prueba:", ["500V", "1000V", "2500V", "5000V"])

        st.divider()
        st.subheader("📊 Megado a tierra (Resistencia)")
        # Primera fila de campos chicos
        c1, c2, c3 = st.columns(3)
        tv1 = c1.text_input("T - V1 (GΩ)")
        tu1 = c2.text_input("T - U1 (GΩ)")
        tw1 = c3.text_input("T - W1 (GΩ)")
        
        st.subheader("📊 Megado entre Boninas (Resistencia)")
        # Segunda fila de campos chicos
        c4, c5, c6 = st.columns(3)
        wv1 = c4.text_input("W1 - V1 (GΩ)")
        wu1 = c5.text_input("W1 - U1 (GΩ)")
        vu1 = c6.text_input("V1 - U1 (GΩ)")

        st.subheader("📏 Resistencia internas")
        c7, c8, c9 = st.columns(3)
        u1u2 = c7.text_input("U1 - U2 (Ω)")
        v1v2 = c8.text_input("V1 - V2 (Ω)")
        w1w2 = c9.text_input("W1 - W2 (Ω)")

        st.subheader("🔌 Megado de Línea")
        c10, c11, c12 = st.columns(3)
        tl1 = c10.text_input("T - L1 (MΩ)")
        tl2 = c11.text_input("T - L2 (MΩ)")
        tl3 = c12.text_input("T - L3 (MΩ)")
        
        c13, c14, c15 = st.columns(3)
        l1l2 = c13.text_input("L1 - L2 (GΩ)")
        l1l3 = c14.text_input("L1 - L3 (GΩ)")
        l2l3 = c15.text_input("L2 - L3 (GΩ)")

        st.text_area("Observaciones")

        # BOTÓN DE Guardado
        if st.form_submit_button("💾 GUARDAR MEDICIONES"):
            if t and resp:
                # 1. RESCATE DE DATOS PARA EL PDF
                busqueda = df_completo[df_completo['Tag'] == t].tail(1)
                info = busqueda.iloc[0].to_dict() if not busqueda.empty else {}

                # 2. ARMAMOS EL DICCIONARIO 'nueva' COMPLETO
                nueva = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                    "Tag": t,  # ¿En el Excel es "Tag" o "TAG"? Tiene que ser igual.
                    "N_Serie": n_serie,
                    "Responsable": resp,
                    "Notas": notas,
                    "Potencia": info.get("Potencia", ""),
                    "Tension": info.get("Tension", ""),
                    "RPM": info.get("RPM", ""),
                    "Carcasa": info.get("Carcasa", ""),
                    "Rodamiento_LA": info.get("Rodamiento_LA", ""),
                    "Rodamiento_LOA": info.get("Rodamiento_LOA", ""),
                    "Descripcion": f"MEGADO - Equipo: {equipo_megado} ({tension_prueba})",
                    
                    # Aquí van los valores de megado, asegurate que estas columnas existan en tu Excel
                    "RT_TV1": tv1, "RT_TU1": tu1, "RT_TW1": tw1,
                    "RB_WV1": wv1, "RB_WU1": wu1, "RB_VU1": vu1,
                    "RI_U1U2": u1u2, "RI_V1V2": v1v2, "RI_W1W2": w1w2,
                    "ML_L1": tl1, "ML_L2": tl2, "ML_L3": tl3,
                    "ML_L1L2": l1l2, "ML_L1L3": l1l3, "ML_L2L3": l2l3
                }

                # 3. GUARDAR Y PDF
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                st.session_state.pdf_buffer = generar_pdf_reporte(nueva, "REPORTE DE MEGADO")
                st.session_state.tag_buffer = f"{t}_MEGADO"
                st.session_state.cnt_meg += 1
                
                # --- EL DETALLITO: AVISO DE ÉXITO ---
                if 'tag_fijo' in st.session_state:
                    st.session_state.tag_fijo = ""
                st.success(f"✅ ¡Excelente! Las mediciones del motor {t} se guardaron correctamente.")
                st.balloons()
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("⚠️ El TAG y el Responsable son obligatorios.")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")










































































































































































































































































































































































































































































































































































