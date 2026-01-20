import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
import re
import time
from io import BytesIO

# Librerías para el PDF (Usaremos ReportLab que es mejor para logos)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

if "form_id" not in st.session_state:
    st.session_state.form_id = 0

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
def generar_pdf_reporte(datos, tag_motor):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # --- LOGO DE LA EMPRESA ---
    try:
        # Posición: X=0.5 pulgada, Y=10 pulgadas (arriba a la izquierda)
        # Tamaño: 1.5 pulgadas de ancho (el alto se ajusta solo)
        c.drawImage("logo_empresa.png", 0.5*inch, 10*inch, width=1.5*inch, preserveAspectRatio=True, mask='auto')
    except:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.5*inch, 10.5*inch, "MARPI MOTORES") # Texto si no carga el logo

    # --- ENCABEZADO ---
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(4.25*inch, 10.2*inch, f"PROTOCOLO DE ALTA - MOTOR {tag_motor}")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(4.25*inch, 10*inch, f"Fecha de Emisión: {datos.get('Fecha', 'N/A')}")
    
    c.line(0.5*inch, 9.8*inch, 8*inch, 9.8*inch) # Línea divisoria

    # --- CUERPO DEL INFORME (Resumen de datos) ---
    y = 9.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.5*inch, y, "DATOS DE PLACA Y REGISTRO")
    y -= 0.3*inch
    
    c.setFont("Helvetica", 10)
    # Lista de datos a imprimir
    items = [
        f"Responsable: {datos.get('Responsable', 'N/A')}",
        f"N° de Serie: {datos.get('N_Serie', 'N/A')}",
        f"Potencia: {datos.get('Potencia', 'N/A')} | RPM: {datos.get('RPM', 'N/A')}",
        f"Carcasa/Frame: {datos.get('Carcasa', 'N/A')}",
        f"Rodamiento LA: {datos.get('Rodamiento_LA', 'N/A')}",
        f"Rodamiento LOA: {datos.get('Rodamiento_LOA', 'N/A')}"
    ]
    
    for item in items:
        c.drawString(0.7*inch, y, f"• {item}")
        y -= 0.2*inch

    # --- MEDICIONES ELÉCTRICAS ---
    y -= 0.2*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.5*inch, y, "MEDICIONES ELÉCTRICAS")
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(0.7*inch, y, f"Resistencia (RT): TU: {datos.get('RT_TU', '-')} | TV: {datos.get('RT_TV', '-')} | TW: {datos.get('RT_TW', '-')}")
    y -= 0.2*inch
    c.drawString(0.7*inch, y, f"Aislamiento (RB): UV: {datos.get('RB_UV', '-')} | VW: {datos.get('RB_VW', '-')} | UW: {datos.get('RB_UW', '-')}")

    # --- PIE DE PÁGINA (Propiedad de la empresa) ---
    c.line(0.5*inch, 1*inch, 8*inch, 1*inch)
    c.setFont("Helvetica-Oblique", 8)
    # ACÁ VA TU LEYENDA
    leyenda = "Este informe es propiedad de MARPI MOTORES. Prohibida su reproducción total o parcial sin autorización."
    c.drawCentredString(4.25*inch, 0.8*inch, leyenda)
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
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
        if not t or not resp:
            st.error("⚠️ El TAG y el Responsable son obligatorios.")
        else:
            # 1. ARMAMOS EL DICCIONARIO
            nueva = {
                "Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, "Responsable": resp,
                "Potencia": p, "Tension": v, "Corriente": cor, "RPM": r, "Carcasa": carc, "Frame": carc,
                "Rodamiento_LA": r_la, "Rodamiento_LOA": r_loa,
                "RT_TU": v_rt_tu, "RT_TV": v_rt_tv, "RT_TW": v_rt_tw,
                "RB_UV": v_rb_uv, "RB_VW": v_rb_vw, "RB_UW": v_rb_uw,
                "RI_U": v_ri_u, "RI_V": v_ri_v, "RI_W": v_ri_w,
                "Descripcion": f"ALTA INICIAL: {desc}", "Trabajos_taller_externo": ext, "Taller_Externo": ext
            }
            
            # 2. GUARDAMOS EN EXCEL
            df_act = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_act)
            st.success("✅ Datos guardados en la nube.")

            # 3. GENERAMOS EL PDF
            pdf_bytes = generar_pdf_reporte(nueva, t)
            
            if pdf_bytes:
                st.download_button(
                    label="📥 DESCARGAR PROTOCOLO DE ALTA (PDF)",
                    data=pdf_bytes,
                    file_name=f"Alta_{t}_{nueva['Fecha']}.pdf",
                    mime="application/pdf"
                )
                st.balloons()
            else:
                st.error("❌ El Excel se guardó pero hubo un problema con el PDF.")
  
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
                # Armamos la fila para guardar
                nueva_data = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": tag_seleccionado, 
                    "N_Serie": serie_confirm,
                    "Responsable": tecnico, 
                    "Rodamiento_LA": rod_la,
                    "Gramos_LA": gr_real_la, 
                    "Rodamiento_LOA": rod_loa,
                    "Gramos_LOA": gr_real_loa, 
                    "Tipo_Grasa": grasa_t, 
                    "Tipo_Tarea": tipo_t, 
                    "Descripcion": "RELUBRICACIÓN",
                    "Taller_Externo": notas
                }
                
                # Subir a Google Sheets
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_data])], ignore_index=True)
                conn.update(data=df_final)
                
                # REINICIO Y LIMPIEZA
                st.session_state.form_id += 1
                st.success("✅ Guardado y Formulario Limpio")
                time.sleep(1)
                st.rerun()
                
elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo (Megado y Continuidad)")
    
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
        btn_guardar = st.form_submit_button("💾 GUARDAR MEDICIONES")

        if btn_guardar:
            if t and resp:
                detalle = (f"Resistencias: T-V1:{tv1}, T-U1:{tu1}, T-W1:{tw1} | "
                           f"Bornes: U1-U2:{u1u2}, V1-V2:{v1v2}, W1-W2:{w1w2} | "
                           f"Línea: T-L1:{tl1}, L1-L2:{l1l2}")
                
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": t,
                    "Responsable": resp,
                    "Descripcion": detalle,
                    "Taller_Externo": "Mediciones completas cargadas desde App."
                }
                
                # Actualizar base de datos
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)
                
                # --- RESET DE CAMPOS ---
                st.session_state.tag_fijo = "" # Limpia el tag de la memoria
                st.session_state.cnt_meg += 1 # Esto cambia la key del form y limpia TODO
                
                st.success(f"✅ Mediciones de {t} guardadas y campos limpios")
                st.rerun()
            else:
                st.error("⚠️ Falta completar TAG o Técnico")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")




































































































































































































































































































































































































































































