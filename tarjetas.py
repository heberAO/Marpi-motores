import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
from fpdf import FPDF
import os

st.set_page_config(page_title="Marpi Motores - Técnico", page_icon="⚡", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SISTEMA DE REGISTRO MARPI ELEC.")
st.markdown("---")

# --- SECCIÓN 1: DATOS BÁSICOS ---
st.subheader("📋 Datos del Servicio")
col_a, col_b, col_c = st.columns(3)
with col_a:
    fecha = st.date_input("fecha", date.today(), format="DD/MM/YYYY")
with col_b:
    tag = st.text_input("Tag / ID Motor", key="ins_t")
with col_c:
    responsable = st.text_input("Técnico Responsable", key="ins_r")

# --- SECCIÓN 2: DATOS DE PLACA ---
st.subheader("🏷️ Datos de Placa")
col_p1, col_p2, col_p3, col_p4 = st.columns(4)
with col_p1:
    potencia = st.text_input("Potencia (HP/kW)", key="ins_pot")
with col_p2:
    tension = st.text_input("Tensión (V)", key="ins_ten")
with col_p3:
    corriente = st.text_input("Corriente (A)", key="ins_corr")
with col_p4:
    rpm = st.text_input("RPM", key="ins_vel")

# --- SECCIÓN 3: MEDICIONES ELÉCTRICAS ---
st.subheader("🧪 Mediciones de Control")
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    res_tierra = st.text_input("Resistencia a Tierra (MΩ o GΩ)", help="Medición con Megóhmetro", key="ins_rt")
with col_m2:
    res_bobinas = st.text_input("Resistencia entre Bobinas (Ω)", help="U-V, V-W, W-U", key="ins_rb")
with col_m3:
    res_ineterna = st.text_input("Resistencia Interna (Ω)", help="V-V, U-U, W-W", key="ins_int")

descripcion = st.text_area("Detalles de Reparación y Repuestos", key="ins_d")
externo_tabajos = st.text_area("Reparacion Taller Externo", key="ins_externo")

# --- FUNCIÓN GUARDAR ---
def guardar_datos(f, r, t, pot, ten, corr, vel, rt, rb, d, externo):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = conn.read(ttl=0)
        fecha_espanol = f.strftime("%d/%m/%Y")
        
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
            "Res_interna": int,
            "Descripcion": d,
            "Externo_tabajos": externo,
        }])
        
        df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        conn.update(data=df_final)
        return True, "Ok"
    except Exception as e:
        return False, str(e)

# --- BOTÓN Y GENERACIÓN ---
if st.button("💾 GUARDAR REGISTRO Y GENERAR INFORME"):
    if not tag or not responsable:
        st.error("⚠️ Tag y Responsable son obligatorios.")
    else:
        exito, msj = guardar_datos(fecha, responsable, tag, potencia, tension, corriente, rpm, res_tierra, res_bobinas, descripcion, externo)
        if exito:
            # Generar QR
            fecha_qr = fecha.strftime("%d/%m/%Y")
            qr_text = (
               f"MARPI: {tag}\n"
               f"FECHA: {fecha_qr}\n"
               f"POTENCIA: {potencia}\n"
               f"R.TIERRA: {res_tierra}\n"
               f"R.BOBINAS: {res_bobinas}\n"
               f"DESC: {descripcion}"
               f"EXTERNO {externo}"
            )
            qr = qrcode.make(qr_text)
            buf_qr = BytesIO()
            qr.save(buf_qr, format="PNG")
            st.image(buf_qr, caption="✅ Código QR generado para el motor", width=250)
            st.divider()
            st.subheader("¿Deseas cargar otro motor?")
            if st.button("🧹 LIMPIAR FORMULARIO PARA NUEVA CARGA"):
                for key in list(st.session_state.keys()):
                    if key.startswith("ins_"):
                         st.session_state[key] = ""
                st.rerun()
            # Generar PDF
            pdf = FPDF()
            pdf.add_page()
            if os.path.exists("logo.png"):
                pdf.image("logo.png", 10, 8, 33)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "PROTOCOLO DE PRUEBAS Y REPARACIÓN", ln=True, align='C')
            pdf.ln(15)

            # Bloque Datos de Placa
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, " 1. DATOS DE PLACA", 0, 1, 'L', True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, f"Tag: {tag} | Potencia: {potencia} | Tension: {tension} | RPM: {rpm}", 1, 1)
            
            pdf.ln(5)
            # Bloque Mediciones
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, " 2. MEDICIONES ELÉCTRICAS", 0, 1, 'L', True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, f"Resistencia a Tierra: {res_tierra}", 1, 1)
            pdf.cell(0, 8, f"Resistencia entre Bobinas (U-V-W): {res_bobinas}", 1, 1)
            pdf.cell(0, 8, f"Resistencia interna: {res_bobinas}", 1, 1)

            pdf.ln(5)
            # Bloque Descripción
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, " 3. DETALLE DE TRABAJOS", 0, 1, 'L', True)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 8, descripcion, 1)

            with open("temp_qr.png", "wb") as f_q:
                f_q.write(buf_qr.getvalue())
            pdf.image("temp_qr.png", 85, pdf.get_y() + 10, 40)

            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("📥 DESCARGAR PROTOCOLO PDF", pdf_out, f"Protocolo_{tag}.pdf")
            st.image(buf_qr.getvalue(), width=200)
        else:
            st.error(f"Error: {msj}")
            st.markdown("---")
st.caption("Sistema diseñado y desarrollado por **Heber Ortiz** | Marpi Electricidad ⚡")





































