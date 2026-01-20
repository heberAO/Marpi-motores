import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse  # Para el QR sin errores
import re

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
def generar_pdf_reporte(datos, tag_motor, tipo_trabajo="INFORME TÉCNICO"):
    try:
        from fpdf import FPDF
        # ESTO ES LO NUEVO: Limpiamos los nombres para que no importe si tienen espacio o guion
        # Convierte "Rodamiento LA" o "Rodamiento_LA" en "rodamiento_la"
        datos_limpios = {str(k).replace(" ", "_").lower(): v for k, v in datos.items()}
        
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Título y Encabezado
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, f'{tipo_trabajo}', 0, 1, 'R')
        pdf.ln(5)

        # Datos Básicos (usando datos_limpios)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(95, 8, f"Fecha: {datos_limpios.get('fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos_limpios.get('responsable','-')}", 1, 1)

        # --- SECCIÓN LUBRICACIÓN ---
        if "LUBRICACION" in tipo_trabajo.upper():
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, " DETALLES DE LUBRICACIÓN:", 1, 1, 'L', True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(95, 8, f"Rod. LA: {datos_limpios.get('rodamiento_la','-')}", 1, 0)
            pdf.cell(95, 8, f"Gramos LA: {datos_limpios.get('gramos_la','0')} g", 1, 1)
            pdf.cell(95, 8, f"Rod. LOA: {datos_limpios.get('rodamiento_loa','-')}", 1, 0)
            pdf.cell(95, 8, f"Gramos LOA: {datos_limpios.get('gramos_loa','0')} g", 1, 1)

        # --- SECCIÓN MEGADO ---
        elif "MEGADO" in tipo_trabajo.upper() or "AISLACION" in tipo_trabajo.upper():
            pdf.ln(5)
            pdf.set_fill_color(0, 51, 102)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, " MEDICIONES DE AISLACIÓN (MOhms)", 1, 1, 'C', True)
            pdf.set_text_color(0, 0, 0)
            # Buscamos las fases
            u = datos_limpios.get('u_gnd') or datos_limpios.get('fase_u') or '-'
            v = datos_limpios.get('v_gnd') or datos_limpios.get('fase_v') or '-'
            w = datos_limpios.get('w_gnd') or datos_limpios.get('fase_w') or '-'
            pdf.cell(63, 12, f"U-GND: {u}", 1, 0, 'C')
            pdf.cell(63, 12, f"V-GND: {v}", 1, 0, 'C')
            pdf.cell(64, 12, f"W-GND: {w}", 1, 1, 'C')

        # --- DESCRIPCIÓN ---
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DESCRIPCIÓN:", 0, 1)
        desc = datos_limpios.get('descripcion') or datos_limpios.get('intervencion') or '-'
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(desc), border=1)

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
    
    # 1. Usamos una "llave" para el formulario (counter) para poder resetearlo
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")

    # 2. El formulario usa la llave de la memoria
    with st.form(key=f"alta_motor_{st.session_state.form_key}"):
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
            if not t or not resp:
                st.error("⚠️ El TAG y el Responsable son obligatorios.")
            else:
                # 1. CREAMOS la variable mediciones antes de usarla
                mediciones = f"RES: T-U:{rt_tu}, T-V:{rt_tv}, T-W:{rt_tw} | B: UV:{rb_uv}, VW:{rb_vw}, UW:{rb_uw}"

                # 2. Ahora armamos el diccionario con todas las columnas
                nueva = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"), 
                    "Tag": t, 
                    "N_Serie": sn, 
                    "Responsable": resp,
                    "Potencia": p,      
                    "RPM": r,           
                    "Frame": f,         
                    "Descripcion": f"{desc} | {mediciones}", 
                    "Taller_Externo": ext
                }
                
                # 3. Guardado en la base de datos
                df_actualizado = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_actualizado)
                
                # 4. Mensaje de éxito y limpieza
                st.session_state.form_key += 1
                st.success(f"✅ Motor {t} guardado con Potencia {p} y {r} RPM")
                st.rerun()
  
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

            # HISTORIAL Y EL BUSCADOR ---

            # 1. Título del historial
            st.subheader("📜 Historial de Intervenciones")
            hist_m = df_completo[df_completo['Tag'] == buscado].copy()
            hist_m = hist_m.iloc[::-1] 

            for idx, fila in hist_m.iterrows():
                intervencion = str(fila.get('Descripcion', '-'))[:40]
                with st.expander(f"📅 {fila.get('Fecha','-')} - {intervencion}..."):
                    st.write(f"**Responsable:** {fila.get('Responsable','-')}")
                    st.write(f"**Detalle completo:** {fila.get('Descripcion','-')}")
                    
                    # Identificamos qué tipo de trabajo era para el PDF
                    desc_txt = str(fila.get('Descripcion', '')).upper()
                    if "PREVENTIVA" in desc_txt or "CORRECTIVA" in desc_txt:
                        t_inf = "REPORTE DE LUBRICACIÓN"
                    elif "MEGADO" in desc_txt or "AISLACION" in desc_txt:
                        t_inf = "INFORME DE MEGADO"
                    else:
                        t_inf = "INFORME TÉCNICO"

                    # Generamos el PDF usando la función que está arriba
                    pdf_archivo = generar_pdf_reporte(fila.to_dict(), buscado, t_inf)
                    
                    if pdf_archivo:
                        st.download_button(
                            label="📄 Descargar Informe PDF",
                            data=pdf_archivo,
                            file_name=f"Reporte_{buscado}_{idx}.pdf",
                            key=f"btn_pdf_{idx}",
                            mime="application/pdf"
                        )

