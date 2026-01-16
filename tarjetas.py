import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import qrcode
from io import BytesIO
import os
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="Marpi Motores", page_icon="⚡", layout="wide")

parametros = st.query_params
query_tag = parametros.get("tag", "").upper()

if 'mostrar_form' not in st.session_state:
    st.session_state.mostrar_form = False

def activar_formulario():
    st.session_state.mostrar_form = True

# --- 2. FUNCIÓN GENERAR PDF ---
def generar_pdf(df_historial, tag_motor):
    try:
        # Orientación vertical, unidad mm, formato A4
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # --- ENCABEZADO PROFESIONAL ---
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 30)
        
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(0, 51, 102) # Azul oscuro profesional
        pdf.cell(0, 15, 'INFORME TECNICO DE MOTORES', 0, 1, 'R')
        
        pdf.set_draw_color(0, 51, 102)
        pdf.set_line_width(0.8)
        pdf.line(10, 25, 200, 25) # Línea decorativa
        pdf.ln(10)
        
        # --- TABLA DE DATOS DEL MOTOR ---
        fijos = df_historial.iloc[0]
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"  DATOS DEL EQUIPO: {tag_motor}", 0, 1, 'L', True)
        
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(0, 0, 0)
        # Fila de datos principales
        pdf.cell(47, 7, f"POTENCIA: {fijos.get('Potencia','-')}", 1, 0, 'C')
        pdf.cell(47, 7, f"RPM: {fijos.get('RPM','-')}", 1, 0, 'C')
        pdf.cell(48, 7, f"FRAME: {fijos.get('Frame','-')}", 1, 0, 'C')
        pdf.cell(48, 7, f"N° SERIE: {fijos.get('N_Serie','-')}", 1, 1, 'C')

        # --- HISTORIAL DE INTERVENCIONES ---
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, "HISTORIAL DE MANTENIMIENTO Y MEDICIONES", 0, 1, 'L')
        pdf.ln(2)

        for _, row in df_historial.sort_index(ascending=False).iterrows():
            # Bloque de Fecha y Responsable
            pdf.set_fill_color(0, 51, 102)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 10)
            header_text = f" FECHA: {row.get('Fecha', '')} | RESPONSABLE: {row.get('Responsable', '')}"
            pdf.cell(0, 7, header_text.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L', True)
            
            # Cuadro de Mediciones (Estilo tabla)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(245, 245, 245)
            
            # Encabezados de mediciones
            pdf.cell(63, 6, "Resistencia Tierra (Gohm)", 1, 0, 'C', True)
            pdf.cell(63, 6, "Resistencia Bobinas (Gohm)", 1, 0, 'C', True)
            pdf.cell(64, 6, "Resistencia Interna (mohm)", 1, 1, 'C', True)
            
            pdf.set_font("Arial", '', 9)
            # Valores
            val_t = f"{row.get('RT_TU','-')} / {row.get('RT_TV','-')} / {row.get('RT_TW','-')}"
            val_b = f"{row.get('RB_UV','-')} / {row.get('RB_VW','-')} / {row.get('RB_UW','-')}"
            val_i = f"{row.get('RI_U','-')} / {row.get('RI_V','-')} / {row.get('RI_W','-')}"
            
            pdf.cell(63, 6, val_t, 1, 0, 'C')
            pdf.cell(63, 6, val_b, 1, 0, 'C')
            pdf.cell(64, 6, val_i, 1, 1, 'C')
            
            # Descripciones y Trabajos
            pdf.ln(1)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 5, "DESCRIPCION DE TRABAJOS:", 0, 1)
            pdf.set_font("Arial", '', 9)
            desc = str(row.get('Descripcion', 'Sin descripcion'))
            pdf.multi_cell(0, 5, desc.encode('latin-1', 'replace').decode('latin-1'), 'LRB')
            
            if row.get('Taller_Externo') and str(row.get('Taller_Externo')) != 'nan':
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(0, 5, "TRABAJOS EXTERNOS / TALLER:", 0, 1)
                pdf.set_font("Arial", '', 9)
                pdf.multi_cell(0, 5, str(row.get('Taller_Externo')).encode('latin-1', 'replace').decode('latin-1'), 'LRB')
            
            pdf.ln(5) # Espacio entre registros
            
        # Pie de página
        pdf.set_y(-20)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, 'Marpi Electricidad - Informe generado automaticamente', 0, 0, 'C')
            
        return pdf.output(dest='S').encode('latin-1', 'replace')
    except Exception as e:
        st.error(f"Error en PDF: {e}")
        return None

