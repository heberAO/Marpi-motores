import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
    
# 1. INICIALIZACIÓN Y LECTURA DE QR
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

# Detectar si venimos de un QR (?tag=XXXX)
query_params = st.query_params
tag_qr = query_params.get("tag", "")

if 'form_id' not in st.session_state:
    st.session_state.form_id = 0

# 2. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except Exception:
    df_completo = pd.DataFrame()

with st.sidebar:
    st.header("⚙️ Menú Marpi")
    modo = st.radio("Seleccione:", ["📝 Nueva Carga / Continuar", "🔍 Ver Historial"])

# --- MODO 1: CARGA DE REPARACIONES ---
if modo == "📝 Nueva Carga / Continuar":
    st.title("SISTEMA DE REGISTRO MARPI ELEC.")
   
    # Identificación
    tag = st.text_input("Tag / ID Motor", value=tag_qr).strip().upper()
    
    # Lógica de "Seguir cargando en ese Tag"
    datos_previa = {"Potencia": "", "Tension": "", "RPM": ""}
    if tag and not df_completo.empty:
        historial = df_completo[df_completo['Tag'].astype(str).str.upper() == tag]
        if not historial.empty:
            ultimo = historial.iloc[-1]
            datos_previa = {
                "Potencia": str(ultimo.get('Potencia', '')),
                "Tension": str(ultimo.get('Tension', '')),
                "RPM": str(ultimo.get('RPM', ''))
            }
            st.success(f"✅ Motor {tag} reconocido. Cargando datos técnicos...")

    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            responsable = st.text_input("Técnico Responsable")
            fecha = st.date_input("Fecha Hoy", date.today(), format="DD/MM/YYYY")
            descripcion = st.text_area("¿Qué reparación se hizo hoy?")
        
        with col2:
            pot = st.text_input("Potencia", value=datos_previa["Potencia"])
            ten = st.text_input("Tensión", value=datos_previa["Tension"])
            rpm = st.text_input("RPM", value=datos_previa["RPM"])
            rt = st.text_input("Res. Tierra (Ω)")
            rb = st.text_input("Res. E.Bobina (Ω)")
            ri = st.text_input("Res. Interna (Ω)")                   

        guardar = st.form_submit_button("💾 GUARDAR EN HISTORIAL")

    if guardar:
        if tag and responsable:
            nuevo = pd.DataFrame([{
                "Fecha": fecha.strftime("%d/%m/%Y"), "Responsable": responsable, "Tag": tag,
                "Potencia": pot, "Tension": ten, "RPM": rpm, "Res_Tierra": rt, "Res_E.Bobina": rb, "Res_Interna": ir, 
                "Descripcion": descripcion
            }])
            df_final = pd.concat([df_completo, nuevo], ignore_index=True)
            conn.update(data=df_final)
            st.success(f"✅ Reparación añadida al historial de {tag}")
            
            # Generar el QR para el motor
            url_app = "https://marpi-motores.streamlit.app/" # Cambiar por tu URL real
            qr_link = f"{url_app}?tag={tag}"
            qr_img = qrcode.make(qr_link)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf, caption=f"QR Único Motor {tag}", width=200)
        else:
            st.error("Faltan campos obligatorios.")

# --- MODO 2: CONSULTA DE HISTORIAL ---
elif modo == "🔍 Ver Historial":
    st.title("🔍 Historial por Motor")
    busqueda = st.text_input("Ingrese Tag:", value=tag_qr).strip().upper()
    if busqueda and not df_completo.empty:
        resultado = df_completo[df_completo['Tag'].astype(str).str.upper() == busqueda]
        if not resultado.empty:
            st.dataframe(resultado.sort_index(ascending=False), use_container_width=True)
        else:
            st.warning("No hay registros.")
    
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






































































































