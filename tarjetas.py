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
    tag = st.text_input("Tag / ID Motor")
with col_c:
    responsable = st.text_input("Técnico Responsable")

# --- SECCIÓN 2: DATOS DE PLACA ---
st.subheader("🏷️ Datos de Placa")
col_p1, col_p2, col_p3, col_p4 = st.columns(4)
with col_p1:
    potencia = st.text_input("Potencia (HP/kW)")
with col_p2:
    tension = st.text_input("Tensión (V)")
with col_p3:
    corriente = st.text_input("Corriente (A)")
with col_p4:
    rpm = st.text_input("RPM")

# --- SECCIÓN 3: MEDICIONES ELÉCTRICAS ---
st.subheader("🧪 Mediciones de Control")
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    res_tierra = st.text_input("Resistencia a Tierra (MΩ o GΩ)", help="Medición con Megóhmetro")
with col_m2:
    res_bobinas = st.text_input("Resistencia entre Bobinas (Ω)", help="U-V, V-W, W-U")
with col_m3:
    res_bobinas = st.text_input("Resistencia Interna (Ω)", help="V-V, U-U, W-W")

descripcion = st.text_area("Detalles de Reparación y Repuestos")
tabajos_taller_externo = st.text_area("Reparacion Taller Externo")

# --- FUNCIÓN GUARDAR ---
def guardar_datos(f, r, t, pot, ten, corr, vel, rt, rb, d):
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
            "Descripcion": d,
            "Trabajos_taller_externo": te,
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
        exito, msj = guardar_datos(fecha, responsable, tag, potencia, tension, corriente, rpm, res_tierra, res_bobinas, descripcion)
        
        if exito:
            st.success("✅ Datos registrados correctamente")

            # Generar QR
            fecha_qr = fecha.strftime("%d/%m/%Y")
            qr_text = (f"MARPI: {tag}\nFECHA: {fecha}\nPOT: {potencia}\n"
                       f"R.TIERRA: {res_tierra}\nR.BOBINAS: {res_bobinas}
                      f"descripcion: {descripcion}")
            qr = qrcode.make(qr_text)
            buf_qr = BytesIO()
            qr.save(buf_qr, format="PNG")

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