# --- 3. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_completo = conn.read(ttl=0)
except:
    st.error("Error de conexión.")
    df_completo = pd.DataFrame()

# --- 4. INTERFAZ ---
with st.sidebar:
    st.header("⚡ Marpi Electricidad")
    # Si entramos por QR, forzamos que el menú se ponga en Historial
    inicio_modo = "🔍 Historial / QR" if query_tag else "📝 Registro Nuevo"
    modo = st.radio("Menú:", ["📝 Registro Nuevo", "🔍 Historial / QR"], index=1 if query_tag else 0)

# --- MODO REGISTRO NUEVO (CON AUTO-LIMPIEZA) ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)
if modo == "📝 Registro Nuevo":
    st.title("📝 Alta y Registro Inicial de Motor")
    fecha = st.date_input("fecha", date.today(), format="DD/MM/YYYY")
    
    # Creamos un contador en el estado de la sesión para reiniciar el formulario
    if "form_count" not in st.session_state:
        st.session_state.form_count = 0

    # Al cambiar la 'key' del formulario, todos los campos se limpian
    with st.form(key=f"alta_motor_{st.session_state.form_count}"):
        col_id1, col_id2, col_id3, col_id4, col_id5 = st.columns(5)
        t = col_id1.text_input("TAG/ID MOTOR").upper()
        p = col_id2.text_input("Potencia (HP/kW)")
        r = col_id3.selectbox("RPM", ["-", "750", "1500", "3000"])
        f = col_id4.text_input("Frame / Carcasa")
        sn = col_id5.text_input("N° de Serie")
        
        st.markdown("---")
        st.subheader("🔍 Mediciones Iniciales")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.write("**Tierra (MΩ)**")
            rt_tu = st.text_input("T-U")
            rt_tv = st.text_input("T-V")
            rt_tw = st.text_input("T-W")
        with m2:
            st.write("**Bobinas (MΩ)**")
            rb_uv = st.text_input("U-V")
            rb_vw = st.text_input("V-W")
            rb_uw = st.text_input("U-W")
        with m3:
            st.write("**Interna (mΩ)**")
            ri_u = st.text_input("U1-U2")
            ri_v = st.text_input("V1-V2")
            ri_w = st.text_input("W1-W2")
            
        st.markdown("---")
        resp = st.text_input("Técnico Responsable")
        desc = st.text_area("Descripción inicial / Trabajos")
        ext = st.text_area("Trabajos Externos")
        
        btn_guardar = st.form_submit_button("💾 REGISTRAR MOTOR")
        
        if btn_guardar:
            if t and resp:
                nueva_fila = {
                    "Fecha": date.today().strftime("%d/%m/%Y"), "Tag": t, "Potencia": p, "RPM": r, "Frame": f,
                    "N_Serie": sn, "Responsable": resp, "Descripcion": desc, "Taller_Externo": ext,
                    "RT_TU": rt_tu, "RT_TV": rt_tv, "RT_TW": rt_tw,
                    "RB_UV": rb_uv, "RB_VW": rb_vw, "RB_UW": rb_uw,
                    "RI_U": ri_u, "RI_V": ri_v, "RI_W": ri_w
                }
                
                # Guardar en Google Sheets
                df_final = pd.concat([df_completo, pd.DataFrame([nueva_fila])], ignore_index=True)
                conn.update(data=df_final)
                
                # AVISO DE ÉXITO
                st.success(f"✅ ¡Excelente! El motor {t} ha sido guardado correctamente.")
                st.balloons() # Un pequeño efecto visual de celebración
                
                # CAMBIAMOS LA KEY PARA LIMPIAR TODO
                st.session_state.form_count += 1
                st.rerun() 
            else:
                st.error("⚠️ El TAG y el Técnico son obligatorios para guardar.")

