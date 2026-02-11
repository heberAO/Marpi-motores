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
        from io import BytesIO

        # 1. Lienzo (600x300 px)
        etiqueta = Image.new('RGB', (600, 300), (255, 255, 255))
        draw = ImageDraw.Draw(etiqueta)

       # 2. QR (LADO IZQUIERDO) - Ahora vinculado a la SERIE
        qr = qrcode.QRCode(version=1, box_size=12, border=1)
        # EL CAMBIO CLAVE:
        qr.add_data(f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?serie={serie_final}")
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
        
        buf = BytesIO()
        final_bw.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        print(f"Error: {e}")
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
    datos_auto = st.session_state.get('datos_motor_auto', {})
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    with st.form(key=f"alta_motor_{st.session_state.form_key}"):
        # --- CAMPOS DE ENTRADA (Mismo diseño anterior) ---
        c1, c2, c3 = st.columns([2, 2, 1])
        t = c1.text_input("TAG/ID MOTOR", value=datos_auto.get('tag', '')).upper()
        sn = c2.text_input("N° de Serie", value=datos_auto.get('serie', '')).upper()
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
        # 1. Limpieza de datos para evitar errores de búsqueda
        df_completo['N_Serie'] = df_completo['N_Serie'].astype(str).str.strip()
        df_completo['Tag'] = df_completo['Tag'].astype(str).str.strip()

        # 2. Crear lista de opciones
        df_completo['Busqueda_Combo'] = df_completo['Tag'] + " | SN: " + df_completo['N_Serie']
        opciones = [""] + sorted(df_completo['Busqueda_Combo'].unique().tolist())
        
        # 3. CAPTURA DE QR (Prioridad a tus etiquetas de planta)
        qr_valor = st.query_params.get("tag") or st.query_params.get("serie") or st.query_params.get("Serie")
        
        idx_automatico = 0 
        if qr_valor:
            v_qr = str(qr_valor).strip().upper()
            for i, op in enumerate(opciones):
                # IMPORTANTE: Buscamos el valor en TODA la cadena (Tag + Serie)
                # Esto hace que encuentre tanto los QR que tienen el Nombre como los que tienen la Serie
                if v_qr in op.upper():
                    idx_automatico = i
                    break

        # 4. EL SELECTOR
        seleccion = st.selectbox(
            "Busca por TAG o N° de Serie:", 
            opciones, 
            index=idx_automatico, 
            key="buscador_marpi_universal"
        )
        if seleccion:
            # EXTRAEMOS LA SERIE (Es el único dato que no cambia)
            # Usamos split y tomamos la parte de la derecha para no confundir con el TAG
            serie_final = seleccion.split(" | SN: ")[1] if " | SN: " in seleccion else ""
            
            # FILTRAR EL HISTORIAL
            historial_motor = df_completo[df_completo['N_Serie'] == serie_final].copy()
            
            if not historial_motor.empty:
                # Definir ultimo_tag para las tarjetas de abajo
                ultimo_tag = str(historial_motor.iloc[-1]['Tag'])
                
                # --- PANEL SUPERIOR Y QR ---
                with st.container(border=True):
                    col_qr, col_info = st.columns([1, 2])
                    
                    # Generamos el link usando la serie_final que acabamos de extraer
                    url_app = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?serie={serie_final}"
                    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url_app}"
                    
                    with col_qr:
                        st.image(qr_api, width=120)
                    with col_info:
                        st.subheader(f"Ⓜ️ {ultimo_tag}")
                        st.info(f"Número de Serie: **{serie_final}**")
            # --- BOTONES DE ACCIÓN RÁPIDA ---
            st.subheader("➕ Nueva Tarea")
            c1, c2, c3 = st.columns(3)
            
            # Extraemos los datos actuales del motor seleccionado para pasarlos al formulario
            # 'historial_motor' ya lo filtraste arriba, tomamos la última fila
            if not historial_motor.empty:
                motor_info = historial_motor.iloc[-1]
                datos_para_pasar = {
                    'tag': motor_info.get('Tag', ''),
                    'serie': motor_info.get('N_Serie', ''),
                    'potencia': motor_info.get('Potencia', ''),
                    'nombre': motor_info.get('Nombre_Empresa', '') # Ajusta al nombre de tu columna
                }
            
            with c1:
                if st.button("🛠️ Reparar", use_container_width=True):
                    st.session_state.datos_motor_auto = datos_para_pasar # <--- MEMORIA
                    st.session_state.seleccion_manual = "Nuevo Registro"
                    st.rerun()
            with c2:
                if st.button("🛢️ Engrasar", use_container_width=True):
                    st.session_state.datos_motor_auto = datos_para_pasar # <--- MEMORIA
                    st.session_state.seleccion_manual = "Relubricacion"
                    st.rerun()
            with c3:
                if st.button("⚡ Megar", use_container_width=True):
                    st.session_state.datos_motor_auto = datos_para_pasar # <--- MEMORIA
                    st.session_state.seleccion_manual = "Mediciones de Campo"
                    st.rerun() 

            st.divider()
            st.subheader("📜 Historial de Intervenciones")
            
            if not historial_motor.empty:
                hist_m = historial_motor.iloc[::-1] # Lo más nuevo arriba

                for idx, fila in hist_m.iterrows():
                    # 1. Limpiamos los datos
                    f_limpia = fila.fillna('-') 
                    
                    # 2. Variables de texto
                    tarea = str(f_limpia.get('Tipo_Tarea', '-')).strip()
                    fecha = str(f_limpia.get('Fecha', '-'))
                    tag_h = str(f_limpia.get('Tag', ultimo_tag))
                    resp_h = str(f_limpia.get('Responsable', '-'))
                    
                    if tarea == "-" or tarea.lower() == "nan":
                        titulo_card = "📝 Registro / Mantenimiento"
                    else:
                        titulo_card = f"🗓️ {tarea}"

                    # --- INICIO DEL CONTENEDOR PARA CAPTURA ---
                    # Envolvemos TODO tu diseño en este div para que la foto lo encuentre
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
                            elif "Mediciones" in tarea:
                                st.markdown("**⚡ Resumen Eléctrico:**")
                                m_tierra = f_limpia.get('RT_TU1', '-')
                                st.warning(f"**Aislamiento T-U1:**\n\n{m_tierra} GΩ")
                                
                                # Nota: Los expanders pueden salir cerrados en la captura, es normal en HTML2Canvas
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
                                # Estas líneas deben estar más a la derecha que el else
                                st.markdown("**🛠️ Detalles Técnicos:**")
                                st.success(f"**Rod. LA:** {f_limpia.get('Rodamiento_LA', '-')}\n\n**Rod. LOA:** {f_limpia.get('Rodamiento_LOA', '-')}")

                        st.divider()
                        st.markdown("**📝 Descripción/Observaciones:**")
                        st.write(f_limpia.get('Descripcion', 'Sin notas adicionales.'))
                        
                        if str(f_limpia.get('Trabajos_Externos', '-')) not in ['-', 'nan', '']:
                            st.info(f"**🏗️ Taller Externo:** {f_limpia.get('Trabajos_Externos')}")
                        
                        if str(f_limpia.get('Notas', '-')) not in ['-', 'nan', '']:
                            st.caption(f"**📌 Notas:** {f_limpia.get('Notas')}")

                    # Estas tres líneas se alinean con el 'with' de arriba
                    st.markdown('</div>', unsafe_allow_html=True) 
                    
                   # --- PREPARAMOS LOS DETALLES PARA LA FOTO ---
                    detalles_foto = ""
                    
                    if "Mediciones" in tarea or "Megado" in tarea:
                        # Lista de todas las mediciones posibles (las 15 que mencionas)
                        campos_electricos = [
                            'RT_TU1', 'RT_TV1', 'RT_TW1', 
                            'RB_WV1', 'RB_VU1', 'RB_UW1',
                            'RI_U1U2', 'RI_V1V2', 'RI_W1W2',
                            'RI_U1V1', 'RI_V1W1', 'RI_W1U1' # Agregá aquí los que falten hasta completar los 15
                        ]
                        detalles_foto = "<b>Mediciones Eléctricas:</b><br>"
                        for i, c in enumerate(campos_electricos):
                            valor = f_limpia.get(c, '-')
                            if valor != '-':
                                detalles_foto += f"{c}: {valor} | "
                                # Cada 3 mediciones, mete un salto de línea para que sea legible
                                if (i + 1) % 3 == 0:
                                    detalles_foto += "<br>"
                    
                    elif "Lubricación" in tarea or "Relubricacion" in tarea:
                        detalles_foto = f"<b>Rodamiento LA:</b> {f_limpia.get('Rodamiento_LA')} ({f_limpia.get('Gramos_LA')}g)<br>"
                        detalles_foto += f"<b>Rodamiento LOA:</b> {f_limpia.get('Rodamiento_LOA')} ({f_limpia.get('Gramos_LOA')}g)"
                    
                    else:
                        detalles_foto = f"Rod. LA: {f_limpia.get('Rodamiento_LA', '-')} | Rod. LOA: {f_limpia.get('Rodamiento_LOA', '-')}"

                    # --- AGREGAMOS TRABAJOS EXTERNOS Y NOTAS SI EXISTEN ---
                    info_extra = ""
                    taller = str(f_limpia.get('Trabajos_Externos', '-'))
                    notas_ad = str(f_limpia.get('Notas', '-'))
                    
                    if taller not in ['-', 'nan', '']:
                        info_extra += f"<br><b>🏗️ Taller Externo:</b> {taller}"
                    if notas_ad not in ['-', 'nan', '']:
                        info_extra += f"<br><b>📌 Notas:</b> {notas_ad}"

                    # Esta línea debe estar verticalmente igual a los 'if' de arriba
                    html_boton = boton_descarga_pro(
                        tag_h, 
                        fecha, 
                        tarea, 
                        resp_h, 
                        f_limpia.get('N_Serie', '-'), 
                        f_limpia.get('Potencia', '-'), 
                        f_limpia.get('RPM', '-'),
                        detalles_foto, 
                        info_extra, 
                        f_limpia.get('Descripcion', '-')
                    )
                    components.html(html_boton, height=80)
                    # --- GENERAR IMAGEN DE ETIQUETA ---
                    # --- 1. GENERAR IMAGEN ---
                    img_bytes = generar_etiqueta_honeywell(
                        tag_h, 
                        f_limpia.get('N_Serie', '-'), 
                        f_limpia.get('Potencia', '-')
                    )
                    
                    if img_bytes:
                        # --- BLOQUE DEL BOTÓN CORREGIDO ---
                        # 1. Preparar la imagen
                        # --- 1. PREPARAR LA IMAGEN ---
                        import base64
                        b64_img = base64.b64encode(img_bytes).decode('utf-8')
                        
                        # --- 2. EL BLOQUE DEL BOTÓN (TODO JUNTO AQUÍ) ---
                        boton_html = f"""
                        <div style="width: 100%; text-align: center;">
                            <button id="btnMarpi" style="width:100%; background:#28a745; color:white; padding:15px; border:none; border-radius:10px; font-weight:bold; cursor:pointer; font-family:sans-serif;">
                                🖨️ IMPRIMIR ETIQUETA MEJORADA
                            </button>
                        </div>
                        
                        <script>
                        document.getElementById('btnMarpi').onclick = function() {{
                            const win = window.open('', '', 'width=800,height=600');
                            win.document.write('<html><head><style>');
                            
                            // AQUÍ ES DONDE VAN LAS LÍNEAS QUE DABAN ERROR (DENTRO DEL SCRIPT)
                            win.document.write('@page {{ size: 60mm 30mm; margin: 0 !important; }}');
                            win.document.write('body {{ margin: 0; padding: 0; }}');
                            win.document.write('img {{ width: 60mm; height: 30mm; object-fit: contain; image-rendering: pixelated; }}');
                            
                            win.document.write('</style></head><body>');
                            win.document.write('<img src="data:image/png;base64,{b64_img}" onload="setTimeout(() => {{ window.print(); window.close(); }}, 500);">');
                            win.document.write('</body></html>');
                            win.document.close();
                        }};
                        </script>
                        """
                        
                        # --- 3. MOSTRAR EN STREAMLIT ---
                        import streamlit.components.v1 as components
                        components.html(boton_html, height=100)
                                            
                    
                    st.divider()
elif modo == "Relubricacion":
    st.title("🛢️ Lubricación Inteligente MARPI")
    # ... (el resto de tu código de lubricación)
    
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
                conn.update(data=df_final)

                # 5. Interfaz de usuario
                st.session_state.tag_buffer = tag_actual
                st.session_state.form_id += 1
                st.success(f"✅ Registro de {tag_actual} guardado con éxito.")
                st.balloons()
                
                import time
                time.sleep(1)
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
    if 'current_tag' not in st.session_state: st.session_state.current_tag = "Sin_Tag"
    if "cnt_meg" not in st.session_state: st.session_state.cnt_meg = 0
        
    tag_inicial = st.session_state.get('tag_fijo', '')

    with st.form(f"form_megado_{st.session_state.cnt_meg}"):
        # --- SECCIÓN 1: DATOS BÁSICOS ---
        col1, col2, col3 = st.columns(3)
        t = col1.text_input("TAG del Motor:", value=tag_inicial).upper()
        resp = col3.text_input("Responsable:")
        
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



















































































































































































































































































































































































































































































































































































































































































































































































































































































