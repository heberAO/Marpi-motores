import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
import re
import time
from io import BytesIO
from fpdf import FPDF
import qrcode
from PIL import Image, ImageDraw, ImageFont
import streamlit.components.v1 as components
import requests
import urllib.parse

def boton_descarga_pro(tag, fecha, tarea, resp, serie, pot, rpm, carcasa, detalles, extra, obs):
    st_btn = 'width:100%;background:#007bff;color:white;padding:15px;border:none;border-radius:10px;font-weight:bold;cursor:pointer;font-family:sans-serif;'
    
    contenido = f"""
    <div style='text-align:center;border-bottom:2px solid #444;margin-bottom:15px;'>
        <h2 style='margin:0;color:#007bff;'>REPORTE TÉCNICO DE MOTOR</h2>
    </div>
    <p><b>🏷️ TAG:</b> {tag} | <b>📅 FECHA:</b> {fecha}</p>
    <p><b>🛠️ TAREA:</b> {tarea} | <b>👤 RESP:</b> {resp}</p>
    <hr>
    <div style='background:#1a1c23;padding:10px;border-radius:5px;'>
        <b>📋 DATOS DE PLACA:</b> Serie: {serie} | Pot: {pot} | RPM: {rpm} | <b>Carcasa: {carcasa}</b>
    </div>
    <div style='background:#1a1c23;padding:10px;border-radius:5px;margin:10px 0; font-size:13px;'>
        {detalles}
        <i style='color:#aaa;'>{extra}</i>
    </div>
    <p><b>📝 OBSERVACIONES:</b><br>{obs}</p>
    """
    
    js_code = f"""
    const el = document.createElement('div');
    el.style = 'padding:30px;background:#0e1117;color:white;width:600px;font-family:sans-serif;line-height:1.4;';
    el.innerHTML = `{contenido}`;
    document.body.appendChild(el);
    html2canvas(el,{{backgroundColor:'#0e1117',scale:2}}).then(canvas => {{
        const link = document.createElement('a');
        link.download = 'Reporte_{tag}_{fecha}.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
        document.body.removeChild(el);
    }});
    """
    return f'<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script><button onclick="{js_code}" style="{st_btn}">📥 GUARDAR REPORTE COMPLETO</button>'
def generar_etiqueta_honeywell(tag, serie, potencia):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import qrcode
        import io 
        import os

        # 1. LIENZO (600x300)
        etiqueta = Image.new('RGB', (600, 300), (255, 255, 255))
        draw = ImageDraw.Draw(etiqueta)

        # 2. QR (LADO IZQUIERDO) - 250x250 px
        qr_url = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?serie={serie}&exact=1"
        qr = qrcode.make(qr_url)
        img_qr = qr.convert('RGB').resize((250, 250))
        etiqueta.paste(img_qr, (20, 25))

        # 3. LADO DERECHO (Número de Motor)
        x_derecha = 300
        texto_nro = str(serie).upper()
        
        # --- CARGA DE FUENTE PROPIA ---
        # Intentamos cargar el archivo que vas a subir al GitHub
        nombre_fuente = "Arial-Bold.ttf" 
        if os.path.exists(nombre_fuente):
            fuente = ImageFont.truetype(nombre_fuente, 35) # Tamaño 100: Muy grande
        else:
            # Si aún no lo subes, usamos este truco para que al menos se vea algo
            fuente = ImageFont.load_default()
            st.warning("⚠️ Sube 'Arial-Bold.ttf' a GitHub para ver el número grande.")

        # Dibujamos el número (Centrado verticalmente en el espacio derecho)
        draw.text((x_derecha + 10, 100), texto_nro, font=fuente, fill=(0,0,0))

        # 4. LOGO (Ubicación Superior)
        try:
            logo = Image.open("logo.png").convert('RGBA')
            # Lo redimensionamos para que no tape al número
            logo.thumbnail((250, 80), Image.Resampling.LANCZOS)
            etiqueta.paste(logo, (x_derecha + 15, 20), logo)
        except:
            draw.text((x_derecha + 15, 20), "MARPI MOTORES", fill=(0,0,0))

        # 5. CONVERSIÓN PARA IMPRESORA HONEYWELL
        # Convertimos a blanco y negro puro (Threshold) para que no salga borroso
        etiqueta_final = etiqueta.convert('L').point(lambda x: 0 if x < 128 else 255, '1')

        buf = io.BytesIO()
        etiqueta_final.save(buf, format='PNG') 
        return buf.getvalue()

    except Exception as e:
        st.error(f"Error en etiqueta: {e}")
        return None
        
def calcular_grasa_marpi(rodamiento):
    """Calcula gramos de grasa según el modelo del rodamiento."""
    if not rodamiento or rodamiento in ["-", "S/D", "nan"]:
        return 0
    
    # Extraemos solo los números del rodamiento (ej: de 6319 C3 saca 6319)
    import re
    match = re.search(r'\d{4,5}', str(rodamiento))
    if not match:
        return 0
    
    codigo = match.group()
    # Lógica de cálculo basada en el diámetro exterior aproximado
    # Fórmula: D * B * 0.005 (Simplificada para mantenimiento)
    try:
        serie = int(codigo[1]) # 2 para 62xx, 3 para 63xx
        tamanio = int(codigo[2:]) # Los últimos dos dígitos (19, 22, etc)
        
        # Estimación de gramos Marpi
        if serie == 3:
            gramos = (tamanio * 2.5) - 5 
        else:
            gramos = (tamanio * 1.5)
        return max(5, round(gramos, 1)) # Mínimo 5g para motores industriales
    except:
        return 0
        
