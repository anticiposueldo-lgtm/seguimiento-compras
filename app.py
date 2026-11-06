import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Seguimiento Cierre Anual", layout="wide")

st.title("📊 Sistema de Seguimiento: Compras, Facturas y Tesorería")

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxYoMIZxbExpGLZNTMedKwFrPIAdEyZKRV205xefKoYZ65XxKgvAeXR5SQ-LALU8cndww/exec"

def obtener_datos(sheet_name):
    try:
        url = f"{WEB_APP_URL}?action=getData&sheet={sheet_name}"
        response = requests.get(url)
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error al conectar con la hoja {sheet_name}: {e}")
        return pd.DataFrame()

def buscar_proveedor(codigo):
    try:
        url = f"{WEB_APP_URL}?action=getProveedor&codigo={codigo}"
        response = requests.get(url)
        data = response.json()
        return data.get("razonSocial", "")
    except:
        return ""

def guardar_fila(sheet_name, values):
    try:
        payload = {"action": "appendRow", "sheet": sheet_name, "values": values}
        response = requests.post(WEB_APP_URL, json=payload)
        return response.json()
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return None

menu = st.sidebar.selectbox("Seleccionar Sección", ["Compras", "Facturas", "Tesorería"])

# ==========================================
# 1. SECCIÓN COMPRAS
# ==========================================
if menu == "Compras":
    st.header("📝 Registro de Órdenes de Compra")
    
    with st.form("form_compras"):
        n_orden = st.text_input("NUMERO ORDEN DE COMPRAS")
        fecha = st.date_input("FECHA")
        
        # Campo de N° Proveedor (al cambiar y presionar Enter o salir del campo, busca solo)
        n_proveedor = st.text_input("N PROVEEDOR")
        
        # Buscamos automáticamente si se ingresó un código
        nombre_proveedor_auto = ""
        if n_proveedor:
            nombre_proveedor_auto = buscar_proveedor(n_proveedor)
            if not nombre_proveedor_auto:
                nombre_proveedor_auto = "PROVEEDOR NO ENCONTRADO"

        proveedor = st.text_input("PROVEEDOR", value=nombre_proveedor_auto)
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
        st.info("No hay registros todavía o verifica la conexión.")

# ==========================================
# 2. SECCIÓN FACTURAS
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
                col_h = st.date_input("Fecha de Comprobante")
                col_i = st.number_input("Monto Factura", min_value=0.0, format="%.2f")
                col_j = st.text_input("Observaciones / Detalles")
                
                submit_factura = st.form_submit_button("Guardar Datos de Factura")
                if submit_factura:
                    guardar_fila("FACTURAS", [n_orden_buscar, str(col_g), str(col_h), col_i, col_j])
                    st.success("¡Datos de factura guardados correctamente!")

# ==========================================
# 3. SECCIÓN TESORERÍA
# ==========================================
elif menu == "Tesorería":
    st.header("💰 Gestión de Tesorería")
    df_compras = obtener_datos("COMPRAS")
    if not df_compras.empty and "NUMERO ORDEN DE COMPRAS" in df_compras.columns:
        lista_ordenes = df_compras["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_teso = st.selectbox("Seleccione el N° de Orden de Compra para Tesorería:", [""] + lista_ordenes)
        
        if n_orden_teso and n_orden_teso != "":
            datos_orden = df_compras[df_compras["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_teso].iloc[0]
            st.info("Datos de referencia de la Compra:")
            st.write(f"**Proveedor:** {datos_orden.get('PROVEEDOR', '')} | **Monto:** {datos_orden.get('MONTO', '')}")
            
            with st.form("form_tesoreria"):
                st.subheader("Completar datos de Pago (Desde Columna K)")
                col_k = st.date_input("Fecha de Pago")
                col_l = st.text_input("N° Orden de Pago")
                col_m = st.selectbox("Medio de Pago", ["Transferencia", "Cheque", "Efectivo"])
                col_n = st.text_input("Comprobante / Detalle")
                
                submit_teso = st.form_submit_button("Guardar Datos de Tesorería")
                if submit_teso:
                    guardar_fila("TESORERIA", [n_orden_teso, str(col_k), col_l, col_m, col_n])
                    st.success("¡Datos de tesorería guardados correctamente!")
