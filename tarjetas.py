import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import os
from fpdf import FPDF
import urllib.parse
import re
import time

# 1. FUNCIÓN PDF MEJORADA (Incluye tus mediciones de campo)
def generar_pdf_reporte(datos, tag_motor, tipo_trabajo="INFORME TÉCNICO"):
    try:
        from fpdf import FPDF
        datos_limpios = {str(k).replace(" ", "_").lower(): v for k, v in datos.items()}
        
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Encabezado MARPI
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, f'{tipo_trabajo}', 0, 1, 'R')
        pdf.ln(5)

        # Datos del Equipo
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" DATOS DEL EQUIPO: {tag_motor}", 1, 1, 'L', True)
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(95, 8, f"Fecha: {datos_limpios.get('fecha','-')}", 1, 0)
        pdf.cell(95, 8, f"Responsable: {datos_limpios.get('responsable','-')}", 1, 1)

        # Si es Lubricación
        if "LUBRICACION" in tipo_trabajo.upper() or "gramos_la" in datos_limpios:
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, " DETALLES DE LUBRICACIÓN:", 1, 1, 'L', True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(95, 8, f"Rod. LA: {datos_limpios.get('rodamiento_la','-')}", 1, 0)
            pdf.cell(95, 8, f"Gramos LA: {datos_limpios.get('gramos_la','0')} g", 1, 1)
            pdf.cell(95, 8, f"Rod. LOA: {datos_limpios.get('rodamiento_loa','-')}", 1, 0)
            pdf.cell(95, 8, f"Gramos LOA: {datos_limpios.get('gramos_loa','0')} g", 1, 1)

        # Detalle / Mediciones
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "DETALLE DE INTERVENCIÓN / MEDICIONES:", 0, 1)
        desc = datos_limpios.get('descripcion') or datos_limpios.get('detalle') or '-'
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, str(desc), border=1)

        obs = datos_limpios.get('observaciones') or datos_limpios.get('taller_externo') or ''
        if obs and obs != '-':
            pdf.ln(3)
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 8, f"Notas: {obs}", 0, 1)

        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error PDF: {e}")
        return None

# --- ESTRUCTURA DE PESTAÑAS (REPARADA) ---