# --- SALIMOS DEL HISTORIAL 
st.divider()

if "form_id" not in st.session_state:
    st.session_state.form_id = 0

# 2. EL BUSCADOR (Lo ponemos aquí para que Python lo lea antes de usarlo abajo)
df_lista = df_completo.fillna("-")
lista_sugerencias = sorted(list(set(df_lista['Tag'].astype(str).tolist() + df_lista['N_Serie'].astype(str).tolist())))

opcion_elegida = st.selectbox(
    "Seleccione TAG o N° DE SERIE para nueva carga", 
    options=[""] + lista_sugerencias,
    key=f"search_{st.session_state.form_id}"
)

# 3. LÓGICA DE MOTOR ENCONTRADO
motor_encontrado = None
if opcion_elegida != "":
    res = df_lista[(df_lista['Tag'] == opcion_elegida) | (df_lista['N_Serie'] == opcion_elegida)]
    if not res.empty:
        motor_encontrado = res.iloc[-1]
        st.success(f"✅ Motor detectado: {motor_encontrado['Tag']}")
    
    # --- 2. PREPARACIÓN DE VALORES PARA LOS CAMPOS ---
    if motor_encontrado is not None:
        # Usamos .get por si acaso, pero fijate que el nombre coincida con el st.write
        val_la_sug = str(motor_encontrado.get('Rodamiento_LA', ''))
        val_loa_sug = str(motor_encontrado.get('Rodamiento_LOA', ''))
        serie_sug = str(motor_encontrado.get('N_Serie', ''))

    else:
       val_la_sug = ""
       val_loa_sug = ""
       serie_sug = ""

    # 2. Rodamientos y Cálculo
    col1, col2 = st.columns(2)
    with col1:
        val_la = str(motor_encontrado['Rodamiento_LA']) if motor_encontrado is not None else ""
        rod_la = st.text_input("Rodamiento LA", value=val_la_sug).upper()
        gr_la_sug = calcular_grasa_avanzado(rod_la)
        st.metric("Sugerido LA", f"{gr_la_sug} g")

    with col2:
        val_loa = str(motor_encontrado['Rodamiento_LOA']) if motor_encontrado is not None else ""
        rod_loa = st.text_input("Rodamiento LOA", value=val_loa_sug).upper()
        gr_loa_sug = calcular_grasa_avanzado(rod_loa)
        st.metric("Sugerido LOA", f"{gr_loa_sug} g")

    # 3. Formulario de Carga
    with st.form(key=f"form_main_{st.session_state.form_id}"): # <--- El formulario también cambia de ID
        serie_final = st.text_input("Confirmar N° de Serie", value=str(motor_encontrado['N_Serie']) if motor_encontrado is not None else "")
        resp_r = st.text_input("Técnico Responsable")
        
        c1, c2 = st.columns(2)
        with c1:
            gr_f_la = st.number_input("Gramos Reales LA", value=float(gr_la_sug))
        with c2:
            gr_f_loa = st.number_input("Gramos Reales LOA", value=float(gr_loa_sug))
        Tipo_tarea = st.radio(
            "Tipo de Intervencion",
            ["Preventivo (planificaco)", "Correctiva (Urgencia)"],
            index=0
        )
            
        grasa = st.selectbox("Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
        obs = st.text_area("Notas")
        
        btn_guardar = st.form_submit_button("💾 GUARDAR REGISTRO")

    # 4. Lógica de Guardado
    ¡Estamos en el último tramo, Heber! No te vuelvas loco, ese error pasa porque la dirección de tu Excel (la URL) está guardada en una variable con otro nombre o está dentro de tus Secrets de Streamlit.

Para que no dependamos de nombres raros, vamos a usar lo que ya tenés funcionando. Si tu App ya muestra el historial, es porque ya está conectada a la planilla.

La solución "Corta" (Hacé esto primero)
Buscá en tu código la parte donde dice conn.read(...). Verás que adentro dice algo como spreadsheet=url o spreadsheet=st.secrets["..."].

Cambiá tu bloque de guardado por este, que es el más estándar para Streamlit:

Python

    if btn_guardar:
        if not resp_r or not opcion_elegida:
            st.error("⚠️ Falta completar datos.")
        else:
            try:
                # 1. Armamos los datos
                datos_nuevos = pd.DataFrame([{
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": opcion_elegida,
                    "N_Serie": serie_final,
                    "Responsable": resp_r,
                    "Rodamiento LA": rod_la,
                    "Rodamiento LOA": rod_loa,
                    "Gramos LA": gr_f_la,
                    "Gramos LOA": gr_f_loa,
                    "Grasa": grasa,
                    "Descripcion": Tipo_tarea,
                    "Observaciones": obs
                }])

                # 2. GUARDADO DIRECTO (Sin usar variables externas)
                # Usamos la misma conexión 'conn' que usás para leer el historial
                conn.create(data=datos_nuevos) 
                
                st.success("✅ ¡Registro guardado en Google Sheets!")

                # 3. GENERAR PDF PARA DESCARGAR
                # Usamos datos_nuevos.iloc[0] para que la función del PDF reciba un diccionario
                pdf_content = generar_pdf_reporte(datos_nuevos.iloc[0].to_dict(), opcion_elegida, "REPORTE DE LUBRICACIÓN")
                
                if pdf_content:
                    st.download_button("📥 Descargar Reporte PDF", pdf_content, f"Lubricacion_{opcion_elegida}.pdf")

                st.balloons()
                time.sleep(2)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")
                    
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












































































































































































































































































































































































































