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
from PIL import Image, ImageDraw
def generar_etiqueta_honeywell(tag, serie, potencia):
    try:
        # 1. Tamaño exacto 60x40mm (480x320 px)
        ancho, alto = 480, 320
        etiqueta = Image.new('L', (ancho, alto), 255)
        draw = ImageDraw.Draw(etiqueta)

        # 2. Generar QR
        url = f"https://marpi-motores.streamlit.app/?tag={tag}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=5, 
            border=1
        )
        qr.add_data(url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('L')

        # 3. Reinsertar el Logo MARPI (Asegurate que logo.png esté en la carpeta)
        if os.path.exists("logo.png"):
            logo = Image.open("logo.png").convert("L")
            logo_dim = 55 # Tamaño para que se vea bien la M
            logo = logo.resize((logo_dim, logo_dim), Image.Resampling.LANCZOS)
            
            qr_w, qr_h = img_qr.size
            pos = ((qr_w - logo_dim) // 2, (qr_h - logo_dim) // 2)
            
            # Parche blanco para que el logo resalte
            parche = Image.new('L', (logo_dim + 10, logo_dim + 10), 255)
            img_qr.paste(parche, (pos[0]-5, pos[1]-5))
            img_qr.paste(logo, pos)

        # 4. Posicionamiento
        # Pegamos el QR a la izquierda
        etiqueta.paste(img_qr, (20, (alto - img_qr.size[1]) // 2))

        # Línea divisoria central
        draw.line([230, 35, 230, 285], fill=0, width=4)

        # 5. Textos (Convertidos a string para evitar errores)
        x_text = 250
        
        # Título
        draw.text((x_text, 40), "MARPI MOTORES S.R.L.", fill=0)
        draw.line([x_text, 58, 450, 58], fill=0, width=2)

        # Datos - Usamos str() para que no falle con números
        draw.text((x_text, 80), "IDENTIFICACIÓN:", fill=0)
        draw.text((x_text, 100), f"TAG: {str(tag).upper()}", fill=0)
        
        draw.text((x_text, 150), "DATOS TÉCNICOS:", fill=0)
        draw.text((x_text, 175), f"SERIE: {str(serie).upper()}", fill=0)
        draw.text((x_text, 205), f"POTENCIA: {str(potencia).upper()}", fill=0)

        draw.text((320, 285), "SERVICE OFICIAL", fill=0)

        # Marco exterior
        draw.rectangle([5, 5, ancho-5, alto-5], outline=0, width=3)

        # 6. Conversión final
        final_bw = etiqueta.convert('1')
        buf = BytesIO()
        final_bw.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        st.error(f"Error en diseño: {e}")
        return None
    except Exception as e:
        st.error(f"Error de legibilidad: {e}")
        return None
st.set_page_config(page_title="Marpi Motores", layout="wide")

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

# --- 2. FUNCIONES DE GENERACIÓN DE PDF ESPECIALIZADAS ---

def generar_pdf_ingreso(datos):
    try:
        pdf = FPDF()
        pdf.add_page()
        # Encabezado estándar Marpi
        pdf.set_font("Arial", 'B', 16); pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, "MARPI MOTORES S.R.L.", ln=True, align='R')
        pdf.set_font("Arial", 'B', 10); pdf.cell(0, 5, f"FECHA: {datos.get('Fecha','-')}", ln=True, align='R')
        
        pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255); pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 12, f"PROTOCOLO DE ALTA Y REGISTRO: {datos.get('Tag','-')}", ln=True, align='C', fill=True)
        pdf.ln(5); pdf.set_text_color(0)

        # Tabla de Datos de Placa
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, " 1. ESPECIFICACIONES DE PLACA", ln=True)
        pdf.set_font("Arial", '', 10)
        col_w = 45
        pdf.cell(col_w, 8, "TAG:", 1); pdf.cell(50, 8, str(datos.get('Tag','-')), 1)
        pdf.cell(col_w, 8, "N. SERIE:", 1); pdf.cell(50, 8, str(datos.get('N_Serie','-')), 1, 1)
        pdf.cell(col_w, 8, "POTENCIA:", 1); pdf.cell(50, 8, str(datos.get('Potencia','-')), 1)
        pdf.cell(col_w, 8, "TENSIÓN:", 1); pdf.cell(50, 8, str(datos.get('Tension','-')), 1, 1)
        pdf.cell(col_w, 8, "RPM:", 1); pdf.cell(50, 8, str(datos.get('RPM','-')), 1)
        pdf.cell(col_w, 8, "CARCASA:", 1); pdf.cell(50, 8, str(datos.get('Carcasa','-')), 1, 1)
        
        # Mediciones de Alta (9 campos)
        pdf.ln(5); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, " 2. MEDICIONES ELÉCTRICAS DE INGRESO", ln=True)
        pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(230,230,230)
        pdf.cell(63, 7, "AISLAMIENTO (Tierra)", 1, 0, 'C', True); pdf.cell(63, 7, "BOBINADO (Entre sí)", 1, 0, 'C', True); pdf.cell(64, 7, "RESISTENCIA (Ohm)", 1, 1, 'C', True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(63, 7, f"RT_TU: {datos.get('RT_TU','-')}", 1, 0); pdf.cell(63, 7, f"RB_UV: {datos.get('RB_UV','-')}", 1, 0); pdf.cell(64, 7, f"RI_U: {datos.get('RI_U','-')}", 1, 1)
        pdf.cell(63, 7, f"RT_TV: {datos.get('RT_TV','-')}", 1, 0); pdf.cell(63, 7, f"RB_VW: {datos.get('RB_VW','-')}", 1, 0); pdf.cell(64, 7, f"RI_V: {datos.get('RI_V','-')}", 1, 1)
        pdf.cell(63, 7, f"RT_TW: {datos.get('RT_TW','-')}", 1, 0); pdf.cell(63, 7, f"RB_UW: {datos.get('RB_UW','-')}", 1, 0); pdf.cell(64, 7, f"RI_W: {datos.get('RI_W','-')}", 1, 1)

        # Notas
        pdf.ln(5); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, " 3. DETALLES Y TRABAJOS", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, f"DESCRIPCIÓN: {datos.get('Descripcion','-')}\nEXTERNO: {datos.get('Trabajos_Externos','-')}", border=1)
        
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except: return None

