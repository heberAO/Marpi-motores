import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

# 1. INICIALIZACIÓN (Debe estar arriba de todo)
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0
if 'guardado' not in st.session_state:
    st.session_state.guardado = False

st.set_page_config(page_title="Marpi Motores - Técnico", page_icon="⚡", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SISTEMA DE REGISTRO MARPI ELEC.")
st.markdown("---")
with st.container(key=f"marco_maestro_{st.session_state.form_id}"):
    
    # --- SECCIÓN 1: DATOS BÁSICOS ---
    st.subheader("📋 Datos del Servicio")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        fecha = st.date_input("fecha", date.today(), format="DD/MM/YYYY")
    with col_b:
        tag = st.text_input("Tag / ID Motor", key=f"tag_{st.session_state.form_id}")
    with col_c:
        responsable = st.text_input("Técnico Responsable", key=f"resp_{st.session_state.form_id}")

    # --- SECCIÓN 2: DATOS DE PLACA ---
    st.subheader("🏷️ Datos de Placa")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        potencia = st.text_input("Potencia (HP/kW)", key=f"pot_{st.session_state.form_id}")
    with col_p2:
        tension = st.text_input("Tensión (V)", key=f"ten_{st.session_state.form_id}")
    with col_p3:
        corriente = st.text_input("Corriente (A)", key=f"corr_{st.session_state.form_id}")
    with col_p4:
        rpm = st.text_input("RPM", key=f"rpm_{st.session_state.form_id}")

# --- MEDICIONES ELÉCTRICAS ---
    st.subheader("MEDICIONES ELECTRICAS")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        res_tierra = st.text_input("Resistencia entre tierra (Ω)", key=f"rt_{st.session_state.form_id}")
    with col_m2:
        res_bobinas = st.text_input("Resistencia entre Bobinas (Ω)", key=f"rb_{st.session_state.form_id}")
    with col_m3:
        res_interna = st.text_input("Resistencia Interna (Ω)", key=f"ri_{st.session_state.form_id}")
    
    descripcion = st.text_area("Detalles de Reparación y Repuestos", key=f"desc_{st.session_state.form_id}")
    externo = st.text_area("Reparacion Taller Externo", key=f"ext_{st.session_state.form_id}")

# --- FUNCIÓN GUARDAR (Fuera del container para evitar errores) ---
def guardar_datos(f, r, t, pot, ten, corr, vel, rt, rb, ri, d, ext):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = conn.read(ttl=0)
        fecha_espanol = f.strftime("%d/%m/%Y")
        nuevo_registro = pd.DataFrame([{
            "Fecha": fecha_espanol, "Responsable": r, "Tag": t, "Potencia": pot,
            "Tension": ten, "Corriente": corr, "RPM": vel, "Res_Tierra": rt,
            "Res_Bobinas": rb, "Res_interna": ri, "Descripcion": d, "Externo": ext,
        }])
        df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        conn.update(data=df_final)
        return True, "Ok"
    except Exception as e:
        return False, str(e)
        
        nuevo_registro = pd.DataFrame([{
            "Fecha": fecha_espanol,
            "Responsable": r, 
            "Tag": t, 
            "Potencia": pot,
            "Tension": ten, 
            "Corriente": corr, 
            "RPM": vel,
            "Res_Tierra": rt, 
            "Res_Bobinas": rb, 
            "Res_interna": ri, 
            "Descripcion": d, 
            "Externo": externo,
        }])
        
        df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        conn.update(data=df_final)
        return True, "Ok"
    except Exception as e:
        return False, str(e)

# --- LÓGICA DE BOTONES ---
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("💾 GUARDAR REGISTRO Y GENERAR INFORME"):
        if not tag or not responsable:
            st.error("⚠️ Tag y Responsable son obligatorios.")
        else:
            exito, msj = guardar_datos(fecha, responsable, tag, potencia, tension, corriente, rpm, res_tierra, res_bobinas, res_interna, descripcion, externo)
            if exito:
                st.session_state.guardado = True
                st.success("✅ Datos guardados correctamente.")
            else:
                st.error(f"Error al guardar: {msj}")

with col_btn2:
    if st.button("🧹 LIMPIAR"):
        # 1. Guardamos el número actual para que no se pierda
        nuevo_id = st.session_state.get('form_id', 0) + 1
        
        # 2. Borramos la memoria
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # 3. Volvemos a crear las variables (MIRA LOS ESPACIOS AQUÍ)
        st.session_state.form_id = nuevo_id
        st.session_state.guardado = False
        
        # 4. Reiniciamos
        st.rerun()
# --- SI YA SE GUARDÓ, MOSTRAR QR Y PDF ---
if st.session_state.get('guardado', False):
    st.divider()
    col_qr, col_pdf = st.columns(2)
    
    # Generar QR para visualización y PDF
    fecha_qr = fecha.strftime("%d/%m/%Y")
    qr_text = f"MARPI: {tag}\nFECHA: {fecha_qr}\nPOT: {potencia}\nDESC: {descripcion}"
    qr = qrcode.make(qr_text)
    buf_qr = BytesIO()
    qr.save(buf_qr, format="PNG")
    
    with col_qr:
        st.image(buf_qr, caption="Código QR generado", width=200)

    # Generar PDF
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 8, 33)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "PROTOCOLO DE PRUEBAS Y REPARACIÓN", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Fecha: {fecha_qr} | Responsable: {responsable}", ln=True)
    pdf.cell(0, 8, f"Tag: {tag} | Potencia: {potencia} | Tension: {tension} | RPM: {rpm}", ln=True)
    pdf.multi_cell(0, 8, f"Descripción: {descripcion}")
    
    # Guardar QR temporal para el PDF
    with open("temp_qr.png", "wb") as f_q:
        f_q.write(buf_qr.getvalue())
    pdf.image("temp_qr.png", 85, pdf.get_y() + 10, 40)
    
    pdf_out = pdf.output(dest='S').encode('latin-1')
    
    with col_pdf:
        st.subheader("📄 Tu informe está listo")
        st.download_button("📥 DESCARGAR PROTOCOLO PDF", pdf_out, f"Protocolo_{tag}.pdf")

st.markdown("---")
st.caption("Sistema diseñado por **Heber Ortiz** | Marpi Electricidad ⚡")

























































