import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os  # <--- ESTO ES LO QUE FALTABA PARA EL LOGO

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Marpi Motores - Historial QR", page_icon="⚡", layout="wide")

# --- MOSTRAR LOGO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

# Inicializar sesión para limpiar formulario o detectar QR
query_tag = st.query_params.get("tag", "")
if 'guardado' not in st.session_state:
    st.session_state.guardado = False

# 2. CONEXIÓN A BASE DE DATOS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    st.error("Error de conexión con Google Sheets")
    df_completo = pd.DataFrame()

# 3. MENÚ LATERAL
with st.sidebar:
    st.header("⚙️ Menú Marpi")
    modo = st.radio("Seleccione:", ["📝 Registro y Continuidad", "🔍 Consulta de Historial"])

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro y Continuidad":
    st.title("SISTEMA DE REGISTRO MARPI ELEC.")
    
    # Si viene de un QR, usamos ese Tag por defecto
    tag_input = st.text_input("Tag / ID Motor", value=query_tag).strip().upper()
    
    # Lógica de carga automática de datos previos
    datos_previa = {"Potencia": "", "Tension": "", "RPM": ""}
    if tag_input and not df_completo.empty:
        historia_motor = df_completo[df_completo['Tag'].astype(str).str.upper() == tag_input]
        if not historia_motor.empty:
            ultimo = historia_motor.iloc[-1]
            datos_previa = {
                "Potencia": str(ultimo.get('Potencia', '')),
                "Tension": str(ultimo.get('Tension', '')),
                "RPM": str(ultimo.get('RPM', ''))
            }
            st.info(f"✅ Motor conocido. {len(historia_motor)} reparaciones previas.")

    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("fecha", date.today(), format="DD/MM/YYYY")
            descripcion = st.text_area("Detalles de la Reparación de Hoy")
        
        with col2:
            st.markdown("**Datos Técnicos y Mediciones**")
            potencia = st.text_input("Potencia", value=datos_previa["Potencia"])
            tension = st.text_input("Tensión", value=datos_previa["Tension"])
            rpm = st.text_input("RPM", value=datos_previa["RPM"])
            rt = st.text_input("Res. Tierra (Ω)")
            rb = st.text_input("Res. E.Bobina (Ω)")
            ri = st.text_input("Res. Interna (Ω)")

        enviar = st.form_submit_button("💾 GUARDAR NUEVA REPARACIÓN")

    if enviar:
        if tag_input and responsable:
            nuevo = pd.DataFrame([{
                "Fecha": fecha.strftime("%d/%m/%Y"), 
                "Responsable": responsable, 
                "Tag": tag_input,
                "Potencia": potencia, 
                "Tension": tension, 
                "RPM": rpm, 
                "Res_Tierra": rt,
                "Res_Bobinas": rb,
                "Res_Interna": ri,
                "Descripcion": descripcion
            }])
            df_final = pd.concat([df_completo, nuevo], ignore_index=True)
            conn.update(data=df_final)
            st.session_state.guardado = True
            st.success(f"Reparación guardada para el motor {tag_input}")
            st.rerun()
        else:
            st.error("Faltan datos obligatorios (Tag o Responsable).")

    # Mostrar QR si se guardó o si el Tag está presente
    if tag_input:
        st.divider()
        # REEMPLAZA ESTO CON TU URL REAL DE STREAMLIT CLOUD:
        url_base = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/" 
        qr_link = f"{url_base}?tag={tag_input}"
        
        qr = qrcode.make(qr_link)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf, width=150, caption=f"QR de acceso al motor {tag_input}")

# --- MODO 2: CONSULTA ---
elif modo == "🔍 Consulta de Historial":
    st.title("🔍 Hoja de Vida del Motor")
    tag_buscar = st.text_input("Tag a consultar:", value=query_tag).strip().upper()
    
    if tag_buscar:
        historia = df_completo[df_completo['Tag'].astype(str).str.upper() == tag_buscar]
        if not historia.empty:
            st.subheader(f"Cronología de Intervenciones: {tag_buscar}")
            st.dataframe(historia.sort_index(ascending=False), use_container_width=True)
        else:
            st.error("No se encontraron registros para este motor.")
    
    # --- DATOS TÉCNICOS (Se autocompletan si el motor ya existe) ---
    st.subheader("🏷️ Datos de Placa")
    c1, c2, c3, c4 = st.columns(4)
    potencia = c1.text_input("Potencia (HP/kW)", key=f"pot_{st.session_state.form_id}")
    tension = c2.text_input("Tensión (V)", key=f"ten_{st.session_state.form_id}")
    corriente = c3.text_input("Corriente (A)", key=f"corr_{st.session_state.form_id}")
    rpm = c4.text_input("RPM", key=f"rpm_{st.session_state.form_id}")

    # --- NUEVA REPARACIÓN ---
    st.subheader("🛠️ Nueva Intervención")
    m1, m2, m3 = st.columns(3)
    res_tierra = m1.text_input("Res. Tierra (MΩ)", key=f"rt_{st.session_state.form_id}")
    res_bobinas = m2.text_input("Res. Bobinas (Ω)", key=f"rb_{st.session_state.form_id}")
    res_interna = m3.text_input("Res. Interna (Ω)", key=f"ri_{st.session_state.form_id}")
    
    descripcion = st.text_area("Detalle de la reparación actual", placeholder="¿Qué se le hizo hoy al motor?")
    externo = st.text_area("Trabajos de terceros (opcional)")

    if st.button("💾 GUARDAR NUEVA ENTRADA AL HISTORIAL"):
        if tag and responsable:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_previo = conn.read(ttl=0)
                nuevo_log = pd.DataFrame([{
                    "Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag,
                    "Potencia": potencia, "Tension": tension, "Corriente": corriente, "RPM": rpm,
                    "Res_Tierra": res_tierra, "Res_Bobinas": res_bobinas, "Res_interna": res_interna,
                    "Descripcion": descripcion, "Externo": externo
                }])
                df_final = pd.concat([df_previo, nuevo_log], ignore_index=True)
                conn.update(data=df_final)
                st.session_state.guardado = True
                st.balloons()
                st.success(f"✅ Se agregó una nueva reparación al historial del motor {tag}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Faltan datos obligatorios (Tag o Técnico).")

    # --- QR ÚNICO ---
    if st.session_state.guardado:
        qr_text = f"MARPI - MOTOR: {tag}\nVer historial en sistema con este ID."
        qr = qrcode.make(qr_text)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf, caption="Este QR identifica al motor para siempre", width=150)
        if st.button("🔄 Cargar otro motor"):
            st.session_state.form_id += 1
            st.session_state.guardado = False
            st.rerun()

elif modo == "🔍 Historial Completo":
    st.title("🔍 Hoja de Vida del Motor")
    tag_buscar = st.text_input("Ingrese el Tag para ver todo su historial:").strip().upper()
    
    if tag_buscar:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0)
            historia = df[df['Tag'].astype(str).str.upper() == tag_buscar]
            
            if not historia.empty:
                st.subheader(f"Lista de reparaciones para: {tag_buscar}")
                # Mostramos la tabla invertida para ver lo más nuevo arriba
                st.dataframe(historia.sort_index(ascending=False), use_container_width=True)
            else:
                st.warning("No se encontraron registros previos para ese ID.")
        except Exception as e:
            st.error(f"Error al consultar: {e}")
st.markdown("---")
st.caption("Sistema diseñado y desarrollado por **Heber Ortiz** | Marpi Electricidad ⚡")















































































