def generar_pdf_lubricacion(datos):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado MARPI
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "MARPI MOTORES S.R.L.", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"REPORTE DE LUBRICACIÓN: {datos.get('Tag', 'S/D')}", ln=True, align='C')
    pdf.ln(5)

    # Datos Generales
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. IDENTIFICACIÓN DEL MOTOR", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Fecha de Intervención: {datos.get('Fecha', 'S/D')}", ln=True)
    pdf.cell(0, 8, f"Responsable: {datos.get('Responsable', 'S/D')}", ln=True)
    pdf.ln(5)

    # Detalle de Lubricación
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. DETALLES DE LUBRICACIÓN", ln=True)
    pdf.set_font("Arial", '', 11)
    
    # Rodamiento LA
    pdf.cell(0, 8, f"Rodamiento LA (Lado Acople): {datos.get('Rodamiento_LA', 'S/D')}", ln=True)
    pdf.cell(0, 8, f"Grasa Inyectada LA: {datos.get('Gramos_LA', '0')} gr.", ln=True)
    pdf.ln(2)
    
    # Rodamiento LOA
    pdf.cell(0, 8, f"Rodamiento LOA (Lado Opuesto): {datos.get('Rodamiento_LOA', 'S/D')}", ln=True)
    pdf.cell(0, 8, f"Grasa Inyectada LOA: {datos.get('Gramos_LOA', '0')} gr.", ln=True)
    pdf.ln(5)

    # Observaciones
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. OBSERVACIONES TÉCNICAS", ln=True)
    pdf.set_font("Arial", '', 11)
    desc = datos.get('Descripcion', 'Sin observaciones adicionales.')
    pdf.multi_cell(0, 8, desc)

    # Retornar el buffer para Streamlit
    return pdf.output(dest='S').encode('latin-1')
