import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Seguimiento Cierre Anual", layout="wide")

st.title("📊 Sistema de Seguimiento: Compras, Facturas y Tesorería")

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx64d_-HsdEofZLzLg3EQ58DeS_2ESQ5PlbTdKp4ObxkRHcQgtmdNJ1MIcFyjjDRELJ1Q/exec"

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

def eliminar_fila(sheet_name, orden):
    try:
        payload = {"action": "deleteRow", "sheet": sheet_name, "orden": orden}
        response = requests.post(WEB_APP_URL, json=payload)
        return response.json()
    except Exception as e:
        st.error(f"Error al eliminar: {e}")
        return None

menu = st.sidebar.selectbox("Seleccionar Sección", ["Compras", "Facturas", "Tesorería"])

# ==========================================
# 1. SECCIÓN COMPRAS
# ==========================================
if menu == "Compras":
    st.header("📝 Registro de Órdenes de Compra")
    
    if "input_n_orden" not in st.session_state:
        st.session_state.input_n_orden = ""
    if "input_n_proveedor" not in st.session_state:
        st.session_state.input_n_proveedor = ""
    if "input_monto" not in st.session_state:
        st.session_state.input_monto = 0.0

    n_orden = st.text_input("NUMERO ORDEN DE COMPRAS", key="input_n_orden")
    
    # Consultamos si la orden ya existe
    df_compras_actual = obtener_datos("COMPRAS")
    orden_existe = False
    
    if n_orden and not df_compras_actual.empty and "NUMERO ORDEN DE COMPRAS" in df_compras_actual.columns:
        match = df_compras_actual[df_compras_actual["NUMERO ORDEN DE COMPRAS"].astype(str).str.strip() == str(n_orden).strip()]
        if not match.empty:
            orden_existe = True

    fecha = st.date_input("FECHA")
    n_proveedor = st.text_input("N PROVEEDOR", key="input_n_proveedor")
    
    nombre_proveedor_auto = ""
    if n_proveedor:
        nombre_proveedor_auto = buscar_proveedor(n_proveedor)
        if not nombre_proveedor_auto:
            nombre_proveedor_auto = "PROVEEDOR NO ENCONTRADO"

    proveedor = st.text_input("PROVEEDOR", value=nombre_proveedor_auto)
    monto = st.number_input("MONTO", min_value=0.0, format="%.2f", key="input_monto")
    estado = st.selectbox("ESTADO", ["Pendiente", "Aprobado", "Rechazado", "Pagado"])

    if orden_existe:
        st.warning(f"⚠️ La Orden N° **{n_orden}** ya se encuentra registrada.")
        
        if st.button("🗑️ Eliminar Registro Existente"):
            res = eliminar_fila("COMPRAS", str(n_orden))
            if res and res.get("status") == "deleted":
                st.success(f"¡Orden N° {n_orden} eliminada correctamente!")
                st.session_state.input_n_orden = ""
                st.session_state.input_n_proveedor = ""
                st.session_state.input_monto = 0.0
                st.rerun()
            else:
                st.error("No se pudo eliminar el registro de la hoja.")
    else:
        if st.button("Guardar Orden de Compra"):
            if n_orden:
                valores = [str(n_orden), str(fecha), str(n_proveedor), str(proveedor), float(monto), str(estado)]
                resultado = guardar_fila("COMPRAS", valores)
                if resultado:
                    st.success(f"¡Orden de Compra {n_orden} guardada exitosamente!")
                    st.session_state.input_n_orden = ""
                    st.session_state.input_n_proveedor = ""
                    st.session_state.input_monto = 0.0
                    st.rerun()
            else:
                st.warning("Por favor completa al menos el Número de Orden de Compras.")

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