if "archivo_nombre" not in st.session_state:
    st.session_state.archivo_nombre = "Reporte_Motor"        
# Inicializamos variables de estado
if "tag_fijo" not in st.session_state: st.session_state.tag_fijo = ""
if "modo_manual" not in st.session_state: st.session_state.modo_manual = False
# --- FUNCIÓN DE CARGA OPTIMIZADA ---
# --- 1. CONEXIÓN GLOBAL (Afuera de las funciones) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10) 
def cargar_datos_google():
    try:
        # Ya no definimos conn aquí adentro, usamos la de afuera
        return conn.read(ttl=0) 
    except Exception as e:
        st.error(f"⚠️ Error conectando a Google Sheets: {e}")
        return pd.DataFrame()

# --- USO DE LA FUNCIÓN ---
df_completo = cargar_datos_google()
# --- CONEXIÓN A LA HOJA DE PLANIFICACIÓN ---
# Reemplaza "Planificacion" por el nombre exacto que le pusiste a la pestaña
try:
    df_plan = conn.read(worksheet="Planificación")
except Exception as e:
    st.error(f"No se pudo leer la hoja de Planificación: {e}")
    df_plan = pd.DataFrame()
# --- 2. INICIALIZACIÓN DE VARIABLES Y QR ---
if "motor_seleccionado" not in st.session_state:
    st.session_state.motor_seleccionado = None

# --- SOLO DETECCIÓN (No dibujes nada aquí) ---
params = st.query_params
qr_valor = params.get("serie") or params.get("tag") or params.get("Serie") or params.get("Tag")

# Decidimos a qué pestaña ir (1 es Historial)
indice_inicio = 1 

# --- 2. FILTRO DE MOTOR POR QR ---
# Solo ejecutamos el filtro si realmente existe un qr_valor
if qr_valor:
    v_qr = str(qr_valor).strip().upper()
    
    # Verificamos que el DataFrame no esté vacío antes de filtrar
    if not df_completo.empty:
        filtro = df_completo[
            (df_completo['N_Serie'].astype(str).str.upper() == v_qr) | 
            (df_completo['Tag'].astype(str).str.upper() == v_qr)
        ]
        
        # Si encontró algo, lo guardamos en el session_state
        if not filtro.empty:
            st.session_state.motor_seleccionado = filtro.iloc[-1]
# --- 5. MENÚ LATERAL (ROBUSTO) ---
opciones_menu = ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"]

# Inicializar la memoria de navegación si no existe
if "navegacion_actual" not in st.session_state:
    st.session_state.navegacion_actual = "Historial y QR"

with st.sidebar:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    
    # Buscamos en qué posición (0, 1, 2, 3) está la página guardada en memoria
    try:
        idx_defecto = opciones_menu.index(st.session_state.navegacion_actual)
    except ValueError:
        idx_defecto = 1 # Por defecto Historial

    # Creamos el menú usando ese índice
    seleccion = st.radio(
        "Ir a:", 
        opciones_menu, 
        index=idx_defecto
    )

    # Si el usuario hace CLIC manual en el menú, actualizamos la memoria
    if seleccion != st.session_state.navegacion_actual:
        st.session_state.navegacion_actual = seleccion
        st.rerun()

    # Botón de Reset
    if st.button("🧹 Inicio / Reset"):
        st.session_state.clear()
        st.rerun()

# Asignamos la variable 'modo' para que el resto de tu código funcione igual
modo = st.session_state.navegacion_actual

# --- 6. VALIDACIÓN DE CONTRASEÑA ---
if modo in ["Nuevo Registro", "Relubricacion", "Mediciones de Campo"]:
    if "autorizado" not in st.session_state:
        st.session_state.autorizado = False

    if not st.session_state.autorizado:
        st.title("🔒 Acceso Restringido")
        st.info("Esta sección es solo para personal de MARPI.")
        with st.form("login_marpi"):
            clave = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("Validar Ingreso"):
                if clave == "MARPI2026":
                    st.session_state.autorizado = True
                    st.rerun()
                else:
                    st.error("⚠️ Clave incorrecta")
        st.stop() # <--- AQUÍ SE DETIENE SOLO SI NO ESTÁ LOGUEADO
st.title("🛠️ Gestión de Reparaciones - Marpi")

