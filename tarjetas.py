import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

# Importante: Inicializar variables para que no den el error de la foto
if 'guardado' not in st.session_state:
    st.session_state.guardado = False

# 2. DETECTAR QR (Parámetros de URL)
# Esto lee el ?tag=XXXX del QR
query_params = st.query_params
tag_qr = query_params.get("tag", "")

# 3. MOSTRAR LOGO
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

# 4. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    df_completo = pd.DataFrame()

# 5. MENÚ LATERAL (Si hay tag de QR, salta a Historial automáticamente)
with st.sidebar:
    st.header("⚙️ Menú Marpi")
    default_index = 1 if tag_qr else 0
    modo = st.radio("Seleccione:", ["📝 Registro", "🔍 Historial / QR"], index=default_index)

# --- MODO 1: REGISTRO ---
if modo == "📝 Registro":
    st.title("📝 Nueva Reparación")
    
    tag = st.text_input("Tag / ID Motor", value=tag_qr).strip().upper()
    
    # Cargar datos automáticos si el motor ya existe
    datos_previa = {"Potencia": "", "Tension": "", "RPM": ""}
    if tag and not df_completo.empty:
        historia = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
        if not historia.empty:
            ultimo = historia.iloc[-1]
            datos_previa = {
                "Potencia": str(ultimo.get('Potencia', '')),
                "Tension": str(ultimo.get('Tension', '')),
                "RPM": str(ultimo.get('RPM', ''))
            }

    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("fecha", date.today(), format="DD/MM/YYYY")
            descripcion = st.text_area("Descripción del trabajo")
        
        with col2:
            pot = st.text_input("Potencia (HP/kW)", value=datos_previa["Potencia"])
            ten = st.text_input("Tensión (V)", value=datos_previa["Tension"])
            rpm = st.text_input("RPM", value=datos_previa["RPM"])
            rt = st.text_input("Res. Tierra (Ω)")
            rb = st.text_input("Res. E.Bobina (Ω)")
            ri = st.text_input("Res. Interna (Ω)")
            
        btn_guardar = st.form_submit_button("💾 GUARDAR")

    if btn_guardar:
        if tag and responsable:
            nuevo = pd.DataFrame([{
                "Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag,
                "Potencia": pot, "Tension": ten, "RPM": rpm, 
                "Res_Tierra": rt, "Res_Bobinas": rb, "Res_Interna": ri,
                "Descripcion": descripcion
            }])
            df_final = pd.concat([df_completo, nuevo], ignore_index=True)
            conn.update(data=df_final)
            st.success(f"✅ Guardado en el historial de {tag}")
            st.session_state.guardado = True
        else:
            st.error("Faltan campos (Tag o Técnico)")

  # Generar QR para el motor actual
    if tag:
        st.divider()
        # 1. PEGA AQUÍ TU URL REAL (la que ves en el navegador)
        mi_url = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
        
        # 2. LIMPIAMOS LA URL (por si acaso hay espacios)
        mi_url = mi_url.strip()
        if not mi_url.endswith("/"):
            mi_url += "/"
            
        # 3. CREAMOS EL ENLACE FINAL
        link_qr = f"{mi_url}?tag={tag}"
        
        # 4. GENERAMOS LA IMAGEN
        qr_img = qrcode.make(link_qr)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        st.image(buf, width=150, caption=f"QR Motor {tag}")
        st.info(f"Enlace del QR: {link_qr}") # Esto te servirá para verificar si el link está bien

# --- MODO 2: HISTORIAL (Lo que abre el QR) ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida del Motor")
    
    id_buscar = st.text_input("ID del Motor:", value=tag_qr).strip().upper()
    
    if id_buscar:
        if not df_completo.empty:
            res = df_completo[df_completo['Tag'].astype(str).str.upper() == id_buscar]
            if not res.empty:
                st.subheader(f"Reparaciones de {id_buscar}")
                # Mostramos la tabla. Sort por índice descendente para ver lo nuevo arriba
                st.dataframe(res.sort_index(ascending=False), use_container_width=True)
            else:
                st.warning(f"No hay registros para {id_buscar}")
        else:
            st.error("No hay datos en la base de datos.")
    
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





















































































































