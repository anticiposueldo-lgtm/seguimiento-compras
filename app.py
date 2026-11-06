import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Seguimiento Cierre Anual", layout="wide")

st.title("📊 Sistema de Seguimiento: Compras, Facturas y Tesorería")

# --- CONFIGURACIÓN DE CONEXIÓN CON GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Utiliza los secretos configurados en Streamlit Cloud
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Abre tu planilla de Google Sheets
    sheet = client.open("SEGUIMIENTO CIERRE ANUAL")
    return sheet

try:
    spreadsheet = conectar_gsheets()
except Exception as e:
    st.error(f"Error al conectar con Google Sheets. Asegurate de configurar los secretos. Detalle: {e}")

# Menú lateral para navegar entre secciones
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
                try:
                    worksheet = spreadsheet.worksheet("COMPRAS")
                    # Agrega la fila con los datos en el orden de tus columnas (A hasta F)
                    worksheet.append_row([n_orden, str(fecha), n_proveedor, proveedor, monto, estado])
                    st.success(f"¡Orden de Compra {n_orden} guardada exitosamente en la pestaña COMPRAS!")
                except Exception as e:
                    st.error(f"Error al guardar en la hoja: {e}")
            else:
                st.warning("Por favor completa al menos el Número de Orden de Compras.")

    # Mostrar registros actuales de compras
    st.subheader("📋 Registros Actuales en Compras")
    try:
        worksheet = spreadsheet.worksheet("COMPRAS")
        data = worksheet.get_all_records()
        if data:
            df_compras = pd.DataFrame(data)
            st.dataframe(df_compras, use_container_width=True)
        else:
            st.info("No hay registros todavía en la pestaña COMPRAS.")
    except Exception as e:
        st.warning("No se pudo cargar la vista previa de compras.")

# ==========================================
# 2. SECCIÓN FACTURAS (Desde Columna G en adelante)
# ==========================================
elif menu == "Facturas":
    st.header("📄 Gestión de Facturas")
    
    try:
        ws_compras = spreadsheet.worksheet("COMPRAS")
        df_compras = pd.DataFrame(ws_compras.get_all_records())
    except:
        df_compras = pd.DataFrame()

    if not df_compras.empty and "NUMERO ORDEN DE COMPRAS" in df_compras.columns:
        # Selector o buscador de orden de compra
        lista_ordenes = df_compras["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_buscar = st.selectbox("Seleccione o busque el N° de Orden de Compra:", [""] + lista_ordenes)
        
        if n_orden_buscar and n_orden_buscar != "":
            # Filtrar datos de esa orden en Compras
            datos_orden = df_compras[df_compras["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_buscar].iloc[0]
            
            st.info("Datos recuperados de la Orden de Compra:")
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Proveedor:** {datos_orden.get('PROVEEDOR', '')}")
            col2.write(f"**Monto Compra:** {datos_orden.get('MONTO', '')}")
            col3.write(f"**Estado:** {datos_orden.get('ESTADO', '')}")
            
            with st.form("form_facturas"):
                st.subheader("Completar datos de Facturación (Desde Columna G)")
                col_g = st.text_input("N° de Factura / Detalle G")
                col_h = st.date_input("Fecha de Factura / Detalle H")
                col_i = st.number_input("Monto Facturado / Detalle I", min_value=0.0, format="%.2f")
                col_j = st.text_input("Observaciones Factura / Detalle J")
                
                submit_factura = st.form_submit_button("Guardar Datos de Factura")
                
                if submit_factura:
                    try:
                        ws_facturas = spreadsheet.worksheet("FACTURAS")
                        # Guarda los datos correspondientes en la pestaña Facturas
                        ws_facturas.append_row([n_orden_buscar, str(col_g), str(col_h), col_i, col_j])
                        st.success("¡Datos de factura guardados correctamente!")
                    except Exception as e:
                        st.error(f"Error al guardar en la pestaña Facturas: {e}")
    else:
        st.warning("Primero debes registrar Órdenes de Compra en la pestaña COMPRAS.")

# ==========================================
# 3. SECCIÓN TESORERÍA (Desde Columna K en adelante)
# ==========================================
elif menu == "Tesorería":
    st.header("💰 Gestión de Tesorería")
    
    try:
        ws_compras = spreadsheet.worksheet("COMPRAS")
        df_compras = pd.DataFrame(ws_compras.get_all_records())
    except:
        df_compras = pd.DataFrame()

    if not df_compras.empty and "NUMERO ORDEN DE COMPRAS" in df_compras.columns:
        lista_ordenes = df_compras["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_teso = st.selectbox("Seleccione el N° de Orden de Compra para Tesorería:", [""] + lista_ordenes)
        
        if n_orden_teso and n_orden_teso != "":
            datos_orden = df_compras[df_compras["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_teso].iloc[0]
            
            st.info("Datos de referencia de la Compra:")
            st.write(f"**Proveedor:** {datos_orden.get('PROVEEDOR', '')} | **Monto:** {datos_orden.get('MONTO', '')}")
            
            with st.form("form_tesoreria"):
                st.subheader("Completar datos de Pago (Desde Columna K)")
                col_k = st.date_input("Fecha de Pago / Detalle K")
                col_l = st.text_input("N° Orden de Pago / Detalle L")
                col_m = st.selectbox("Medio de Pago / Detalle M", ["Transferencia", "Cheque", "Efectivo"])
                col_n = st.text_input("Comprobante / Detalle N")
                
                submit_teso = st.form_submit_button("Guardar Datos de Tesorería")
                
                if submit_teso:
                    try:
                        ws_tesoreria = spreadsheet.worksheet("TESORERIA")
                        ws_tesoreria.append_row([n_orden_teso, str(col_k), col_l, col_m, col_n])
                        st.success("¡Datos de tesorería guardados correctamente!")
                    except Exception as e:
                        st.error(f"Error al guardar en la pestaña Tesorería: {e}")
    else:
        st.warning("No hay órdenes de compra disponibles para asociar en tesorería.")