def generar_pdf_megado(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "MARPI MOTORES S.R.L.", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"REPORTE DE MEDICIONES ELÉCTRICAS: {datos.get('Tag', 'S/D')}", ln=True, align='C')
    pdf.ln(10)
    
    # Datos de Megado/Resistencia
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "MEDICIONES DE AISLAMIENTO Y RESISTENCIA", ln=True)
    pdf.set_font("Arial", '', 11)
    
    # Ejemplo de campos (ajusta según tus nombres de columna)
    pdf.cell(0, 8, f"RT_TU: {datos.get('RT_TU', '-')} | RT_TV: {datos.get('RT_TV', '-')} | RT_TW: {datos.get('RT_TW', '-')}", ln=True)
    pdf.cell(0, 8, f"RI_U: {datos.get('RI_U', '-')} | RI_V: {datos.get('RI_V', '-')} | RI_W: {datos.get('RI_W', '-')}", ln=True)
    
    pdf.ln(5)
    pdf.multi_cell(0, 8, f"Observaciones: {datos.get('Descripcion', 'Sin observaciones')}")
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')
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
                # 1. Crear el diccionario de datos
                nueva = {
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
                    "Trabajos_Externos": ext,
                    "Tipo_Tarea": "Nuevo Registro"
                }

                # 2. Guardar en la base de datos (Google Sheets / DataFrame)
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)

                # 3. Limpiar y Generar PDF en el estado de la sesión
                if "pdf_buffer" in st.session_state:
                    del st.session_state["pdf_buffer"]
                
                st.session_state.pdf_buffer = generar_pdf_ingreso(nueva)
                st.session_state.tag_actual = t
                st.session_state.form_key += 1
                
                # 4. Mostrar Éxito y Etiqueta
                st.success(f"✅ Motor {t} registrado con éxito.")
                
                etiqueta_img = generar_etiqueta_honeywell(t, sn, p)
                if etiqueta_img:
                    st.info("📋 Etiqueta lista para Honeywell PC42")
                    st.image(etiqueta_img, width=300)
                    st.download_button(
                        label="💾 Descargar Etiqueta (PNG)",
                        data=etiqueta_img,
                        file_name=f"Etiqueta_{t}.png",
                        mime="image/png"
                    )

                # 5. Efecto visual (Opcional: No uses rerun aquí si quieres que descarguen el PDF)
                st.balloons()
                
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
                    st.subheader(f" Ⓜ {buscado}")
                    st.caption(f"Número de Serie: {seleccion.split('SN: ')[1] if 'SN: ' in seleccion else 'S/D'}")

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
                fecha = fila.get('Fecha','-')
                tarea = fila.get('Tipo_Tarea', 'General')
                responsable = fila.get('Responsable', 'S/D')
                desc_completa = str(fila.get('Descripcion', '-'))
                desc_corta = desc_completa[:30]

                with st.expander(f"🔍 {fecha} - {tarea} ({desc_corta}...)"):
                    # 1. Mostrar información en pantalla
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**👤 Responsable:** {responsable}")
                        st.write(f"**📝 Descripción:** {desc_completa}")
                    with c2:
                        st.write(f"**⚙️ Rod. LA:** {fila.get('Rodamiento_LA','-')}")
                        st.write(f"**⚙️ Rod. LOA:** {fila.get('Rodamiento_LOA','-')}")
                    st.divider()    
                # 2. Generación de PDF y Botones
                    col_pdf, col_qr = st.columns(2)
                    with col_pdf:
                        # Convertimos la fila actual a diccionario para las funciones
                        datos_fila = fila.to_dict()
                        tipo_t = str(datos_fila.get('Tipo_Tarea', '')).lower()
                        
                        # LÓGICA DE SELECCIÓN DE PLANTILLA
                        try:
                            if "lubric" in tipo_t or "grasa" in tipo_t:
                                pdf_archivo = generar_pdf_lubricacion(datos_fila)
                            elif "mega" in tipo_t or "medici" in tipo_t:
                                pdf_archivo = generar_pdf_megado(datos_fila)
                            else:
                                pdf_archivo = generar_pdf_ingreso(datos_fila)

                            # 3. BOTÓN DE DESCARGA
                            if pdf_archivo:
                                st.download_button(
                                    label="📄 Descargar Informe",
                                    data=pdf_archivo,
                                    file_name=f"Informe_{datos_fila.get('Tag','Motor')}_{idx}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_pdf_hist_{idx}"
                                 )
                        except Exception as e:
                            st.error(f"Error al generar PDF: {e}")

                    with col_qr:
                        etiqueta_bytes = generar_etiqueta_honeywell(
                            fila.get('Tag', 'S/D'), 
                            fila.get('N_Serie', 'S/D'), 
                            fila.get('Potencia', 'S/D')
                        )
                        if etiqueta_bytes:
                            st.download_button(
                                label="🖨️ Etiqueta QR",
                                data=etiqueta_bytes,
                                file_name=f"Etiqueta_{idx}.png",
                                mime="image/png",
                                key=f"qr_hist_{idx}"
                            )
                
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

                    # --- ESTE BLOQUE DEBE ESTAR AQUÍ ADENTRO (CON ESTA SANGRÍA) ---
                    # --- DENTRO DE TU BUCLE DE HISTORIAL ---
                    try:
                        # 1. Convertimos la fila a diccionario
                        raw_data = fila.to_dict()
                        
                        # 2. TRADUCTOR: Forzamos que los datos estén donde el PDF los busca
                        datos_limpios = {
                            "Fecha": raw_data.get('Fecha') or raw_data.get('fecha') or "S/D",
                            "Tag": raw_data.get('Tag') or raw_data.get('tag') or "S/D",
                            "Responsable": raw_data.get('Responsable') or raw_data.get('responsable') or "Marpi Motores",
                            "N_Serie": raw_data.get('N_Serie') or raw_data.get('Serie') or "S/D",
                            "Potencia": raw_data.get('Potencia') or "S/D",
                            "Tension": raw_data.get('Tension') or raw_data.get('Tensión') or "S/D",
                            "RPM": raw_data.get('RPM') or "S/D",
                            "Carcasa": raw_data.get('Carcasa') or "S/D",
                            # Datos Megado (Asegúrate que coincidan con tus funciones de PDF)
                            "RT_TV1": raw_data.get('RT_TV1', '-'), "RT_TU1": raw_data.get('RT_TU1', '-'), "RT_TW1": raw_data.get('RT_TW1', '-'),
                            "RI_U1U2": raw_data.get('RI_U1U2', '-'), "RI_V1V2": raw_data.get('RI_V1V2', '-'), "RI_W1W2": raw_data.get('RI_W1W2', '-'),
                            # Datos Lubricación
                            "Rodamiento_LA": raw_data.get('Rodamiento_LA') or "S/D",
                            "Rodamiento_LOA": raw_data.get('Rodamiento_LOA') or "S/D",
                            "Gramos_LA": raw_data.get('Gramos_LA') or "0",
                            "Gramos_LOA": raw_data.get('Gramos_LOA') or "0",
                            "Descripcion": raw_data.get('Descripcion') or raw_data.get('descripcion') or "S/D"
                        }

                        # --- 3. SELECCIÓN DE PLANTILLA PDF SEGÚN EL TIPO DE TAREA ---
                        datos_pdf = fila.to_dict()
                        tipo_t = str(datos_pdf.get('Tipo_Tarea', '')).strip().lower()
                        pdf_archivo = None # Limpiamos el texto
                        try:
                            if "lubric" in tipo_t or "grasa" in tipo_t:
                                pdf_archivo = generar_pdf_lubricacion(datos_pdf)
                            elif "mega" in tipo_t or "medici" in tipo_t or "aisla" in tipo_t:
                                pdf_archivo = generar_pdf_megado(datos_pdf)
                            else:
                                pdf_archivo = generar_pdf_ingreso(datos_pdf)
                        except Exception as e:
                            # Este es el bloque que faltaba y por eso daba SyntaxError
                            st.error(f"Error al generar el PDF: {e}")
                            pdf_archivo = None

                        # --- 4. BOTÓN DE DESCARGA (Dentro del primer try) ---
                        if pdf_archivo:
                            st.download_button(
                                label=f"📄 Descargar {tipo_t}",
                                data=pdf_archivo,
                                file_name=f"Reporte_{datos_limpios['Tag']}.pdf",
                                mime="application/pdf",
                                key=f"btn_pdf_{idx}"
                            )

                    except Exception as e:
                        st.error(f"Error al generar el PDF del historial en fila {idx}: {e}")
        else:
            st.warning("No hay intervenciones registradas para este motor.")

