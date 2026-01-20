import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
import re
import time
from io import BytesIO
from fpdf import FPDF

fecha_hoy = date.today()

if 'pdf_listo' not in st.session_state:
    st.session_state.pdf_listo = None

def calcular_grasa_avanzado(codigo):
    try:
        s = str(codigo).split('.')[0] # Quitamos el .0 si existe
        solo_numeros = re.sub(r'\D', '', s) 
        
        if len(solo_numeros) < 3: 
            return 0.0
        
        serie_eje = int(solo_numeros[-2:])
        d = serie_eje * 5
        
        serie_tipo = int(solo_numeros[-3])
        
        # 4. Cálculo de dimensiones (D=Exterior, B=Ancho)
        if serie_tipo == 3: # Serie pesada (63xx)
            D = d * 2.2
            B = D * 0.25
        else: # Serie liviana/media (62xx, 60xx)
            D = d * 1.8
            B = D * 0.22
            
        # 5. Fórmula SKF (G = D * B * 0.005)
        gramos = D * B * 0.005
        return round(gramos, 1)
    except Exception as e:
        # Esto nos va a ayudar a ver si hay un error escondido
        print(f"Error en cálculo: {e}")
        return 0.0

# --- 1. FUNCIÓN PDF (Mantiene tus campos) ---
def generar_pdf_reporte(datos, titulo_informe):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. ENCABEZADO Y LOGO
    try:
        pdf.image("logo.png", 10, 8, 33)
    except:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "MARPI MOTORES", ln=True, align='L')

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"{titulo_informe}", ln=True, align='C')
    pdf.ln(5)
    
    # Función para limpiar los NAN
    def v(clave):
        val = str(datos.get(clave, ""))
        return "---" if val.lower() in ["nan", "none", "", "n/a"] else val

    # 2. DATOS DE IDENTIFICACIÓN (Siempre van)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " INFORMACIÓN DEL EQUIPO", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 7, f"Fecha: {v('Fecha')} | Responsable: {v('Responsable')}", ln=True)
    pdf.cell(0, 7, f"TAG: {v('Tag')} | N° Serie: {v('N_Serie')}", ln=True)
    pdf.ln(3)

    # 3. SI ES "NUEVO REGISTRO" (ALTA)
    # --- SECCIÓN: DATOS DE PLACA ---
    if "Potencia" in datos:
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " DATOS DE PLACA", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 7, f"Potencia: {v('Potencia')} | Tension: {v('Tension')} | Corriente: {v('Corriente')}", ln=True)
        pdf.cell(0, 7, f"RPM: {v('RPM')} | Carcasa: {v('Carcasa')}", ln=True)
        pdf.cell(0, 7, f"Rodamiento LA: {v('Rodamiento_LA')} | Rodamiento LOA: {v('Rodamiento_LOA')}", ln=True)
        pdf.ln(3)

    # --- SECCIÓN: MEDICIONES ELÉCTRICAS (9 MEDICIONES DE ALTA) ---
    if "RT_TU" in datos:
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " MEDICIONES ELÉCTRICAS INICIALES", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 7, f"Aislamiento Tierra: TU:{v('RT_TU')} | TV:{v('RT_TV')} | TW:{v('RT_TW')}", ln=True)
        pdf.cell(0, 7, f"Aislamiento Bobinas: UV:{v('RB_UV')} | VW:{v('RB_VW')} | UW:{v('RB_UW')}", ln=True)
        pdf.cell(0, 7, f"Resistencias Internas: U:{v('RI_U')} | V:{v('RI_V')} | W:{v('RI_W')}", ln=True)
        pdf.ln(3)

    # --- SECCIÓN: MEGADO DE CAMPO (15 MEDICIONES) ---
    if "RT_TV1" in datos:
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " MEDICIONES DE CAMPO", ln=True, fill=True)
        # Campos de Alta
       if "RT_TU" in datos:
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " MEDICIONES ELÉCTRICAS INICIALES", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 7, f"Aislamiento a Tierra: TU:{v('RT_TU')} | TV:{v('RT_TV')} | TW:{v('RT_TW')}", ln=True)
        pdf.cell(0, 7, f"Aislamiento entre Bobinas: UV:{v('RB_UV')} | VW:{v('RB_VW')} | UW:{v('RB_UW')}", ln=True)
        pdf.cell(0, 7, f"Resistencias Internas: U:{v('RI_U')} | V:{v('RI_V')} | W:{v('RI_W')}", ln=True)
        # Campos de Megado de campo
        if "RT_TV1" in datos:
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(200, 220, 255) # Un color celeste para destacar
            pdf.cell(0, 8, " MEDICIONES DE MEGADO Y RESISTENCIAS", ln=True, fill=True)
            pdf.set_font("Arial", '', 10)

        # 1. Megado a Tierra (Motor) - 3 datos
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 7, "Aislamiento a Tierra (Motor):", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 7, f"T-V1: {v('RT_TV1')} GOhm | T-U1: {v('RT_TU1')} GOhm | T-W1: {v('RT_TW1')} GOhm", ln=True)

        # 2. Megado entre Bobinas (Motor) - 3 datos
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 7, "Aislamiento entre Bobinas:", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 7, f"W1-V1: {v('RB_WV1')} GOhm | W1-U1: {v('RB_WU1')} GOhm | V1-U1: {v('RB_VU1')} GOhm", ln=True)

        # 3. Resistencias Internas - 3 datos
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 7, "Resistencias Internas (Continuidad):", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 7, f"U1-U2: {v('RI_U1U2')} Ohm | V1-V2: {v('RI_V1V2')} Ohm | W1-W2: {v('RI_W1W2')} Ohm", ln=True)

            pdf.ln(2)
            # 4. Megado de Línea - 6 datos
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 7, "Mediciones de Línea (Alimentación):", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 7, f"Tierra-L1: {v('ML_L1')} GOhm | Tierra-L2: {v('ML_L2')} GOhm | Tierra-L3: {v('ML_L3')} GOhm", ln=True)
            pdf.cell(0, 7, f"L1-L2: {v('ML_L1L2')} GOhm | L1-L3: {v('ML_L1L3')} GOhm | L2-L3: {v('ML_L2L3')} GOhm", ln=True)

    # 5. DETALLE / DESCRIPCIÓN (Lubricación, Reparación u Otros)
    if "Descripcion" in datos:
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, " DETALLE DE INTERVENCIÓN", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, v("Descripcion"))

    # 6. PIE DE PÁGINA
    pdf.set_y(-25)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, "Informe generado por Sistema Marpi Motores", align='C', ln=True)
    pdf.cell(0, 5, "PROPIEDAD DE MARPI MOTORES - CONFIDENCIAL", align='C', ln=True)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')
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
                
                st.success(f"✅ Motor {t} registrado con éxito.")
                st.balloons()
            else:
                st.error("⚠️ El TAG y el Responsable son obligatorios.")
  
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
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url_app}"
            
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
    st.title("🛢️ Lubricación Inteligente MARPI")

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
        
        if st.form_submit_button("💾 GUARDAR REGISTRO"):
            if tecnico and tag_seleccionado:
                # Armamos el paquete de datos con los nombres exactos de tus variables
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": tag_seleccionado, 
                    "Responsable": tecnico,
                    "N_Serie": v_serie,
                    "Descripcion": (f"TAREA: {tipo_t} | GRASA: {grasa_t} | "
                                    f"LA: {rod_la} ({gr_real_la}g) | "
                                    f"LOA: {rod_loa} ({gr_real_loa}g) | "
                                    f"NOTAS: {notas}")
                }
                
                # 1. Guardar en Google Sheets
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                
                # --- REINICIO Y LIMPIEZA (Alineado con el st.success) ---
                st.session_state.form_id += 1
                st.success("✅ Guardado y Formulario Limpio")
                # Quitamos el st.rerun() de acá adentro para que el PDF no se borre
            else:
                st.error("⚠️ Falta Técnico o TAG")

    # --- BOTÓN DE DESCARGA (PEGADO AL MARGEN IZQUIERDO DEL MODO RELUBRICACION) ---
    if st.session_state.get("pdf_buffer"):
        st.divider()
        st.download_button(
            label="📥 DESCARGAR REPORTE PDF",
            data=st.session_state.pdf_buffer,
            file_name=f"Reporte_{st.session_state.tag_buffer}.pdf",
            mime="application/pdf"
        )
                
elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo (Megado y Continuidad)")
    fecha_hoy = date.today()
    # Aseguramos que el contador exista para la limpieza
    if "cnt_meg" not in st.session_state:
        st.session_state.cnt_meg = 0
        
    tag_inicial = st.session_state.get('tag_fijo', '')
    
    # Agregamos la key dinámica al form para que al cambiar cnt_meg se limpie todo
    with st.form(key=f"form_completo_{st.session_state.cnt_meg}"):
        col_t, col_r = st.columns(2)
        t = col_t.text_input("TAG MOTOR", value=tag_inicial).upper()
        sn = st.text_input("N° de Serie")
        resp = col_r.text_input("Técnico Responsable")
        
        st.subheader("📊 Megado a tierra (Resistencia)")
        # Primera fila de campos chicos
        c1, c2, c3 = st.columns(3)
        tv1 = c1.text_input("T - V1 (Ω)")
        tu1 = c2.text_input("T - U1 (Ω)")
        tw1 = c3.text_input("T - W1 (Ω)")
        
        st.subheader("📊 Megado entre Boninas (Resistencia)")
        # Segunda fila de campos chicos
        c4, c5, c6 = st.columns(3)
        wv1 = c4.text_input("W1 - V1 (Ω)")
        wu1 = c5.text_input("W1 - U1 (Ω)")
        vu1 = c6.text_input("V1 - U1 (Ω)")

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
        l1l2 = c13.text_input("L1 - L2 (MΩ)")
        l1l3 = c14.text_input("L1 - L3 (MΩ)")
        l2l3 = c15.text_input("L2 - L3 (MΩ)")

        st.text_area("Observaciones")

        # BOTÓN DE GUARDADO
       # BOTÓN DE GUARDADO
        # 1. BOTÓN DE GUARDADO
        btn_guardar = st.form_submit_button("💾 GUARDAR MEDICIONES")

        if btn_guardar:
            if t and resp:
                detalle = (f"Resistencias: T-V1:{tv1}, T-U1:{tu1}, T-W1:{tw1} | "
                           f"Bornes: U1-U2:{u1u2}, V1-V2:{v1v2}, W1-W2:{w1w2} | "
                           f"Línea: T-L1:{tl1}, L1-L2:{l1l2}")
                
                nueva = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                    "Tag": t,
                    "Responsable": resp,
                    "RT_TV1": tv1, "RT_TU1": tu1, "RT_TW1": tw1,
                    "RB_WV1": wv1, "RB_WU1": wu1, "RB_VU1": vu1,
                    "RI_U1U2": u1u2, "RI_V1V2": v1v2, "RI_W1W2": w1w2,
                    "ML_L1": tl1, "ML_L2": tl2, "ML_L3": tl3,
                    # AGREGÁ ESTAS 3 AQUÍ:
                    "ML_L1L2": l1l2, 
                    "ML_L1L3": l1l3, 
                    "ML_L2L3": l2l3
                }
                
                # Actualizar base de datos
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                
                # GUARDAMOS EL PDF EN LA MEMORIA PARA USARLO AFUERA
                st.session_state.pdf_a_descargar = generar_pdf_reporte(nueva, t)
                st.session_state.tag_actual = t
                
                st.success(f"✅ Mediciones de {t} guardadas.")
            else:
                st.error("⚠️ Falta TAG o Responsable")

    # --- 2. EL BOTÓN DE DESCARGA VA AFUERA DEL FORMULARIO (Saliendo del 'with st.form') ---
    if "pdf_a_descargar" in st.session_state and st.session_state.pdf_a_descargar is not None:
        st.write("---")
        st.download_button(
            label="📥 CLIC AQUÍ PARA DESCARGAR REPORTE PDF",
            data=st.session_state.pdf_a_descargar,
            file_name=f"Reporte_{st.session_state.tag_actual}.pdf",
            mime="application/pdf"
        )
        if st.button("Hacer otro registro (Limpiar)"):
            st.session_state.pdf_a_descargar = None
            st.session_state.tag_fijo = ""
            st.session_state.cnt_meg += 1
            st.rerun()
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")

































































































































































































































































































































































































































































