with st.expander("📝 PROGRAMAR NUEVA REPARACIÓN"):
    with st.form("nuevo_plan"):
        c1, c2 = st.columns(2)
        with c1:
            f_ot = st.text_input("N° Orden de Trabajo (OT)").upper()
            opciones_motores = df_completo['Tag'].astype(str) + " | " + df_completo['N_Serie'].astype(str) if not df_completo.empty else ["Sin datos"]
            f_motor = st.selectbox("Seleccionar Motor", opciones_motores)
            f_planta = st.text_input("Planta").upper()
            f_inspector = st.selectbox("Inspector", ["CONNAN ENZO", "VILLARTA EDGARDO", "CORREA MARCELO", "SALCEDO GASTON", "CORVALAN DARIO"])

        with c2:
            f_tarea = st.selectbox("Tarea a realizar", ["Desarmar/Evaluar", "Cambio de Rodamientos", "Armado"])
            f_encargado = st.selectbox("Asignar a Reparador", ["Toledano Ruben", "Accordinaro Diego", "Ortega Enzo"])
            f_prioridad = st.select_slider("Prioridad", options=["Baja", "Normal", "Urgente"])
            f_fecha = st.date_input("Fecha Programada", date.today())

        btn_plan = st.form_submit_button("Guardar en Agenda")

    if btn_plan:
        if f_ot and f_motor:
            # 1. Preparamos los datos
            nueva_fila_plan = pd.DataFrame([{
                "Fecha": f_fecha.strftime("%d/%m/%Y"),
                "OT": f_ot,
                "Motor": f_motor,
                "Planta": f_planta,
                "Inspector": f_inspector,
                "Encargado": f_encargado,
                "Tarea": f_tarea,
                "Prioridad": f_prioridad,
                "Estado": "Pendiente",
            }])
            
            try:
                df_plan_actual = conn.read(worksheet="Planificación", ttl=0)
                
                # 3. Unimos lo nuevo con lo viejo
                df_final_plan = pd.concat([df_plan_actual, nueva_fila_plan], ignore_index=True)
                
                # 4. Actualizamos la hoja completa
                conn.update(worksheet="Planificación", data=df_final_plan)
                
                st.success(f"✅ OT {f_ot} guardada en Agenda")

                # --- Lógica de WhatsApp ---
                telefonos = {
                    "Toledano Ruben": "5492615914147",
                    "Accordinaro Diego": "549261000000",
                    "Ortega Enzo": "549261000000"
                }

                tel = telefonos.get(f_encargado, "")
                if tel:
                    mensaje_wa = f"Hola {f_encargado}, se te asignó la OT: {f_ot} para el motor {f_motor}. Tarea: {f_tarea}. Planta: {f_planta}. Inspector: {f_inspector}. "
                    texto_url = urllib.parse.quote(mensaje_wa)
                    link_wa = f"https://wa.me/{tel}?text={texto_url}"
                    st.link_button(f"📲 Enviar WhatsApp a {f_encargado}", link_wa)
            
            except Exception as e:
                st.error(f"❌ Error de Conexión: {e}")
                st.info("Asegúrate de que la pestaña se llame exactamente 'Planificación' y tenga los encabezados en la fila 1.")
        else:
            st.warning("Por favor, completa N° de OT y selecciona un Motor.")

if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0
    
    # 1. Recuperamos los datos que enviamos desde el Historial
    datos_auto = st.session_state.get('datos_motor_auto', {})
    
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    
    with st.form(key=f"alta_motor_{st.session_state.form_key}"):
        st.markdown("### 📝 Datos de la Nueva Intervención")
        # --- CAMPOS DE ENTRADA ---
        c1, c2, c3 = st.columns([2, 2, 1])
        # Llenamos TAG y Serie
        t = c1.text_input("TAG/ID MOTOR", value=datos_auto.get('tag', '')).upper()
        sn = c2.text_input("N° de Serie", value=datos_auto.get('serie', '')).upper()
        resp = c3.text_input("Responsable")

        c4, c5, c6, c7, c8 = st.columns(5)
        # Llenamos Potencia, Tensión, Corriente y Carcasa automáticamente
        p = c4.text_input("Potencia", value=datos_auto.get('potencia', ''))
        v = c5.text_input("Tensión", value=datos_auto.get('tension', ''))
        cor = c6.text_input("Corriente", value=datos_auto.get('corriente', ''))
        
        # 1. Extraemos valores únicos de la base de datos, quitamos vacíos y convertimos a texto
        if not df_completo.empty and 'RPM' in df_completo.columns:
            # Obtenemos valores únicos, los pasamos a string y eliminamos 'nan'
            rpms_db = df_completo['RPM'].astype(str).unique().tolist()
            rpms_db = [val for val in rpms_db if val not in ['nan', '-', 'None', '']]
        else:
            rpms_db = []

        # 2. Definimos valores base (por si la base de datos está vacía)
        rpms_estandar = ["750", "1000", "1500", "3000"]
        
        # 3. Combinamos ambos, eliminamos duplicados y ordenamos de menor a mayor
        # Usamos set() para que no se repitan y sorted() para el orden
        rpms_limpias = [str(r).strip() for r in (rpms_estandar + rpms_db) if r and str(r).strip() != 'nan']
        rpms_lista = ["-"] + sorted(list(set(rpms_limpias)), key=lambda x: int(x) if str(x).isdigit() else 0)
        # 4. Buscamos el valor que viene de datos_auto (del QR o Historial)
        val_rpm = str(datos_auto.get('rpm', '-'))
        
        # Si el valor no está en la lista (caso raro), lo agregamos para que no de error
        if val_rpm not in rpms_lista:
            rpms_lista.append(val_rpm)
            rpms_lista = sorted(rpms_lista, key=lambda x: int(x) if x.isdigit() else 0)

        # 5. Calculamos el índice para el autocompletado
        idx_rpm = rpms_lista.index(val_rpm)
        
        # 6. Mostramos el Selectbox final
        r = c7.selectbox("RPM", rpms_lista, index=idx_rpm)
        
        carc = c8.text_input("Carcasa/Frame", value=datos_auto.get('carcasa', ''))

        st.subheader("⚙️ Rodamientos de Placa")
        r1, r2 = st.columns(2)
        # Llenamos los rodamientos automáticamente
        r_la = r1.text_input("Rodamiento LA", value=datos_auto.get('r_la', '')).upper()
        r_loa = r2.text_input("Rodamiento LOA", value=datos_auto.get('r_loa', '')).upper()
        
        tipo_rodamiento = st.selectbox(
            "Tipo de rodamientos instalados:",
            ["Abierto (Sin sellos)","RS Sello de un solo lado", "2RS (Sello Caucho Sintetico - Hermético)", "ZZ (Blindaje Metálico)"]
        )    


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
                # 1. Crear el diccionario con los datos exactos
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                    "Tag": t,
                    "N_Serie": sn,
                    "Responsable": resp,
                    "Potencia": p, "Tension": v, "Corriente": cor,
                    "RPM": r, "Carcasa": carc,
                    "Rodamiento_LA": r_la, "Rodamiento_LOA": r_loa,
                    "Tipo_Sello": tipo_rodamiento,
                    "RT_TU": v_rt_tu, "RT_TV": v_rt_tv, "RT_TW": v_rt_tw,
                    "RB_UV": v_rb_uv, "RB_VW": v_rb_vw, "RB_UW": v_rb_uw,
                    "RI_U": v_ri_u, "RI_V": v_ri_v, "RI_W": v_ri_w,
                    "Descripcion": desc,
                    "Trabajos_Externos": ext,  # <--- CORREGIDO: Antes podía faltar o tener otro nombre
                    "Tipo_Tarea": "Nuevo Registro"
                }

                # Lógica para subir a Google Sheets
                df_nueva = pd.DataFrame([nueva_fila])
                df_actualizado = pd.concat([df_completo, df_nueva], ignore_index=True)
                # 3. UNIR Y ACTUALIZAR (Lógica de Historial Conectado)
                if not df_completo.empty and sn in df_completo['N_Serie'].astype(str).values:
                    st.info(f"Vínculo detectado: Agregando nueva intervención al historial del motor SN: {sn}")
                # Concatenamos la nueva fila al historial general
                df_actualizado = pd.concat([df_completo, df_nueva], ignore_index=True)
                df_actualizado = df_actualizado.drop_duplicates()
                
                try:
                    # Intentar subir a Google Sheets
                    conn.update(data=df_actualizado)
                    
                    # 4. LIMPIAR CACHÉ (Muy importante para que aparezca en el historial)
                    st.cache_data.clear() 
                    
                    st.success(f"✅ Motor {t} guardado en la base de datos.")
                    st.balloons()
                    
                    # Preparamos la etiqueta para descargar (AFUERA del formulario después)
                    st.session_state.etiqueta_lista = generar_etiqueta_honeywell(t, sn, p)
                    st.session_state.motor_registrado = t
                    
                except Exception as e:
                    st.error(f"❌ Error al conectar con Google Sheets: {e}")
            else:
                st.error("⚠️ El TAG y el Responsable son obligatorios.")

    # 2. EL BOTÓN DE DESCARGA VA AFUERA (Sin espacios al principio del 'if')
    if "etiqueta_lista" in st.session_state and st.session_state.etiqueta_lista:
        st.divider()
        st.info(f"📋 Etiqueta lista para motor: {st.session_state.motor_registrado}")
        st.image(st.session_state.etiqueta_lista, width=300)
        
        st.download_button(
            label="💾 Descargar Etiqueta (PNG)",
            data=st.session_state.etiqueta_lista,
            file_name=f"Etiqueta_{st.session_state.motor_registrado}.png",
            mime="image/png"
        )
  
