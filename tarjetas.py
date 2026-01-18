import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF

# --- 1. FUNCIÓN UNIFICADA PARA PDF ---
def generar_pdf_reporte(datos, tag_motor, tipo_trabajo="INFORME TÉCNICO"):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 33)
            
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, f'{tipo_trabajo}', 0, 1, 'R')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 5, 'MARPI MOTORES - Mantenimiento Industrial', 0, 1, 'R')
        pdf.ln(15)
        
        # Ficha del Motor
        pdf.set_fill_color(230, 233, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 8, f"Fecha: {datos.get('Fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos.get('Responsable','-')}", 1, 1)
        pdf.cell(190, 8, f"N° Serie: {datos.get('N_Serie','-')}", 1, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DETALLE DE LA INTERVENCIÓN:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "OBSERVACIONES / ESTADO FINAL:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Taller_Externo','-')), border=1)

        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

# --- 2. CONFIGURACIÓN ---
st.set_page_config(page_title="Marpi Motores", layout="wide")

if "form_count" not in st.session_state: st.session_state.form_count = 0
if "count_relub" not in st.session_state: st.session_state.count_relub = 0
if "count_campo" not in st.session_state: st.session_state.count_campo = 0

# --- 3. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # CARGA LAS DOS HOJAS DE UNA (Asegurate que estos nombres sean iguales a tus pestañas)
    df_recepcion = conn.read(worksheet="Motores", ttl=0)
    df_completo = conn.read(worksheet="Movimientos", ttl=0)
except Exception:
    # Si falla porque los nombres son distintos, cargamos la primera hoja por defecto
    df_recepcion = conn.read(ttl=0)
    df_completo = df_recepcion 

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    modo = st.radio("SELECCIONE UNA FUNCIÓN:", ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"])

# --- 5. LÓGICA DE NAVEGACIÓN ---

if modo == "Nuevo Registro":
    st.title("📝 Alta de Motor")
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    with st.form(key=f"alta_{st.session_state.form_count}"):
        c1, c2, c3 = st.columns(3)
        t = c1.text_input("TAG/ID MOTOR").upper()
        p = c2.text_input("Potencia")
        sn = c3.text_input("N° de Serie")
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción")
        if st.form_submit_button("💾 GUARDAR ALTA"):
            if t and resp:
                nueva = {"Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "N_Serie": sn, "Responsable": resp, "Descripcion": desc, "Taller_Externo": "ALTA INICIAL"}
                df_final = pd.concat([df_recepcion, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_final, worksheet="Motores")
                st.success("✅ Guardado"); st.rerun()

elif modo == "Historial y QR":
    st.title("🔍 Consulta de Motor")
    if not df_recepcion.empty:
        lista_tags = [""] + list(df_recepcion['Tag'].unique())
        motor_buscado = st.selectbox("Seleccioná un Motor:", lista_tags)
        if motor_buscado:
            fijos = df_recepcion[df_recepcion['Tag'] == motor_buscado].iloc[0]
            st.header(f"🚜 Motor: {motor_buscado}")
            st.write(f"**Serie:** {fijos.get('N_Serie','-')} | **Potencia:** {fijos.get('Potencia','-')}")
            
            historial = df_completo[df_completo['Tag'] == motor_buscado].copy()
            if not historial.empty:
                for idx, fila in historial.iterrows():
                    with st.expander(f"📅 {fila['Fecha']} - {fila['Responsable']}"):
                        col_t, col_b = st.columns([3, 1])
                        col_t.write(fila['Descripcion'])
                        pdf_b = generar_pdf_reporte(fila.to_dict(), motor_buscado)
                        col_b.download_button("📥 PDF", pdf_b, f"Reporte_{motor_buscado}.pdf", "application/pdf", key=f"btn_{idx}")
            else: st.info("Sin historial.")

elif modo == "Relubricacion":
    st.title("🛢️ Gestión de Relubricación")
    with st.form(key=f"relub_{st.session_state.count_relub}"):
        tag_r = st.text_input("TAG MOTOR").upper()
        gr_la = st.text_input("Gramos LA")
        gr_loa = st.text_input("Gramos LOA")
        resp_r = st.text_input("Responsable")
        if st.form_submit_button("💾 GUARDAR ENGRASE"):
            nueva = {"Fecha": date.today().strftime("%d/%m/%Y"), "Tag": tag_r, "Responsable": resp_r, "Descripcion": f"RELUBRICACIÓN: LA {gr_la}g / LOA {gr_loa}g", "Taller_Externo": "Mantenimiento Preventivo"}
            df_up = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_up, worksheet="Movimientos")
            st.session_state.count_relub += 1
            st.success("✅ Guardado"); st.rerun()

elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo")
    with st.form(key=f"campo_{st.session_state.count_campo}"):
        t_c = st.text_input("TAG MOTOR").upper()
        v_c = st.selectbox("Voltaje", ["500V", "1000V", "2500V"])
        res_c = st.text_input("Resultado Megado (MΩ)")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")















































































































































































































































































