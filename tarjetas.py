import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF

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
        
        # Ficha del Motor
        pdf.set_fill_color(230, 233, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DETALLES DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 8, f"Fecha: {datos.get('Fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos.get('Responsable','-')}", 1, 1)
        pdf.cell(190, 8, f"N° Serie: {datos.get('N_Serie','-')}", 1, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DESCRIPCIÓN DE LA TAREA / MEDICIONES:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Descripcion','-')), border=1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "ESTADO FINAL Y OBSERVACIONES:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(datos.get('Taller_Externo','-')), border=1)

        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

# --- 2. CONFIGURACIÓN ---
st.set_page_config(page_title="Marpi Motores", layout="wide")

if "form_count" not in st.session_state: st.session_state.form_count = 0
if "count_relub" not in st.session_state: st.session_state.count_relub = 0
if "count_campo" not in st.session_state: st.session_state.count_campo = 0

# --- 3. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0) # Carga la base principal
except Exception as e:
    st.error(f"Error de conexión: {e}")
    df_completo = pd.DataFrame()

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", width=150)
    st.title("⚡ MARPI MOTORES")
    modo = st.radio("SELECCIONE:", ["Nuevo Registro", "Historial y QR", "Relubricacion", "Mediciones de Campo"])

# --- 5. SECCIONES ---

if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")
    with st.form(key=f"alta_{st.session_state.form_count}"):
        col1, col2, col3, col4, col5 = st.columns(5)
        t = col1.text_input("TAG/ID MOTOR").upper()
        p = col2.text_input("Potencia")
        r = col3.selectbox("RPM", ["-", "750", "1500", "3000"])
        f = col4.text_input("Carcasa")
        sn = col5.text_input("N° de Serie")
        
        st.subheader("🔍 Mediciones Iniciales")
        m1, m2, m3 = st.columns(3)
        with m1: rt_tu, rt_tv, rt_tw = st.text_input("T-U"), st.text_input("T-V"), st.text_input("T-W")
        with m2: rb_uv, rb_vw, rb_uw = st.text_input("U-V"), st.text_input("V-W"), st.text_input("U-W")
        with m3: ri_u, ri_v, ri_w = st.text_input("U1-U2"), st.text_input("V1-V2"), st.text_input("W1-W2")
        
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción Inicial")
        ext = st.text_area("Trabajos Externos")
        
        if st.form_submit_button("💾 GUARDAR ALTA"):
            if t and resp:
                nueva_fila = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f, "N_Serie": sn,
                    "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext,
                    "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw, "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                    "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"✅ Guardado {t}"); st.session_state.form_count += 1; st.rerun()
elif modo == "Historial y QR":
    st.title("🔍 Consulta de Motor y QR")
    
    if not df_completo.empty:
        # 1. Buscador Principal
        lista_tags = [""] + sorted(list(df_completo['Tag'].unique()))
        motor_buscado = st.selectbox("Seleccioná un Motor:", lista_tags)
        
        if motor_buscado:
            # Guardamos datos en memoria para que aparezcan en las otras pestañas
            fijos = df_completo[df_completo['Tag'] == motor_buscado].iloc[-1] # Tomamos el último registro
            st.session_state['tag_seleccionado'] = motor_buscado
            st.session_state['serie_seleccionada'] = fijos.get('N_Serie', '')
            
            st.header(f"🚜 Motor: {motor_buscado}")
            st.info(f"**N° Serie:** {st.session_state['serie_seleccionada']} | **Potencia:** {fijos.get('Potencia','-')}")

            # --- BOTONES DE ACCIÓN RÁPIDA ---
            st.subheader("➕ Nueva Intervención")
            st.write("Seleccioná qué vas a registrar para este motor:")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⚡ Registrar Megado"):
                    st.info("Cambiá a 'Mediciones de Campo' en el menú lateral. El TAG ya estará cargado.")
            with c2:
                if st.button("🛢️ Registrar Lubricación"):
                    st.info("Cambiá a 'Relubricacion' en el menú lateral. El TAG ya estará cargado.")

            st.divider()

            # --- HISTORIAL ---
            st.subheader("📜 Historial de Intervenciones")
            hist_m = df_completo[df_completo['Tag'] == motor_buscado].copy()
            hist_m['Fecha_dt'] = pd.to_datetime(hist_m['Fecha'], dayfirst=True, errors='coerce')
            hist_m = hist_m.sort_values(by='Fecha_dt', ascending=False)

            for idx, fila in hist_m.iterrows():
                with st.expander(f"📅 {fila['Fecha']} - {fila['Responsable']}"):
                    c_txt, c_pdf = st.columns([3, 1])
                    with c_txt:
                        st.write(f"**Detalle:** {fila['Descripcion']}")
                        st.write(f"**Obs:** {fila.get('Taller_Externo', '-')}")
                    with c_pdf:
                        pdf_b = generar_pdf_reporte(fila.to_dict(), motor_buscado)
                        st.download_button("📄 PDF", pdf_b, f"Reporte_{motor_buscado}_{idx}.pdf", "application/pdf", key=f"h_{idx}")

            # --- GENERADOR DE QR ---
            st.divider()
            st.subheader("🖼️ Código QR para el Equipo")
            
            # Ajustamos la URL para que al escanear abra el historial directo
            # Reemplaza la URL por la de tu app real
            url_qr = f"https://marpi-motores.streamlit.app/?tag={motor_buscado}"
            
            try:
                # Usamos qrcode directamente si está importado
                import qrcode
                from io import BytesIO
                
                qr_img = qrcode.make(url_qr)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                
                col_qr, col_desc = st.columns([1, 2])
                col_qr.image(buf.getvalue(), width=150)
                col_desc.write("Escaneá o descargá este código para pegar en el motor. Al hacerlo, abrirá este historial directamente.")
                col_desc.download_button("📥 Descargar imagen QR", buf.getvalue(), f"QR_{motor_buscado}.png", "image/png")
            except Exception as e:
                st.warning("No se pudo generar el QR. Verifica que 'qrcode' esté en requirements.txt")

    else:
        st.warning("La base de datos está vacía.")                


elif modo == "Relubricacion":
    st.title("🛢️ Gestión de Relubricación")
    with st.form(key=f"relub_{st.session_state.count_relub}"):
        t_r = st.text_input("TAG DEL MOTOR").upper()
        sn_r = st.text_input("N° de Serie")
        resp_r = st.text_input("Responsable")
        c1, c2 = st.columns(2)
        rod_la = c1.text_input("Rodamiento LA")
        gr_la = c1.text_input("Gramos LA")
        rod_loa = c2.text_input("Rodamiento LOA")
        gr_loa = c2.text_input("Gramos LOA")
        grasa = st.selectbox("Grasa", ["SKF LGHP 2", "Mobil Polyrex EM", "Shell Gadus", "Otra"])
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("💾 GUARDAR ENGRASE"):
            nueva = {
                "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_r, "N_Serie": sn_r, "Responsable": resp_r,
                "Descripcion": f"RELUBRICACIÓN: LA: {rod_la} ({gr_la}g) - LOA: {rod_loa} ({gr_loa}g)",
                "Taller_Externo": f"Grasa: {grasa}. {obs}"
            }
            df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_final)
            st.session_state.count_relub += 1
            st.success("✅ Engrase Guardado")
            pdf_b = generar_pdf_reporte(nueva, t_r, "REPORTE DE LUBRICACIÓN")
            st.download_button("📥 Bajar PDF", pdf_b, f"Lubricacion_{t_r}.pdf", "application/pdf")

elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones de Campo")
    with st.form(key=f"campo_{st.session_state.count_campo}"):
        t_c = st.text_input("TAG MOTOR").upper()
        sn_c = st.text_input("N° SERIE")
        resp_c = st.text_input("Técnico")
        volt = st.selectbox("Voltaje", ["500V", "1000V", "2500V"])
        est = st.selectbox("Estado", ["APTO PARA OPERAR", "RIESGO DE FALLA", "NO APTO"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🟢 Motor")
            rt_tu, rt_tv, rt_tw = st.text_input("T-U "), st.text_input("T-V "), st.text_input("T-W ")
        with col2:
            st.markdown("### 🔵 Línea")
            rl1, rl2, rl3 = st.text_input("T-L1"), st.text_input("T-L2"), st.text_input("T-L3")
        
        obs_c = st.text_area("Observaciones")
        
        if st.form_submit_button("💾 GUARDAR MEGADO"):
            detalle = f"MEGADO {volt}. Mot:[T:{rt_tu}/{rt_tv}/{rt_tw}] - Lin:[T:{rl1}/{rl2}/{rl3}]"
            nueva = {
                "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t_c, "N_Serie": sn_c, "Responsable": resp_c,
                "Descripcion": detalle, "Taller_Externo": f"ESTADO: {est}. {obs_c}"
            }
            df_final = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(data=df_final)
            st.session_state.count_campo += 1
            st.success("✅ Megado Guardado")
            pdf_b = generar_pdf_reporte(nueva, t_c, "REPORTE DE AISLAMIENTO")
            st.download_button("📥 Bajar PDF", pdf_b, f"Megado_{t_c}.pdf", "application/pdf")
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")



















































































































































































































































































