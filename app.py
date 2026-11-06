import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Seguimiento Cierre Anual", layout="wide")

st.title("📊 Sistema de Seguimiento: Compras, Facturas y Tesorería")

# --- URL DE TU APLICACIÓN WEB DE APPS SCRIPT ---
# Pega aquí la URL exacta que te generó Apps Script al implementar
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxYoMIZxbExpGLZNTMedKwFrPIAdEyZKRV205xefKoYZ65XxKgvAeXR5SQ-LALU8cndww/exec"

# Función para obtener datos desde Google Sheets vía Apps Script
def obtener_datos(sheet_name):
    try:
        url = f"{WEB_APP_URL}?action=getData&sheet={sheet_name}"
        response = requests.get(url)
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al conectar con la hoja {sheet_name}: {e}")
        return pd.DataFrame()

# Función para enviar/agregar una fila nueva a Google Sheets vía Apps Script
def guardar_fila(sheet_name, values):
    try:
        payload = {
            "action": "appendRow",
            "sheet": sheet_name,
            "values": values
        }
        response = requests.post(WEB_APP_URL, json=payload)
        return response.json()
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return None

# Menú lateral para navegar
menu = st.sidebar.selectbox("Seleccionar Sección", ["Compras", "Facturas", "Tesorería"])

# ==========================================
# 1. SECCIÓN COMPRAS
# ==========================================
if menu == "Compras":
    st.header("📝 Registro de Órdenes de Compra")
    
    with st.form("form_compras"):
        n_orden = st.text_input("NUMERO ORDEN DE COMPRAS")
        fecha = st.date_input("FECHA")
        n_proveedor = st.text_input("N PROVEEDOR")
        proveedor = st.text_input("PROVEEDOR")
        monto = st.number_input("MONTO", min_value=0.0, format="%.2f")
        estado = st.selectbox("ESTADO", ["Pendiente", "Aprobado", "Rechazado", "Pagado"])
        
        submit_compra = st.form_submit_button("Guardar Orden de Compra")
        
        if submit_compra:
            if n_orden:
                valores = [n_orden, str(fecha), n_proveedor, proveedor, monto, estado]
                resultado = guardar_fila("COMPRAS", valores)
                if resultado:
                    st.success(f"¡Orden de Compra {n_orden} guardada exitosamente!")
            else:
                st.warning("Por favor completa al menos el Número de Orden de Compras.")

    st.subheader("📋 Registros Actuales en Compras")
    df_compras = obtener_datos("COMPRAS")
    if not df_compras.empty:
        st.dataframe(df_compras, use_container_width=True)
    else:
        st.info("No hay registros todavía o verifica la URL de la API.")

# ==========================================
# 2. SECCIÓN FACTURAS (Desde Columna G en adelante)
# ==========================================
elif menu == "Facturas":
    st.header("📄 Gestión de Facturas")
    
    df_compras = obtener_datos("COMPRAS")

    if not df_compras.empty and "NUMERO ORDEN DE COMPRAS" in df_compras.columns:
        lista_ordenes = df_compras["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_buscar = st.selectbox("Seleccione el N° de Orden de Compra:", [""] + lista_ordenes)
        
        if n_orden_buscar and n_orden_buscar != "":
            datos_orden = df_compras[df_compras["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_buscar].iloc[0]
            
            st.info("Datos recuperados de la Orden de Compra:")
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Proveedor:** {datos_orden.get('PROVEEDOR', '')}")
            col2.write(f"**Monto Compra:** {datos_orden.get('MONTO', '')}")
            col3.write(f"**Estado:** {datos_orden.get('ESTADO', '')}")
            
            with st.form("form_facturas"):
                st.subheader("Completar datos de Facturación (Desde Columna G)")
                col_g = st.text_input("N° de Factura")
                col_h = st.date_input("
