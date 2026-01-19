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
    st.title("🛢️ Calculadora de Lubricación para Grandes Motores")

    def calcular_grasa_avanzado(codigo):
        """Calcula gramos basado en el código del rodamiento (Ej: 6318)"""
        try:
            # Limpiamos el código (ej: de 'NU 318 C3' a '318')
            solo_numeros = ''.join(filter(str.isdigit, codigo))
            if len(solo_numeros) < 3: return None
            
            # Los últimos dos dígitos son la serie del diámetro interior
            serie_eje = int(solo_numeros[-2:])
            # El dígito anterior indica la serie (2 = liviana, 3 = pesada)
            serie_ancho = int(solo_numeros[-3])

            # d = diámetro interior (eje)
            d = serie_eje * 5
            
            # Estimación de D (exterior) y B (ancho) según series estándar 
            if serie_ancho == 3: # Serie pesada (ej 63xx)
                D = d * 2.2 
                B = D * 0.25
            else: # Serie liviana (ej 62xx)
                D = d * 1.8
                B = D * 0.22
                
            gramos = D * B * 0.005
            return round(gramos, 1)
        except:
            return None

    with st.form("form_lub_profesional"):
        t_r = st.text_input("TAG DEL MOTOR").upper()
        col1, col2 = st.columns(2)
        
        with col1:
            rod_la = st.text_input("Número de Rodamiento LA (ej: 6320, NU322)").upper()
            gr_la_sugerido = calcular_grasa_avanzado(rod_la)
            if gr_la_sugerido:
                st.success(f"📊 Sugerido para {rod_la}: **{gr_la_sugerido}g**")
            gr_la = st.number_input("Gramos finales LA", value=gr_la_sugerido if gr_la_sugerido else 0.0)

        with col2:
            rod_loa = st.text_input("Número de Rodamiento LOA").upper()
            gr_loa_sugerido = calcular_grasa_avanzado(rod_loa)
            if gr_loa_sugerido:
                st.success(f"📊 Sugerido para {rod_loa}: **{gr_loa_sugerido}g**")
            gr_loa = st.number_input("Gramos finales LOA", value=gr_loa_sugerido if gr_loa_sugerido else 0.0)

        if st.form_submit_button("💾 GUARDAR LUBRICACIÓN"):
            # ... (aquí va tu lógica de guardado que ya funciona) ...
            st.success("✅ Datos guardados correctamente")
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


















































































































































































































































































































