elif modo == "Historial y QR":
    st.title("🔍 Consulta y Gestión de Motores")
    
    if not df_completo.empty:
        # 1. Limpieza y preparación de datos (Blindada)
        df_completo['N_Serie'] = df_completo['N_Serie'].fillna('S/S').astype(str).str.strip()
        df_completo['Tag'] = df_completo['Tag'].fillna('S/T').astype(str).str.strip()

        # 2. Crear lista de opciones ÚNICA POR SERIE (Muestra el TAG MÁS RECIENTE)
        df_temp = df_completo.copy()
        
        # Convertimos la columna Fecha a formato fecha real para poder ordenar
        df_temp['Fecha_DT'] = pd.to_datetime(df_temp['Fecha'], dayfirst=True, errors='coerce')
        
        # ORDENAMOS: Lo más nuevo PRIMERO (descendente)
        df_temp = df_temp.sort_values('Fecha_DT', ascending=False)

        # MANTENEMOS EL PRIMERO (que ahora es el más nuevo gracias al sort anterior)
        df_ultimos = df_temp.drop_duplicates(subset=['N_Serie'], keep='first')

        # Creamos la lista de opciones
        opciones_base = [
            f"{row['Tag']} | SN: {row['N_Serie']}" 
            for _, row in df_ultimos.iterrows() 
            if str(row['N_Serie']) != 'nan'
        ]
        
        # Ordenamos la lista alfabéticamente para que sea fácil buscar
        opciones = [""] + sorted(opciones_base)
        
        # 3. LÓGICA DE RECONOCIMIENTO DE QR
        params = st.query_params
        # Buscamos en todos los posibles nombres de parámetros
        qr_valor = params.get("serie") or params.get("tag") or params.get("Serie") or params.get("Tag")
        
        idx_buscador = 0
        if qr_valor:
            v_qr = str(qr_valor).strip().upper()
            for i, op in enumerate(opciones):
                if v_qr in op.upper():
                    idx_buscador = i
                    break
        
        # 4. EL SELECTOR ÚNICO
        # Protección extra por si el índice se sale de rango
        if idx_buscador >= len(opciones):
            idx_buscador = 0

        seleccion = st.selectbox(
            "🔍 Seleccione o Busque el Motor:", 
            opciones, 
            index=idx_buscador, 
            key="buscador_final_marpi"
        )

        if seleccion != "": 
            # 1. Extraemos la serie (nuestro identificador único)
            serie_final = seleccion.split(" | SN: ")[1] if " | SN: " in seleccion else ""
            
            # 2. Filtramos TODO el historial de esa serie (sin importar el Tag)
            df_historial = df_completo[df_completo['N_Serie'] == serie_final].copy()
            
            if not df_historial.empty:
                # 3. Convertir fecha para ordenar: lo más nuevo DEBE ir arriba
                df_historial['Fecha_DT'] = pd.to_datetime(df_historial['Fecha'], dayfirst=True, errors='coerce')
                df_historial = df_historial.sort_values('Fecha_DT', ascending=False)
                
                # 4. Obtener la info más actual (la primera fila después de ordenar)
                motor_info = df_historial.iloc[0]
                
                # Usamos el Tag del último registro guardado (el más nuevo)
                ultimo_tag = str(motor_info.get('Tag', 'S/D'))

                # --- PANEL SUPERIOR ---
                with st.container(border=True):
                    col_qr, col_info = st.columns([1, 2])
                    url_app = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?tag={serie_final}"
                    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url_app}"
                    
                    with col_qr:
                        st.image(qr_api, width=120) 
                    with col_info:
                        st.subheader(f"Ⓜ️ {ultimo_tag}")
                        st.info(f"Número de Serie: **{serie_final}**")

                # Dentro de la sección Historial y QR...

                def enviar_a_formulario_con_datos(tarea_tipo):
                    # 1. Guardar TODOS los datos del motor en el diccionario
                    st.session_state['datos_motor_auto'] = {
                        'tag': str(motor_info.get('Tag', '')),
                        'serie': str(motor_info.get('N_Serie', '')),
                        'potencia': str(motor_info.get('Potencia', '')),
                        'tension': str(motor_info.get('Tension', '')),
                        'corriente': str(motor_info.get('Corriente', '')),
                        'rpm': str(motor_info.get('RPM', '-')),
                        'carcasa': str(motor_info.get('Carcasa', '')), # O 'Frame' según tu Excel
                        'r_la': str(motor_info.get('Rodamiento_LA', '')),
                        'r_loa': str(motor_info.get('Rodamiento_LOA', ''))
                    }
                    
                    # 2. Cambiar la navegación
                    if tarea_tipo == "Lubricación":
                        st.session_state.navegacion_actual = "Relubricacion"
                    elif tarea_tipo == "Megado":
                        st.session_state.navegacion_actual = "Mediciones de Campo"
                    else:
                        st.session_state.navegacion_actual = "Nuevo Registro"
                    
                    st.rerun()
                
                st.divider()
                st.write("### ⚡ Acciones Rápidas")
                col_A, col_B, col_C = st.columns(3)
                
                with col_A:
                    if st.button("🛢️ Lubricar", use_container_width=True, key="btn_lub_hist"):
                        enviar_a_formulario_con_datos("Lubricación")
                with col_B:
                    if st.button("🔌 Megar", use_container_width=True, key="btn_meg_hist"):
                        enviar_a_formulario_con_datos("Megado")
                with col_C:
                    if st.button("📝 Reparación", use_container_width=True, key="btn_rep_hist"):
                        enviar_a_formulario_con_datos("Reparación General")
                # --- 6. HISTORIAL DE INTERVENCIONES (MANTENIENDO TU FORMATO) ---
                st.divider()
                st.subheader("📜 Historial de Intervenciones")
                
                hist_m = df_historial.iloc[:] # Lo más nuevo arriba
                for idx, fila in hist_m.iterrows():
                    f_limpia = fila.fillna('-')
                    tarea = str(f_limpia.get('Tipo_Tarea', '-')).strip()
                    fecha = str(f_limpia.get('Fecha', '-'))
                    tag_h = str(f_limpia.get('Tag', ultimo_tag))
                    resp_h = str(f_limpia.get('Responsable', '-'))
                    
                    titulo_card = f"🗓️ {tarea}" if tarea not in ["-", "nan"] else "📝 Registro / Mantenimiento"

                    # --- INICIO DEL CONTENEDOR PARA CAPTURA (Fondo oscuro preservado) ---
                    st.markdown(f'<div id="ficha_{idx}" style="background-color: #0e1117; padding: 10px;">', unsafe_allow_html=True)
                    with st.container(border=True):
                        st.markdown(f"### {titulo_card} - {fecha}")
                        st.markdown(f"**🆔 TAG:** `{tag_h}`  |  **👤 RESP:** `{resp_h}`")
                        st.divider() 
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**📋 Datos de Placa:**")
                            st.write(f"**Serie:** {f_limpia.get('N_Serie', '-')}")
                            st.write(f"**Potencia:** {f_limpia.get('Potencia', '-')}")
                            st.write(f"**RPM:** {f_limpia.get('RPM', '-')}")
                            st.write(f"**FRAME** {f_limpia.get('Carcasa', '-')}") 
                        with col2:
                            if "Lubricación" in tarea or "Relubricacion" in tarea:
                                st.markdown("**🛢️ Detalle Lubricación:**")
                                st.info(f"**LA:** {f_limpia.get('Rodamiento_LA', '-')} ({f_limpia.get('Gramos_LA', '0')}g)\n\n**LOA:** {f_limpia.get('Rodamiento_LOA', '-')} ({f_limpia.get('Gramos_LOA', '0')}g)")
                            elif "Mediciones" in tarea or "Megado" in tarea:
                                st.markdown("**⚡ Resumen Eléctrico:**")
                                st.warning(f"**Aislamiento T-U1:**\n\n{f_limpia.get('RT_TU1', '-')} GΩ")
                                with st.expander("🔍 Ver todas las Medidas"):
                                    m1, m2, m3 = st.columns(3)
                                    with m1:
                                        st.caption(f"T-V1: {f_limpia.get('RT_TV1', '-')}")
                                        st.caption(f"T-W1: {f_limpia.get('RT_TW1', '-')}")
                                    with m2:
                                        st.caption(f"W1-V1: {f_limpia.get('RB_WV1', '-')}")
                                        st.caption(f"V1-U1: {f_limpia.get('RB_VU1', '-')}")
                                    with m3:
                                        st.caption(f"U1-U2: {f_limpia.get('RI_U1U2', '-')}")
                                        st.caption(f"W1-W2: {f_limpia.get('RI_W1W2', '-')}")
                            else:
                                st.markdown("**🛠️ Detalles Técnicos:**")
                                st.success(f"**Rod. LA:** {f_limpia.get('Rodamiento_LA', '-')}\n\n**Rod. LOA:** {f_limpia.get('Rodamiento_LOA', '-')}")

                        st.divider()
                        st.markdown("**📝 Descripción/Observaciones:**")
                        st.write(f_limpia.get('Descripcion', 'Sin notas adicionales.'))
                        
                        if str(f_limpia.get('Trabajos_Externos', '-')) not in ['-', 'nan', '']:
                            st.info(f"**🏗️ Taller Externo:** {f_limpia.get('Trabajos_Externos')}")
                        if str(f_limpia.get('Notas', '-')) not in ['-', 'nan', '']:
                            st.caption(f"**📌 Notas:** {f_limpia.get('Notas')}")
                    st.markdown('</div>', unsafe_allow_html=True) 

                    # --- LÓGICA DE DETALLES PARA FOTO Y BOTONES ---
                    campos_electricos = ['RT_TU1', 'RT_TV1', 'RT_TW1', 'RB_WV1', 'RB_VU1', 'RB_UW1', 'RI_U1U2', 'RI_V1V2', 'RI_W1W2', 'RI_U1V1', 'RI_V1W1', 'RI_W1U1']
                    detalles_foto = ""
                    if "Mediciones" in tarea or "Megado" in tarea:
                        detalles_foto = "<b>Mediciones Eléctricas:</b><br>"
                        for i, c in enumerate(campos_electricos):
                            v = f_limpia.get(c, '-')
                            if v != '-': detalles_foto += f"{c}: {v} | "
                            if (i + 1) % 3 == 0: detalles_foto += "<br>"
                    elif "Lubricación" in tarea or "Relubricacion" in tarea:
                        detalles_foto = f"<b>Rodamiento LA:</b> {f_limpia.get('Rodamiento_LA')} ({f_limpia.get('Gramos_LA')}g)<br><b>Rodamiento LOA:</b> {f_limpia.get('Rodamiento_LOA')} ({f_limpia.get('Gramos_LOA')}g)"
                    else:
                        detalles_foto = f"Rod. LA: {f_limpia.get('Rodamiento_LA', '-')} | Rod. LOA: {f_limpia.get('Rodamiento_LOA', '-')}"

                    # Botón de Descarga
                    html_boton = boton_descarga_pro(tag_h, fecha, tarea, resp_h, f_limpia.get('N_Serie', '-'), f_limpia.get('Potencia', '-'), f_limpia.get('RPM', '-'), f_limpia.get('Carcasa', '-'), detalles_foto, "", f_limpia.get('Descripcion', '-'))
                    components.html(html_boton, height=80)
                    
                    # Botón Honeywell
                    try:
                        s_local = str(f_limpia.get('N_Serie', '-'))
                        p_local = str(f_limpia.get('Potencia', '-'))
                        img_bytes_h = generar_etiqueta_honeywell(tag_h, s_local, p_local)
                        if img_bytes_h:
                            import base64
                            b64_img_h = base64.b64encode(img_bytes_h).decode('utf-8')
                            boton_h_html = f"""
                            <div style="text-align: center; margin-top: -15px;">
                                <button id="btnH_{idx}" style="width:100%; background:#28a745; color:white; padding:8px; border:none; border-radius:5px; font-weight:bold; cursor:pointer; height:38px; font-size:12px;">🖨️ IMPRIMIR ETIQUETA HONEYWELL</button>
                            </div>
                            <script>
                            document.getElementById('btnH_{idx}').onclick = function() {{
                                const win = window.open('', '', 'width=800,height=600');
                                win.document.write('<html><head><style>@page {{ size: 60mm 30mm; margin: 0; }} img {{ width: 60mm; height: 30mm; }}</style></head><body>');
                                win.document.write('<img src="data:image/png;base64,{b64_img_h}" onload="setTimeout(() => {{ window.print(); window.close(); }}, 500);">');
                                win.document.write('</body></html>');
                                win.document.close();
                            }};
                            </script>"""
                            components.html(boton_h_html, height=50)
                    except: pass
                    st.divider()
