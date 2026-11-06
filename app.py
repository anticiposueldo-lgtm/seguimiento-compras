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

def guardar_fila(sheet_name, values, n_orden=None, nuevo_estado=None):
    try:
        payload = {
            "action": "appendRow", 
            "sheet": sheet_name, 
            "values": values,
            "nOrden": n_orden,
            "nuevoEstado": nuevo_estado
        }
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
    
    df_compras_actual = obtener_datos("COMPRAS")
    orden_existente = None
    
    if n_orden and not df_compras_actual.empty and "NUMERO ORDEN DE COMPRAS" in df_compras_actual.columns:
        match = df_compras_actual[df_compras_actual["NUMERO ORDEN DE COMPRAS"].astype(str).str.strip() == str(n_orden).strip()]
        if not match.empty:
            fila_encontrada = match.iloc[0]
            if str(fila_encontrada.get("PROVEEDOR", "")) != "ANULADO":
                orden_existente = fila_encontrada

    default_n_prov = str(orden_existente.get("N PROVEEDOR", "")) if orden_existente is not None else ""
    default_monto = float(orden_existente.get("MONTO", 0.0)) if orden_existente is not None else 0.0
    default_estado = str(orden_existente.get("ESTADO", "Pendiente")) if orden_existente is not None else "Pendiente"
    
    estados_disponibles = ["Pendiente", "Parcial", "Cerrada", "Aprobado", "Rechazado", "Pagado"]
    idx_estado = estados_disponibles.index(default_estado) if default_estado in estados_disponibles else 0

    fecha = st.date_input("FECHA")
    n_proveedor = st.text_input("N PROVEEDOR", value=default_n_prov, key="input_n_proveedor")
    
    nombre_proveedor_auto = ""
    if n_proveedor:
        nombre_proveedor_auto = buscar_proveedor(n_proveedor)
        if not nombre_proveedor_auto:
            nombre_proveedor_auto = "PROVEEDOR NO ENCONTRADO"

    proveedor = st.text_input("PROVEEDOR", value=nombre_proveedor_auto)
    monto = st.number_input("MONTO", min_value=0.0, format="%.2f", value=default_monto, key="input_monto")
    estado = st.selectbox("ESTADO", estados_disponibles, index=idx_estado)

    if orden_existente is not None:
        st.warning(f"⚠️ La Orden N° **{n_orden}** ya se encuentra registrada en la planilla.")
        if st.button("🗑️ Anular / Limpiar este Registro"):
            res = eliminar_fila("COMPRAS", str(n_orden))
            if res and res.get("status") == "deleted":
                st.success(f"¡Orden N° {n_orden} anulada correctamente!")
                st.session_state.input_n_orden = ""
                st.session_state.input_n_proveedor = ""
                st.session_state.input_monto = 0.0
                st.rerun()
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
        df_validas = df_compras[df_compras["PROVEEDOR"].astype(str) != "ANULADO"]
        lista_ordenes = df_validas["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_buscar = st.selectbox("Seleccione el N° de Orden de Compra:", [""] + lista_ordenes)
        
        if n_orden_buscar and n_orden_buscar != "":
            datos_orden = df_validas[df_validas["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_buscar].iloc[0]
            st.info("Datos recuperados de la Orden de Compra:")
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Proveedor:** {datos_orden.get('PROVEEDOR', '')}")
            
            # Formateamos el monto de la compra con separadores de miles y 2 decimales
            monto_compra_raw = datos_orden.get('MONTO', 0)
            monto_compra_fmt = f"${float(monto_compra_raw):,.2f}" if pd.notnull(monto_compra_raw) and str(monto_compra_raw) != "" else "$0.00"
            col2.write(f"**Monto Compra:** {monto_compra_fmt}")
            
            col3.write(f"**Estado Actual:** {datos_orden.get('ESTADO', '')}")
            
            # clear_on_submit=True limpia automáticamente las celdas tras hacer submit
            with st.form("form_facturas", clear_on_submit=True):
                st.subheader("Completar datos de Facturación (Columnas G a J) y Estado")
                n_factura = st.text_input("N° de Factura")
                fecha_comprobante = st.date_input("Fecha de Comprobante")
                monto_factura = st.number_input("Monto Factura", min_value=0.0, format="%.2f")
                fecha_vencimiento = st.date_input("Fecha de Vencimiento")
                
                nuevo_estado_compra = st.selectbox("Actualizar Estado de la Orden de Compra:", ["Parcial", "Cerrada", "Pendiente"])
                
                submit_factura = st.form_submit_button("Guardar Datos de Factura")
                if submit_factura:
                    valores_fila = [
                        str(datos_orden.get("NUMERO ORDEN DE COMPRAS", "")),
                        str(datos_orden.get("FECHA", "")),
                        str(datos_orden.get("N PROVEEDOR", "")),
                        str(datos_orden.get("PROVEEDOR", "")),
                        float(datos_orden.get("MONTO", 0.0)),
                        str(nuevo_estado_compra), 
                        str(n_factura),           
                        str(fecha_comprobante),   
                        float(monto_factura),     
                        str(fecha_vencimiento)    
                    ]
                    
                    guardar_fila("FACTURAS", valores_fila, n_orden=n_orden_buscar, nuevo_estado=nuevo_estado_compra)
                    st.success("¡Datos de factura guardados y estado de compra actualizado correctamente!")

# ==========================================
# 3. SECCIÓN TESORERÍA
# ==========================================
elif menu == "Tesorería":
    st.header("💰 Gestión de Tesorería")
    df_facturas = obtener_datos("FACTURAS")
    
    if not df_facturas.empty and "NUMERO ORDEN DE COMPRAS" in df_facturas.columns:
        df_val_teso = df_facturas[df_facturas["PROVEEDOR"].astype(str) != "ANULADO"]
        lista_ordenes = df_val_teso["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_teso = st.selectbox("Seleccione el N° de Orden de Compra para Tesorería:", [""] + lista_ordenes)
        
        if n_orden_teso and n_orden_teso != "":
            datos_factura = df_val_teso[df_val_teso["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_teso].iloc[0]
            st.info("Datos de referencia (Arrastrados desde Facturas):")
            st.write(f"**Proveedor:** {datos_factura.get('PROVEEDOR', '')} | **N° Factura:** {datos_factura.get('N FACTURA', '')} | **Monto Factura:** {datos_factura.get('MONTO', '')}")
            
            # clear_on_submit=True limpia automáticamente los campos de pago tras guardar
            with st.form("form_tesoreria", clear_on_submit=True):
                st.subheader("Completar datos de Pago (A partir de la Columna K)")
                fecha_pago = st.date_input("Fecha de Pago")
                n_orden_pago = st.text_input("N° Orden de Pago")
                medio_pago = st.selectbox("Medio de Pago", ["Transferencia", "Cheque", "Efectivo"])
                fecha_debito_cheque = st.date_input("Fecha Débito / Cheque")
                
                submit_teso = st.form_submit_button("Guardar Datos de Tesorería")
                if submit_teso:
                    valores_teso = [
                        str(datos_factura.get("NUMERO ORDEN DE COMPRAS", "")),
                        str(datos_factura.get("FECHA", "")),
                        str(datos_factura.get("N PROVEEDOR", "")),
                        str(datos_factura.get("PROVEEDOR", "")),
                        float(datos_factura.get("MONTO", 0.0) if pd.notnull(datos_factura.get("MONTO")) else 0.0),
                        str(datos_factura.get("ESTADO", "")),
                        str(datos_factura.get("N FACTURA", "")),
                        str(datos_factura.get("FECHA DE COMPROBANTE", "")),
                        float(datos_factura.get("MONTO FACTURA", 0.0) if "MONTO FACTURA" in datos_factura and pd.notnull(datos_factura.get("MONTO FACTURA")) else 0.0),
                        str(datos_factura.get("FECHA DE VENCIMIENTO", "")),
                        str(fecha_pago),         
                        str(n_orden_pago),       
                        str(medio_pago),         
                        str(fecha_debito_cheque) 
                    ]
                    
                    guardar_fila("TESORERIA", valores_teso)
                    st.success("¡Datos de tesorería guardados encadenadamente de forma exitosa!")