# --- MODO HISTORIAL / QR ---
elif modo == "🔍 Historial / QR":
    st.title("🔍 Hoja de Vida del Motor")
    
    # El valor por defecto ahora es query_tag (lo que lee del QR)
    id_ver = st.text_input("ESCRIBIR TAG:", value=query_tag).strip().upper()
    
    if id_ver:
        historial = df_completo[
            (df_completo['Tag'].astype(str).str.upper() == id_ver) | 
            (df_completo['N_serie'].astype(str).str.upper() == id_ver)
]
        
        if not historial.empty:
            orig = historial.iloc[0]
            st.subheader(f"Motor: {id_ver} | {orig.get('Potencia','-')} | {orig.get('RPM','-')} RPM")
            
            col_pdf, col_qr, col_form = st.columns(3)
            
            # 1. PDF
            pdf_b = generar_pdf(historial, id_ver)
            if pdf_b:
                col_pdf.download_button("📥 Informe PDF", pdf_b, f"Informe_{id_ver}.pdf")
            
            # 2. QR ÚNICO
            url_base = "https://marpi-motores-mciqbovz6wqnaj9mw7fytb.streamlit.app/"
            link_directo = f"{url_base}?tag={id_ver}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(link_directo)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img_qr.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            col_qr.image(byte_im, width=120, caption="QR Único")
            col_qr.download_button("💾 Guardar imagen QR", byte_im, f"QR_{id_ver}.png", "image/png")
            
            # 3. NUEVA REPARACIÓN
            col_form.button("➕ Cargar Nueva Reparación", on_click=activar_formulario)
            
            if st.session_state.mostrar_form:
                with st.form("nueva_rep"):
                    st.write("### 🛠️ Registrar Intervención")
                    f_rep = st.date_input("Fecha", date.today())
                    t_resp = st.text_input("Técnico")
                    
                    st.markdown("**Mediciones Actuales**")
                    col_t, col_b, col_i = st.columns(3)
                    with col_t:
                        rt1 = st.text_input("T-U (Tierra)")
                        rt2 = st.text_input("T-V (Tierra)")
                        rt3 = st.text_input("T-W (Tierra)")
                    with col_b:
                        rb1 = st.text_input("U-V (Bobina)")
                        rb2 = st.text_input("V-W (Bobina)")
                        rb3 = st.text_input("U-W (Bobina)")
                    with col_i:
                        ri1 = st.text_input("U1-U2 (Interna)")
                        ri2 = st.text_input("V1-V2 (Interna)")
                        ri3 = st.text_input("W1-W2 (Interna)")
                    
                    d_rep = st.text_area("Trabajos realizados")
                    e_rep = st.text_area("Taller externo")
                    
                    if st.form_submit_button("💾 GUARDAR EN HISTORIAL"):
                        nueva_data = {
                            "Fecha": f_rep.strftime("%d/%m/%Y"), "Tag": id_ver, "Responsable": t_resp,
                            "Potencia": orig.get('Potencia','-'), "RPM": orig.get('RPM', '-'),
                            "Frame": orig.get('Frame', '-'),
                            "RT_TU": rt1, "RT_TV": rt2, "RT_TW": rt3,
                            "RB_UV": rb1, "RB_VW": rb2, "RB_UW": rb3,
                            "RI_U": ri1, "RI_V": ri2, "RI_W": ri3,
                            "Descripcion": d_rep, "Taller_Externo": e_rep
                        }
                        df_final = pd.concat([df_completo, pd.DataFrame([nueva_data])], ignore_index=True)
                        conn.update(data=df_final)
                        st.session_state.mostrar_form = False
                        st.rerun()

            st.markdown("---")
            st.dataframe(historial.sort_index(ascending=False))
        else:
            st.warning(f"⚠️ El motor '{id_ver}' no existe en la base de datos.")
st.markdown("---")
st.caption("Sistema diseñado y desarollado por Heber Ortiz | Marpi Electricidad ⚡")













































































































































































