if modo == "Nuevo Registro":
    st.title("📝 Alta y Registro Inicial")
    if "form_key" not in st.session_state: st.session_state.form_key = 0
    fecha_hoy = st.date_input("Fecha", date.today(), format="DD/MM/YYYY")

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
                st.error("⚠️ Datos obligatorios faltantes.")
            else:
                mediciones = f"RES: T-U:{rt_tu}, T-V:{rt_tv}, T-W:{rt_tw} | B: UV:{rb_uv}, VW:{rb_vw}, UW:{rb_uw}"
                nueva = {
                    "Fecha": fecha_hoy.strftime("%d/%m/%Y"), "Tag": t, "N_Serie": sn, 
                    "Responsable": resp, "Potencia": p, "RPM": r, "Frame": f,
                    "Descripcion": f"{desc} | {mediciones}", "Taller_Externo": ext
                }
                df_act = pd.concat([df_completo, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(data=df_act)
                st.session_state.form_key += 1
                st.success(f"✅ Motor {t} guardado")
                st.rerun()

elif modo == "Historial y QR":
    st.title("🔍 Consulta y Gestión de Motores")
    if not df_completo.empty:
        df_completo['Busqueda_Combo'] = df_completo['Tag'].astype(str) + " | SN: " + df_completo['N_Serie'].astype(str)
        # Limpieza para evitar el error de sorted con nulos
        opciones = [""] + sorted([str(x) for x in df_completo['Busqueda_Combo'].dropna().unique()])
        
        seleccion = st.selectbox("Busca por TAG o N° de Serie:", opciones)
        
        if seleccion:
            buscado = seleccion.split(" | ")[0].strip()
            st.session_state.tag_fijo = buscado
            
            col_qr, col_info = st.columns([1, 2])
            url_app = f"https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/?tag={buscado}"
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(url_app)}"
            
            with col_qr: st.image(qr_api, caption=f"QR de {buscado}")
            with col_info:
                st.subheader(f"🚜 Equipo: {buscado}")
                st.write(f"**Link:** {url_app}")
            
            st.divider()
            st.subheader("📜 Historial de Intervenciones")
            hist_m = df_completo[df_completo['Tag'] == buscado].copy().iloc[::-1]
            for idx, fila in hist_m.iterrows():
                with st.expander(f"📅 {fila.get('Fecha','-')} - {str(fila.get('Descripcion','-'))[:30]}..."):
                    st.write(fila.to_dict())
                    pdf_h = generar_pdf_reporte(fila.to_dict(), buscado)
                    if pdf_h:
                        st.download_button("📥 Descargar PDF", pdf_h, f"{buscado}_{idx}.pdf", key=f"h_{idx}")

elif modo == "Relubricacion":
    st.title("🛢️ Lubricación Inteligente MARPI")
    if "form_id_lub" not in st.session_state: st.session_state.form_id_lub = 0
    
    df_lista = df_completo.fillna("-")
    lista_sug = sorted([str(x) for x in list(set(df_lista['Tag'].tolist() + df_lista['N_Serie'].tolist())) if x != "-"] )
    
    opcion_elegida = st.selectbox("Seleccione TAG o N° DE SERIE", [""] + lista_sug, key=f"s_lub_{st.session_state.form_id_lub}")

    motor_e = None
    if opcion_elegida != "":
        res = df_lista[(df_lista['Tag'] == opcion_elegida) | (df_lista['N_Serie'] == opcion_elegida)]
        if not res.empty: motor_e = res.iloc[-1]

    with st.form(key=f"f_lub_{st.session_state.form_id_lub}"):
        col1, col2 = st.columns(2)
        rod_la = col1.text_input("Rodamiento LA", value=str(motor_e['Rodamiento LA']) if motor_e is not None and 'Rodamiento LA' in motor_e else "").upper()
        rod_loa = col2.text_input("Rodamiento LOA", value=str(motor_e['Rodamiento LOA']) if motor_e is not None and 'Rodamiento LOA' in motor_e else "").upper()
        
        gr_la_sug = calcular_grasa_avanzado(rod_la)
        gr_loa_sug = calcular_grasa_avanzado(rod_loa)
        
        resp_r = st.text_input("Técnico Responsable")
        g_la = st.number_input("Gramos Reales LA", value=float(gr_la_sug))
        g_loa = st.number_input("Gramos Reales LOA", value=float(gr_loa_sug))
        tipo_t = st.radio("Tipo", ["Preventivo", "Correctivo"])
        obs = st.text_area("Notas")
        
        if st.form_submit_button("💾 GUARDAR LUBRICACIÓN"):
            if opcion_elegida and resp_r:
                nueva_lub = {
                    "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": opcion_elegida,
                    "Responsable": resp_r, "Rodamiento LA": rod_la, "Gramos LA": g_la,
                    "Rodamiento LOA": rod_loa, "Gramos LOA": g_loa, "Descripcion": tipo_t, "Observaciones": obs
                }
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_lub])], ignore_index=True)
                conn.update(data=df_final)
                st.session_state.form_id_lub += 1
                st.success("✅ Guardado")
                st.rerun()

elif modo == "Mediciones de Campo":
    st.title("⚡ Mediciones (Megado y Continuidad)")
    if "cnt_meg" not in st.session_state: st.session_state.cnt_meg = 0
    tag_ini = st.session_state.get('tag_fijo', '')

    with st.form(key=f"f_meg_{st.session_state.cnt_meg}"):
        c_t, c_r = st.columns(2)
        t = c_t.text_input("TAG MOTOR", value=tag_ini).upper()
        resp = c_r.text_input("Técnico Responsable")
        
        st.subheader("📊 Mediciones")
        c1, c2, c3 = st.columns(3)
        tv1 = c1.text_input("T - V1 (Ω)")
        tu1 = c2.text_input("T - U1 (Ω)")
        tw1 = c3.text_input("T - W1 (Ω)")
        
        u1u2 = st.text_input("U1 - U2 (Ω)")
        tl1 = st.text_input("T - L1 (MΩ)")
        
        if st.form_submit_button("💾 GUARDAR MEDICIONES"):
            if t and resp:
                det = f"Res: T-V1:{tv1}, T-U1:{tu1}, T-W1:{tw1} | Bornes: U1-U2:{u1u2} | Línea: T-L1:{tl1}"
                nueva_m = {
                    "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t,
                    "Responsable": resp, "Descripcion": det, "Taller_Externo": "Medición Campo"
                }
                df_f = pd.concat([df_completo, pd.DataFrame([nueva_m])], ignore_index=True)
                conn.update(data=df_f)
                st.session_state.cnt_meg += 1
                st.success("✅ Mediciones guardadas")
                st.rerun()
            
st.markdown("---")
st.caption("Sistema desarrollado y diseñado por Heber Ortiz | Marpi Electricidad ⚡")
































































































































































































































































































































































































































