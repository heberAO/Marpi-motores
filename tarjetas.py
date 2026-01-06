import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# Función ultra-simple para probar conexión
def guardar_datos(f, r, t, d):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = conn.read(ttl=0)
        nuevo = pd.DataFrame([{"Fecha": str(f), "Responsable": r, "Tag": t, "Descripcion": d}])
        df_final = pd.concat([df_existente, nuevo], ignore_index=True)
        conn.update(data=df_final)
        return True, "Ok"
    except Exception as e:
        return False, str(e)

# Formulario básico
st.title("MARPI - TEST DE CONEXIÓN")
f = st.date_input("Fecha")
r = st.text_input("Responsable")
t = st.text_input("Tag")
d = st.text_area("Notas")

if st.button("PROBAR GUARDADO"):
    exito, msj = guardar_datos(f, r, t, d)
    if exito:
        st.success("✅ ¡FUNCIONA! Datos guardados.")
    else:
        st.error(f"❌ Error: {msj}")