elif modo == "Relubricacion":
    st.title("🛢️ Lubricación Inteligente MARPI")
    
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
                    "N_Serie": v_serie, # <--- AGREGA ESTO
                    "Potencia": info_motor.get('Potencia', 'S/D'), # <--- AGREGA ESTO
                    "Tipo_Tarea": "Relubricacion",
                    "Responsable": resp_actual,
                    "Rodamiento_LA": rod_la,
                    "Rodamiento_LOA": rod_loa,
                    "Gramos_LA": gr_real_la,
                    "Gramos_LOA": gr_real_loa,
                    "Tipo_Grasa": grasa_t,
                    "Notas": notas,
                    "Descripcion": f"LUBRICACIÓN REALIZADA: {grasa_t}"
                }
                
                # 3. Guardado
                df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final)

                # --- LÓGICA DE GENERACIÓN DE PDF REFORZADA (UBICACIÓN EXACTA) ---
                if "pdf_buffer" in st.session_state:
                    del st.session_state["pdf_buffer"]

                tipo_de_informe = nueva.get("Tipo_Tarea", "")

                if tipo_de_informe == "Relubricacion":
                    # ESTA LÍNEA ES LA QUE CAMBIA EL ENCABEZADO Y QUITA LOS NAN
                    st.session_state.pdf_buffer = generar_pdf_lubricacion(nueva)
                elif modo == "Mediciones de Campo":
                    st.session_state.pdf_buffer = generar_pdf_megado(nueva)
                else:
                    st.session_state.pdf_buffer = generar_pdf_ingreso(nueva)
                # --- FIN DE LA LÓGICA ---

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
                
                st.session_state.pdf_buffer = generar_pdf_megado(nueva_fila)
                st.session_state.current_tag = t
                st.success(f"✅ ¡Todo guardado! {t} actualizado con sus 15 mediciones.")
                st.balloons()
            else:
                st.error("⚠️ Falta TAG o Responsable.")

    # 3. BOTÓN DE DESCARGA (Afuera)
    if st.session_state.pdf_buffer:
        st.download_button(
            label="📥 DESCARGAR INFORME TÉCNICO COMPLETO",
            data=st.session_state.pdf_buffer,
            file_name=f"Informe_{st.session_state.current_tag}.pdf",
            mime="application/pdf",
            key="btn_descarga_final"
        )
    
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")
















































































































































































































































































































































































































































































































































































































































































































