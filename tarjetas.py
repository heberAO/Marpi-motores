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

def boton_descarga_pro(tag, fecha, tarea, resp, serie, pot, rpm, detalles, extra, obs):
    st_btn = 'width:100%;background:#007bff;color:white;padding:15px;border:none;border-radius:10px;font-weight:bold;cursor:pointer;font-family:sans-serif;'
    
    contenido = f"""
    <div style='text-align:center;border-bottom:2px solid #444;margin-bottom:15px;'>
        <h2 style='margin:0;color:#007bff;'>REPORTE TÉCNICO DE MOTOR</h2>
    </div>
    <p><b>🏷️ TAG:</b> {tag} | <b>📅 FECHA:</b> {fecha}</p>
    <p><b>🛠️ TAREA:</b> {tarea} | <b>👤 RESP:</b> {resp}</p>
    <hr>
    <div style='background:#1a1c23;padding:10px;border-radius:5px;'>
        <b>📋 DATOS DE PLACA:</b> Serie: {serie} | Pot: {pot} | RPM: {rpm}
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

        # 1. Lienzo (600x300 px)
        etiqueta = Image.new('RGB', (600, 300), (255, 255, 255))
        draw = ImageDraw.Draw(etiqueta)

       # 2. QR (LADO IZQUIERDO) - Ahora vinculado a la SERIE
        qr = qrcode.QRCode(version=1, box_size=12, border=1)
        # EL CAMBIO CLAVE:
        qr.add_data(f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?serie={serie}&exact=1")
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        img_qr = img_qr.resize((260, 260))
        etiqueta.paste(img_qr, (20, 20))

        # 3. LADO DERECHO: LOGO + N° MOTOR
        x_derecha = 310
        ancho_maximo = 275 # Espacio disponible para que no se salga de la etiqueta
        
        try:
            logo_original = Image.open("logo.png").convert('RGBA')
            base_width = 270 
            w_percent = (base_width / float(logo_original.size[0]))
            h_size = int((float(logo_original.size[1]) * float(w_percent)))
            logo_resurced = logo_original.resize((base_width, h_size), Image.Resampling.LANCZOS)
            etiqueta.paste(logo_resurced, (x_derecha, 45), logo_resurced)
            y_pos_nro = 45 + h_size + 35 
        except:
            y_pos_nro = 150

        # 4. LÓGICA DE AJUSTE DE TAMAÑO (VERSIÓN ROBUSTA)
        texto_nro = f"N°: {str(serie).upper()}"
        tamanio_fuente = 40 # Tamaño inicial deseado
        
        # Intentamos cargar la fuente, si falla usamos la de por defecto
        try:
            fuente_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            # Bucle para reducir tamaño hasta que el ancho sea menor al máximo
            while tamanio_fuente > 10:
                fuente_nro = ImageFont.truetype(fuente_path, tamanio_fuente)
                # Medimos el ancho usando getlength (más preciso para fuentes truetype)
                ancho_texto = draw.textlength(texto_nro, font=fuente_nro)
                
                if ancho_texto <= ancho_maximo:
                    break
                tamanio_fuente -= 2
        except:
            # Si falla la carga de fuente, usamos el ajuste básico
            fuente_nro = ImageFont.load_default()

        # Dibujamos el Número de Motor centrado en su columna o alineado a la izquierda
        draw.text((x_derecha + 5, y_pos_nro), texto_nro, font=fuente_nro, fill=(0,0,0))

        # 5. CONVERSIÓN PARA HONEYWELL
        final_bw = etiqueta.convert('1', dither=Image.NONE)
        
        buf = io.BytesIO()
        # CAMBIO AQUÍ: Usamos 'etiqueta' que es el nombre que definiste arriba
        etiqueta.save(buf, format='PNG') 
        return buf.getvalue()

    except Exception as e:
        st.error(f"Error interno en la función de etiqueta: {e}")
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
@st.cache_data(ttl=10) # Guarda los datos en memoria por 10 segundos
def cargar_datos_google():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 aquí asegura que SIEMPRE traiga lo fresco cuando se cumple el tiempo del cache
        return conn.read(ttl=0) 
    except Exception as e:
        st.error(f"⚠️ Error conectando a Google Sheets: {e}")
        return pd.DataFrame() # Retorna tabla vacía para no romper la app

# --- USO DE LA FUNCIÓN ---
df_completo = cargar_datos_google()

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
# --- 5. MENÚ LATERAL (SOLUCIÓN DEFINITIVA) ---
opciones_menu = ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"]

# 1. DETECCIÓN DE SALTO (Prioridad máxima)
# Si venimos desde un botón del historial, forzamos la selección manual
if st.session_state.get('forzar_pestana') is not None:
    idx_destino = st.session_state.forzar_pestana
    st.session_state.seleccion_manual = opciones_menu[idx_destino]
    st.session_state.forzar_pestana = None # Limpiamos para permitir navegación libre

# 2. Sincronización inicial (Solo si la app arranca de cero)
if "seleccion_manual" not in st.session_state:
    # Usamos el indice_inicio definido arriba (que es 1 por defecto)
    st.session_state.seleccion_manual = opciones_menu[indice_inicio]

with st.sidebar:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    
    # CALCULAMOS EL ÍNDICE BASADO EN EL ESTADO DE LA SESIÓN
    try:
        # Esto hace que el radio se mueva solo cuando cambia st.session_state.seleccion_manual
        idx_radio = opciones_menu.index(st.session_state.seleccion_manual)
    except:
        idx_radio = 1

    # IMPORTANTE: El radio debe tener el index=idx_radio
    modo = st.radio(
        "SELECCIONE:", 
        opciones_menu,
        index=idx_radio,
        key="radio_navegacion_principal"
    )
    
    # Si el usuario toca el radio manualmente, actualizamos el estado
    if modo != st.session_state.seleccion_manual:
        st.session_state.seleccion_manual = modo
        st.rerun() # Forzamos recarga para que las secciones lean el nuevo modo

    # --- BOTÓN DE RESET TOTAL ---
    if st.button("🧹 Resetear Navegación"):
        st.query_params.clear()
        for k in ['datos_motor_auto', 'motor_registrado', 'etiqueta_lista', 'seleccion_manual', 'autorizado']:
            if k in st.session_state: del st.session_state[k]
        st.rerun()
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

# --- 7. SECCIONES (Aquí es donde el código continúa si pasó el stop) ---

datos_auto = st.session_state.get('datos_motor_auto', {})

if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    # ... tu código de formulario de registro ...

elif modo == "Relubricacion":
    st.title("🛢️ Registro de Relubricación")
    # AUTOCOMPLETADO PARA LUBRICACIÓN
    c1, c2 = st.columns(2)
    t = c1.text_input("TAG", value=datos_auto.get('tag', ''))
    sn = c2.text_input("N° Serie", value=datos_auto.get('serie', ''))
    # ... resto de campos de lubricación ...

elif modo == "Mediciones de Campo":
    st.title("🔌 Mediciones Eléctricas de Campo")
    # AUTOCOMPLETADO PARA MEDICIONES
    c1, c2 = st.columns(2)
    t = c1.text_input("TAG", value=datos_auto.get('tag', ''))
    sn = c2.text_input("N° Serie", value=datos_auto.get('serie', ''))
    # ... resto de campos de mediciones ...


# --- 5. SECCIONES (CON AUTOCOMPLETADO) ---
if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0
    
    # 1. Recuperamos los datos que enviamos desde el Historial
    datos_auto = st.session_state.get('datos_motor_auto', {})
    
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    
    with st.form(key=f"alta_motor_{st.session_state.form_key}"):
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
        
        # Para el RPM (selectbox), buscamos si el valor existe en la lista
        rpms_lista = ["-", "750", "1000", "1500", "3000"]
        val_rpm = datos_auto.get('rpm', '-')
        idx_rpm = rpms_lista.index(val_rpm) if val_rpm in rpms_lista else 0
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
                    "RT_TU": v_rt_tu, "RT_TV": v_rt_tv, "RT_TW": v_rt_tw,
                    "RB_UV": v_rb_uv, "RB_VW": v_rb_vw, "RB_UW": v_rb_uw,
                    "RI_U": v_ri_u, "RI_V": v_ri_v, "RI_W": v_ri_w,
                    "Descripcion": desc,
                    "Trabajos_Externos": ext,  # <--- CORREGIDO: Antes podía faltar o tener otro nombre
                    "Tipo_Tarea": "Nuevo Registro"
                }

                # 2. Convertir a DataFrame la nueva fila
                df_nueva = pd.DataFrame([nueva_fila])

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
        # 1. Limpieza rápida de datos
        df_completo['N_Serie'] = df_completo['N_Serie'].astype(str).str.strip()
        df_completo['Tag'] = df_completo['Tag'].astype(str).str.strip()

        # 2. Crear lista de opciones
        opciones_base = (df_completo['Tag'] + " | SN: " + df_completo['N_Serie']).unique().tolist()
        opciones = [""] + sorted(opciones_base)
        
        # 3. LÓGICA DE RECONOCIMIENTO DE QR
        params = st.query_params
        qr_valor = params.get("serie") or params.get("tag") or params.get("Serie") or params.get("Tag")
        
        idx_buscador = 0
        if qr_valor:
            v_qr = str(qr_valor).strip().upper()
            for i, op in enumerate(opciones):
                if v_qr in op.upper():
                    idx_buscador = i
                    break
        
        # 4. EL SELECTOR ÚNICO
        seleccion = st.selectbox(
            "🔍 Seleccione o Busque el Motor:", 
            opciones, 
            index=idx_buscador, 
            key="buscador_final_marpi"
        )

        if seleccion:
            # Extraemos la serie para filtrar el historial
            serie_final = seleccion.split(" | SN: ")[1] if " | SN: " in seleccion else ""
            historial_motor = df_completo[df_completo['N_Serie'] == serie_final].copy()
            
            if not historial_motor.empty:
                motor_info = historial_motor.iloc[-1]
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

                def enviar_a_formulario_con_datos(tarea_tipo):
                    st.session_state['datos_motor_auto'] = {
                        'tag': str(motor_info.get('Tag', '')),
                        'serie': str(motor_info.get('N_Serie', '')),
                        'potencia': str(motor_info.get('Potencia', '')),
                        'rpm': str(motor_info.get('RPM', '-')),
                        'r_la': str(motor_info.get('Rodamiento_LA', '')),
                        'r_loa': str(motor_info.get('Rodamiento_LOA', ''))
                    }
                    
                    # --- ASIGNACIÓN DE DESTINO ---
                    if tarea_tipo == "Lubricación":
                        st.session_state.forzar_pestana = 2  # Va a "Relubricacion"
                    elif tarea_tipo == "Megado":
                        st.session_state.forzar_pestana = 3  # Va a "Mediciones de Campo"
                    else:
                        st.session_state.forzar_pestana = 0  # Va a "Nuevo Registro" (Reparación)
                    
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
                
                hist_m = historial_motor.iloc[::-1] # Lo más nuevo arriba
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
                    html_boton = boton_descarga_pro(tag_h, fecha, tarea, resp_h, f_limpia.get('N_Serie', '-'), f_limpia.get('Potencia', '-'), f_limpia.get('RPM', '-'), detalles_foto, "", f_limpia.get('Descripcion', '-'))
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
    datos_auto = st.session_state.get('datos_motor_auto', {})
    
    # Ahora usamos esos datos en los inputs de esta hoja
    t = st.text_input("TAG", value=datos_auto.get('tag', ''), key="tag_relub_input")
    sn = st.text_input("N° Serie", value=datos_auto.get('serie', ''), key="serie_relub_input")
    
    if "cnt_lub" not in st.session_state:
        st.session_state.cnt_lub = 0
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    df_lista = df_completo.copy()
    # 1. Creamos la lista combinando TAG y N_Serie (tal como en Historial)
    df_lista['Busqueda_Combo'] = (
        df_lista['Tag'].astype(str) + " | SN: " + df_lista['N_Serie'].astype(str)
    )
    # 2. Generamos las opciones para el selectbox
    opciones_combo = [""] + sorted(df_lista['Busqueda_Combo'].unique().tolist())
    # 3. Buscador mejorado
    seleccion_full = st.selectbox(
        "Seleccione el Motor (busque por TAG o N° de Serie)", 
        options=opciones_combo,
        key=f"busqueda_{st.session_state.form_id}"
    )
    # 4. Extraemos el TAG puro para que el resto de tu código siga funcionando igual
    tag_seleccionado = seleccion_full.split(" | ")[0].strip() if seleccion_full else ""
    
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
            
            # Usamos la función maestra definida arriba
            g_la_calc = calcular_grasa_marpi(rod_la)
            g_loa_calc = calcular_grasa_marpi(rod_loa)
            
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

   # 4. Inputs de Rodamientos (Usa la fórmula de arriba de todo)
    col1, col2 = st.columns(2)
    with col1:
        rod_la = st.text_input("Rodamiento LA", value=v_la, key=f"la_val_{st.session_state.form_id}").upper()
        # LLAMADA CORREGIDA A LA FUNCIÓN UNIFICADA
        gr_la_sug = calcular_grasa_marpi(rod_la)
        st.metric("Sugerido LA", f"{gr_la_sug} g")

    with col2:
        rod_loa = st.text_input("Rodamiento LOA", value=v_loa, key=f"loa_val_{st.session_state.form_id}").upper()
        # LLAMADA CORREGIDA
        gr_loa_sug = calcular_grasa_marpi(rod_loa)
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
            # 1. Identificación de TAG y Responsable
            tag_actual = t if 't' in locals() else (tag_seleccionado if 'tag_seleccionado' in locals() else None)
            resp_actual = resp if 'resp' in locals() else (tecnico if 'tecnico' in locals() else None)

            if tag_actual and resp_actual:
                # 2. Creación del diccionario
                nueva = {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Tag": tag_actual,
                    "N_Serie": v_serie,
                    "Potencia": info_motor.get('Potencia', 'S/D'),
                    "Tipo_Tarea": "Relubricacion",
                    "Responsable": resp_actual,
                    "Rodamiento_LA": rod_la,
                    "Rodamiento_LOA": rod_loa,
                    "Gramos_LA": gr_real_la,
                    "Gramos_LOA": gr_real_loa,
                    "Tipo_Grasa": grasa_t,
                    "Notas": notas,  # <--- CORREGIDO: Se agrega la columna exacta del Excel
                    "Descripcion": f"LUBRICACIÓN REALIZADA: {grasa_t}"
                }
                
                # 3. Guardado
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(data=df_final)

                # 5. Interfaz de usuario
                st.session_state.tag_buffer = tag_actual
                st.session_state.form_id += 1
                st.success(f"✅ Registro de {tag_actual} guardado con éxito.")
                st.balloons()
                
                import time
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
            else:
                st.error("⚠️ Error: El TAG y el Responsable son obligatorios.")
       
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
        
    # Recuperamos datos si vienen del historial
    datos_auto = st.session_state.get('datos_motor_auto', {})
    tag_inicial = datos_auto.get('tag', '')
    serie_inicial = datos_auto.get('serie', '')
    
    # --- FORMULARIO ---
    with st.form(f"form_megado_{st.session_state.cnt_meg}"):
        col1, col2, col3 = st.columns(3)
        
        # Agregamos las keys únicas para evitar el error de Duplicate ID
        t = col1.text_input("TAG del Motor:", value=tag_inicial, key="tag_med_field").upper()
        n_serie = col2.text_input("N° de Serie:", value=n_serie_sug, key="serie_med_field")
        resp = col3.text_input("Responsable:", key="resp_med_field")
        
        # Recuperar N° Serie automáticamente
        n_serie_sug = ""
        if t:
            busq = df_completo[df_completo['Tag'] == t].tail(1)
            if not busq.empty: n_serie_sug = str(busq['N_Serie'].values[0])
        n_serie = col2.text_input("N° de Serie:", value=n_serie_sug)

        col_eq1, col_eq2 = st.columns(2)
        equipo_megado = col_eq1.selectbox("Equipo:", ["Megger MTR 105", "Fluke 1507", "Otro"])
        tension_prueba = col_eq2.selectbox("Tensión:", ["500V", "1000V", "2500V", "5000V"])

        st.divider()
        
        # --- SECCIÓN 2: TODAS LAS MEDICIONES (Recuperadas) ---
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

        # EL BOTÓN DE GUARDADO
        submitted = st.form_submit_button("💾 GUARDAR MEDICIONES")
        
        if submitted:
            if t and resp:
                # Buscar datos de placa para el PDF
                busqueda = df_completo[df_completo['Tag'] == t].tail(1)
                info = busqueda.iloc[0].to_dict() if not busqueda.empty else {}
                
                # Mapeamos TODAS las columnas que me pasaste
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"),
                    "Tag": t, "N_Serie": n_serie, "Responsable": resp,
                    "Tipo_Tarea": "Mediciones de Campo",
                    "Potencia": info.get("Potencia", "-"),
                    "Tension": info.get("Tension", "-"),
                    "RPM": info.get("RPM", "-"),
                    "Descripcion": f"Prueba: {equipo_megado} a {tension_prueba}. {obs}",
                    # Aislamiento Tierra
                    "RT_TV1": tv1, "RT_TU1": tu1, "RT_TW1": tw1,
                    # Entre bobinas
                    "RB_WV1": wv1, "RB_WU1": wu1, "RB_VU1": vu1,
                    # Continuidad
                    "RI_U1U2": u1u2, "RI_V1V2": v1v2, "RI_W1W2": w1w2,
                    # Línea
                    "ML_L1": tl1, "ML_L2": tl2, "ML_L3": tl3,
                    "ML_L1L2": l1l2, "ML_L1L3": l1l3, "ML_L2L3": l2l3
                }

                # Guardar y generar PDF
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final) 
                
                st.success(f"✅ ¡Todo guardado! Reporte listo para {t}")
                st.balloons()
            else:
                st.error("⚠️ Falta TAG o Responsable.")

    # 3. BOTÓN DE DESCARGA (Afuera)
    if st.session_state.get("pdf_buffer") is not None:
        st.download_button(
            label=f"📥 Descargar Reporte",
            data=st.session_state.pdf_buffer,
            file_name=f"Reporte_{tag_seleccionado}.pdf",
            mime="application/pdf"
        )
    
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")









































































































































































































































































































































































































































































































































































































































































































































































































































































































