elif modo == "Relubricacion":
    st.title("🛢️ Lubricación Inteligente MARPI")
    
    # --- 1. INICIALIZACIÓN ABSOLUTA (Para evitar NameError) ---
    v_la = ""
    v_loa = ""
    v_serie = ""
    info_motor = {}
    gr_la_sug = 0.0
    gr_loa_sug = 0.0

    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    # 2. Recuperar datos del QR/Historial
    datos_auto = st.session_state.get('datos_motor_auto', {})
    tag_qr = datos_auto.get('tag', '')

    # 3. Preparar el Buscador
    df_lista = df_completo.copy()
    df_lista['Busqueda_Combo'] = df_lista['Tag'].astype(str) + " | SN: " + df_lista['N_Serie'].astype(str)
   # Aseguramos que 'Busqueda_Combo' exista y esté limpia
  # --- Asegúrate de que este bloque esté alineado con el resto del código ---
    if 'Busqueda_Combo' in df_lista.columns:
    # 1. Limpiamos y convertimos a texto para evitar el TypeError
        lista_limpia = df_lista['Busqueda_Combo'].fillna("").astype(str).str.strip()
    
    # 2. Quitamos duplicados y vacíos
        lista_final = [x for x in lista_limpia.unique().tolist() if x != ""]
    
    # 3. El sorted ahora sí funcionará
        opciones_combo = [""] + sorted(lista_final)
    else:
        opciones_combo = [""]
    
    indice_predef = 0
    if tag_qr:
        for i, opt in enumerate(opciones_combo):
            if opt.startswith(tag_qr):
                indice_predef = i
                break

    seleccion_full = st.selectbox(
        "Seleccione el Motor (busque por TAG o N° de Serie)", 
        options=opciones_combo,
        index=indice_predef,
        key=f"busqueda_relub_{st.session_state.form_id}"
    )

    tag_seleccionado = seleccion_full.split(" | ")[0].strip() if seleccion_full else ""

    # --- 4. CARGA DE DATOS SI HAY SELECCIÓN ---
    if tag_seleccionado:
        fila_motor = df_lista[df_lista['Tag'] == tag_seleccionado]
        if not fila_motor.empty:
            info_motor = fila_motor.iloc[-1]
            # Llenamos las variables con lo que hay en el Excel
            v_la = str(info_motor.get('Rodamiento_LA', '')).replace('nan', '').upper()
            v_loa = str(info_motor.get('Rodamiento_LOA', '')).replace('nan', '').upper()
            v_serie = str(info_motor.get('N_Serie', '')).replace('nan', '')

            # Mostramos alertas de seguridad
            st.markdown("---")
            es_sellado = any(x in v_la or x in v_loa for x in ["2RS", "ZZ"])
            if es_sellado:
                st.error(f"🚫 **AVISO: RODAMIENTOS SELLADOS ({v_la} / {v_loa}). NO LUBRICAR.**")
            else:
                st.success("✅ **EQUIPO APTO PARA LUBRICACIÓN**")

    st.divider()

    # --- 5. INPUTS DE RODAMIENTOS (v_la ya existe siempre aquí) ---
    col1, col2 = st.columns(2)
    
    # Usamos text_input para que el técnico pueda corregir el rodamiento si es distinto al de placa
    rod_la_final = col1.text_input("Rodamiento LA", value=v_la, key=f"la_input_{st.session_state.form_id}").upper()
    rod_loa_final = col2.text_input("Rodamiento LOA", value=v_loa, key=f"loa_input_{st.session_state.form_id}").upper()
    
    # Calculamos gramos basados en lo que dice el input (por si se cambió el rodamiento)
    gr_la_sug = calcular_grasa_marpi(rod_la_final)
    gr_loa_sug = calcular_grasa_marpi(rod_loa_final)
    
    col1.caption(f"Sugerido: {gr_la_sug} g")
    col2.caption(f"Sugerido: {gr_loa_sug} g")

    # --- 6. FORMULARIO FINAL ---
    with st.form(key=f"form_lub_{st.session_state.form_id}"):
        tecnico = st.text_input("Técnico Responsable")
        
        c1, c2 = st.columns(2)
        gr_real_la = c1.number_input("Gramos Reales LA", value=float(gr_la_sug))
        gr_real_loa = c2.number_input("Gramos Reales LOA", value=float(gr_loa_sug))
        
        grasa_t = st.selectbox("Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus"])
        notas = st.text_area("Notas / Observaciones")
        
        if st.form_submit_button("💾 GUARDAR REGISTRO"):
            if tag_seleccionado and tecnico:
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": tag_seleccionado,
                    "N_Serie": v_serie,
                    "Potencia": info_motor.get('Potencia', 'S/D'),
                    "Tipo_Tarea": "Relubricacion",
                    "Responsable": tecnico,
                    "Rodamiento_LA": rod_la_final,
                    "Rodamiento_LOA": rod_loa_final,
                    "Gramos_LA": gr_real_la,
                    "Gramos_LOA": gr_real_loa,
                    "Tipo_Grasa": grasa_t,
                    "Notas": notas,
                    "Descripcion": f"LUBRICACIÓN REALIZADA: {grasa_t}"
                }
                
                # Guardado usando la conexión GLOBAL
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)

                st.success(f"✅ ¡Registro de {tag_seleccionado} guardado!")
                st.balloons()
                st.cache_data.clear()
                st.session_state.form_id += 1
                import time
                time.sleep(2)
                st.rerun()
            else:
                st.error("⚠️ Falta seleccionar el Motor o ingresar el Técnico.")
       
    st.divider()
    
    # 6. LOS BOTONES DE DESCARGA Y LIMPIEZA VAN AQUÍ AFUERA
    col_descarga, col_limpiar = st.columns(2)
    
    with col_descarga:
        if "pdf_buffer" in st.session_state and st.session_state.pdf_buffer is not None:
            nombre_final = st.session_state.get("archivo_nombre", f"Reporte_Lubricacion_{tag_seleccionado}")
            st.download_button(
                label=f"📥 Descargar Reporte",
                data=st.session_state.pdf_buffer,
                file_name=f"{nombre_final}.pdf",
                mime="application/pdf",
                key="btn_descarga_lub_final"
            )
        else:
            st.info("ℹ️ El reporte se habilitará después de guardar.")

    with col_limpiar:
        # AHORA ESTE BOTÓN YA NO DARÁ ERROR
        if st.button("🔄 Limpiar y nuevo registro", use_container_width=True):
            st.session_state.pdf_buffer = None
            st.session_state.tag_buffer = None
            st.rerun()
                
elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo (Megado y Continuidad)")
    fecha_hoy = date.today()
    
    # 1. Inicialización de Memoria
    if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
    if "cnt_meg" not in st.session_state: st.session_state.cnt_meg = 0
        
    # 2. RECUPERACIÓN PREVIA (Fuera del form para evitar NameError)
    datos_auto = st.session_state.get('datos_motor_auto', {})
    tag_inicial = datos_auto.get('tag', '')
    serie_inicial = datos_auto.get('serie', '')
    
    n_serie_sug = serie_inicial
    # Si tenemos un TAG pero no serie, buscamos en el DF antes de entrar al form
    if tag_inicial and not n_serie_sug:
        if not df_completo.empty:
            busq = df_completo[df_completo['Tag'] == tag_inicial].tail(1)
            if not busq.empty: 
                n_serie_sug = str(busq['N_Serie'].values[0])
    
    # --- 3. FORMULARIO ---
    with st.form(f"form_megado_{st.session_state.cnt_meg}"):
        col1, col2, col3 = st.columns(3)
        
        # Agregamos las keys únicas y usamos n_serie_sug ya calculada
        t = col1.text_input("TAG del Motor:", value=tag_inicial, key="tag_med_field").upper()
        # Eliminamos la duplicidad: un solo input para N° de Serie
        n_serie = col2.text_input("N° de Serie:", value=n_serie_sug, key="serie_med_field")
        resp = col3.text_input("Responsable:", key="resp_med_field")

        col_eq1, col_eq2 = st.columns(2)
        equipo_megado = col_eq1.selectbox("Equipo:", ["Megger MTR 105", "Fluke 1507", "Otro"])
        tension_prueba = col_eq2.selectbox("Tensión:", ["500V", "1000V", "2500V", "5000V"])

        st.divider()
        
        # --- SECCIÓN 2: TODAS LAS MEDICIONES (Mantenidas exactamente igual) ---
        st.subheader("📊 Megado a Tierra (Aislamiento GΩ)")
        c1, c2, c3 = st.columns(3)
        tv1 = c1.text_input("T - V1")
        tu1 = c2.text_input("T - U1")
        tw1 = c3.text_input("T - W1")
        
        st.subheader("📊 Megado entre Bobinas (GΩ)")
        c4, c5, c6 = st.columns(3)
        wv1 = c4.text_input("W1 - V1")
        wu1 = c5.text_input("W1 - U1")
        vu1 = c6.text_input("V1 - U1")

        st.subheader("📏 Resistencia Interna (Continuidad Ω)")
        c7, c8, c9 = st.columns(3)
        u1u2 = c7.text_input("U1 - U2")
        v1v2 = c8.text_input("V1 - V2")
        w1w2 = c9.text_input("W1 - W2")

        st.subheader("🔌 Megado de Línea (MΩ / GΩ)")
        c10, c11, c12 = st.columns(3)
        tl1 = c10.text_input("T - L1 (MΩ)")
        tl2 = c11.text_input("T - L2 (MΩ)")
        tl3 = c12.text_input("T - L3 (MΩ)")
        
        c13, c14, c15 = st.columns(3)
        l1l2 = c13.text_input("L1 - L2")
        l1l3 = c14.text_input("L1 - L3")
        l2l3 = c15.text_input("L2 - L3")

        obs = st.text_area("Observaciones")

        # EL BOTÓN DE GUARDADO (Cierra el bloque with st.form)
        submitted = st.form_submit_button("💾 GUARDAR MEDICIONES")
        
        if submitted:
            if t and resp:
                # Buscar datos de placa para el PDF
                busqueda = df_completo[df_completo['Tag'] == t].tail(1)
                info = busqueda.iloc[0].to_dict() if not busqueda.empty else {}
                
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                    "Tag": t, "N_Serie": n_serie, "Responsable": resp,
                    "Tipo_Tarea": "Mediciones de Campo",
                    "Potencia": info.get("Potencia", "-"),
                    "Tension": info.get("Tension", "-"),
                    "RPM": info.get("RPM", "-"),
                    "Descripcion": f"Prueba: {equipo_megado} a {tension_prueba}. {obs}",
                    "RT_TV1": tv1, "RT_TU1": tu1, "RT_TW1": tw1,
                    "RB_WV1": wv1, "RB_WU1": wu1, "RB_VU1": vu1,
                    "RI_U1U2": u1u2, "RI_V1V2": v1v2, "RI_W1W2": w1w2,
                    "ML_L1": tl1, "ML_L2": tl2, "ML_L3": tl3,
                    "ML_L1L2": l1l2, "ML_L1L3": l1l3, "ML_L2L3": l2l3
                }

                # 3. Guardado usando la conexión global 'conn'
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final) 
                
                # 4. Limpieza y éxito
                st.cache_data.clear()
                st.success(f"✅ ¡Todo guardado! Reporte listo para {t}")
                st.balloons()
                
                # Opcional: un pequeño sleep y rerun para refrescar la tabla
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("⚠️ Falta TAG o Responsable.")

    # 3. BOTÓN DE DESCARGA (Fuera del formulario)
    # Importante: Asegúrate de que 't' esté disponible aquí o usa st.session_state
    if st.session_state.get("pdf_buffer") is not None:
        st.download_button(
            label=f"📥 Descargar Reporte",
            data=st.session_state.pdf_buffer,
            file_name=f"Reporte_{t if 't' in locals() else 'Motor'}.pdf",
            mime="application/pdf"
        )
    
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")











































































































































































































































































































































































































































































































































































































































































































































































































































































































































































