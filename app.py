import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Seguimiento Cierre Anual", layout="wide")

# Estilo CSS para forzar alineación a la derecha en columnas numéricas y monetarias
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {
        text-align: left;
    }
    div[data-testid="stDataFrame"] td:has-text("$"),
    div[data-testid="stDataFrame"] th:has-text("Importe"),
    div[data-testid="stDataFrame"] th:has-text("Monto"),
    div[data-testid="stDataFrame"] th:has-text("Saldo"),
    div[data-testid="stDataFrame"] th:has-text("Total") {
        text-align: right !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Panel de Compras y Pagos")

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx64d_-HsdEofZLzLg3EQ58DeS_2ESQ5PlbTdKp4ObxkRHcQgtmdNJ1MIcFyjjDRELJ1Q/exec"

def formatear_moneda(valor):
    try:
        val = float(valor)
        return f"${val:,.2f}"
    except:
        return "$0.00"

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

menu = st.sidebar.radio("Secciones", ["Compras", "Facturas", "Tesorería", "Reportes"])

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
    df_facturas_actual = obtener_datos("FACTURAS")
    
    orden_existente = None
    estado_desde_facturas = None
    
    if n_orden and not df_facturas_actual.empty:
        col_oc_fac = next((c for c in df_facturas_actual.columns if "ORDEN" in c.upper()), df_facturas_actual.columns[0])
        match_fac = df_facturas_actual[df_facturas_actual[col_oc_fac].astype(str).str.strip() == str(n_orden).strip()]
        if not match_fac.empty:
            col_est_fac = next((c for c in match_fac.columns if "ESTADO" in c.upper()), match_fac.columns[5] if len(match_fac.columns) > 5 else None)
            if col_est_fac:
                estado_desde_facturas = str(match_fac.iloc[-1].get(col_est_fac, ""))

    if n_orden and not df_compras_actual.empty and "NUMERO ORDEN DE COMPRAS" in df_compras_actual.columns:
        match = df_compras_actual[df_compras_actual["NUMERO ORDEN DE COMPRAS"].astype(str).str.strip() == str(n_orden).strip()]
        if not match.empty:
            fila_encontrada = match.iloc[0]
            if str(fila_encontrada.get("PROVEEDOR", "")) != "ANULADO":
                orden_existente = fila_encontrada

    default_n_prov = str(orden_existente.get("N PROVEEDOR", "")) if orden_existente is not None else ""
    default_monto = float(orden_existente.get("MONTO", 0.0)) if orden_existente is not None else 0.0
    
    default_estado = "Pendiente"
    if estado_desde_facturas and estado_desde_facturas in ["Parcial", "Cerrada", "Pendiente"]:
        default_estado = estado_desde_facturas
    elif orden_existente is not None:
        default_estado = str(orden_existente.get("ESTADO", "Pendiente"))
    
    estados_disponibles = ["Pendiente","Anulada"]
    idx_estado = estados_disponibles.index(default_estado) if default_estado in estados_disponibles else 0

    fecha = st.date_input("FECHA")
    fecha_str = fecha.strftime("%d/%m/%Y")

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
        st.warning(f"⚠️ La Orden N° **{n_orden}** ya se encuentra registrada en la planilla. Estado actual: **{default_estado}**")
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
                valores = [str(n_orden), fecha_str, str(n_proveedor), str(proveedor), float(monto), str(estado)]
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
    df_facturas = obtener_datos("FACTURAS")
    
    if not df_compras.empty and "NUMERO ORDEN DE COMPRAS" in df_compras.columns:
        df_validas = df_compras[df_compras["PROVEEDOR"].astype(str) != "ANULADO"]
        lista_ordenes = df_validas["NUMERO ORDEN DE COMPRAS"].astype(str).tolist()
        n_orden_buscar = st.selectbox("Seleccione el N° de Orden de Compra:", [""] + lista_ordenes)
        
        if n_orden_buscar and n_orden_buscar != "":
            datos_orden = df_validas[df_validas["NUMERO ORDEN DE COMPRAS"].astype(str) == n_orden_buscar].iloc[0]
            
            estado_actual_fac = "Pendiente"
            total_facturado_previo = 0.0
            
            if not df_facturas.empty:
                col_oc_fac = df_facturas.columns[0]
                match_facs = df_facturas[df_facturas[col_oc_fac].astype(str).str.strip() == str(n_orden_buscar).strip()]
                if not match_facs.empty:
                    col_est = next((c for c in match_facs.columns if "ESTADO" in c.upper()), match_facs.columns[5] if len(match_facs.columns) > 5 else None)
                    if col_est:
                        estado_actual_fac = str(match_facs.iloc[-1].get(col_est, "Pendiente"))
                    
                    col_monto_f = next((c for c in match_facs.columns if "MONTO FACTURA" in c.upper() or "MONTO COMP" in c.upper()), match_facs.columns[8] if len(match_facs.columns) > 8 else None)
                    if col_monto_f:
                        for _, f_row in match_facs.iterrows():
                            try:
                                total_facturado_previo += float(f_row.get(col_monto_f, 0.0))
                            except:
                                pass
            
            monto_compra_total = float(datos_orden.get('MONTO', 0.0) if pd.notnull(datos_orden.get('MONTO')) else 0.0)
            monto_disponible = monto_compra_total - total_facturado_previo
            if monto_disponible < 0:
                monto_disponible = 0.0
            
            st.info("Datos recuperados de la Orden de Compra:")
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Proveedor:** {datos_orden.get('PROVEEDOR', '')}")
            col2.write(f"**Monto Compra:** {formatear_moneda(monto_compra_total)}")
            col3.write(f"**Estado Actual:** {estado_actual_fac}")
            
            if total_facturado_previo > 0:
                st.warning(f"⚠️ Ya se facturó un total de **{formatear_moneda(total_facturado_previo)}** para esta orden.")
            
            st.markdown(f"### 💵 Monto disponible para facturar: **{formatear_moneda(monto_disponible)}**")
            
            with st.form("form_facturas", clear_on_submit=True):
                st.subheader("Completar datos de Facturación y Estado")
                n_factura = st.text_input("N° de Factura")
                
                fecha_comprobante = st.date_input("Fecha de Comprobante")
                fecha_comprobante_str = fecha_comprobante.strftime("%d/%m/%Y")
                
                monto_factura = st.number_input("Monto Factura", min_value=0.0, max_value=float(monto_disponible) if monto_disponible > 0 else 0.0, value=min(100.0, monto_disponible) if monto_disponible > 0 else 0.0, format="%.2f")
                
                fecha_vencimiento = st.date_input("Fecha de Vencimiento")
                fecha_vencimiento_str = fecha_vencimiento.strftime("%d/%m/%Y")
                
                nuevo_estado_compra = st.selectbox("Actualizar Estado de la Orden de Compra:", ["Parcial", "Cerrada", "Pendiente"])
                
                submit_factura = st.form_submit_button("Guardar Datos de Factura")
                if submit_factura:
                    if nuevo_estado_compra == "Cerrada":
                        monto_disponible = 0.0
                        
                    valores_fila = [
                        str(datos_orden.get("NUMERO ORDEN DE COMPRAS", "")),
                        str(datos_orden.get("FECHA", "")),
                        str(datos_orden.get("N PROVEEDOR", "")),
                        str(datos_orden.get("PROVEEDOR", "")),
                        float(monto_compra_total),
                        str(nuevo_estado_compra), 
                        str(n_factura),           
                        fecha_comprobante_str,   
                        float(monto_factura),     
                        fecha_vencimiento_str    
                    ]
                    
                    guardar_fila("FACTURAS", valores_fila, n_orden=n_orden_buscar, nuevo_estado=nuevo_estado_compra)
                    st.success("¡Datos de factura guardados y estado de compra actualizado correctamente!")
                    st.rerun()

# ==========================================
# 3. SECCIÓN TESORERÍA
# ==========================================
elif menu == "Tesorería":
    st.header("💰 Gestión de Tesorería")
    df_facturas = obtener_datos("FACTURAS")
    df_tesoreria = obtener_datos("TESORERIA")
    
    if not df_facturas.empty:
        col_oc_facturas = df_facturas.columns[0]
        lista_ordenes = df_facturas[col_oc_facturas].astype(str).unique().tolist()
        n_orden_teso = st.selectbox("Seleccione el N° de Orden de Compra para Tesorería:", [""] + lista_ordenes)
        
        if n_orden_teso and n_orden_teso != "":
            facturas_orden = df_facturas[df_facturas[col_oc_facturas].astype(str) == n_orden_teso]
            
            facturas_pendientes = []
            for _, fac in facturas_orden.iterrows():
                n_fac = str(fac.iloc[6]) if len(fac) > 6 else ""
                
                monto_f_total = 0.0
                try:
                    monto_f_total = float(fac.iloc[8]) if len(fac) > 8 and pd.notnull(fac.iloc[8]) else 0.0
                except:
                    monto_f_total = 0.0
                
                pagada_total = False
                total_pagado_acumulado = 0.0
                
                if not df_tesoreria.empty and n_fac:
                    for _, p in df_tesoreria.iterrows():
                        try:
                            p_n_fac = str(p.iloc[6]).strip() if len(p) > 6 else ""
                            if p_n_fac == str(n_fac).strip():
                                total_pagado_acumulado += float(p.iloc[8]) if len(p) > 8 and pd.notnull(p.iloc[8]) else 0.0
                        except:
                            pass
                
                if monto_f_total > 0 and total_pagado_acumulado >= monto_f_total:
                    pagada_total = True
                
                if not pagada_total and n_fac:
                    fac_dict = fac.to_dict()
                    fac_dict["_MONTO_REAL"] = monto_f_total
                    fac_dict["_N_FAC_REAL"] = n_fac
                    facturas_pendientes.append(fac_dict)
            
            if not facturas_pendientes:
                st.success("✅ ¡Todas las facturas asociadas a esta Orden de Compra ya han sido pagadas en su totalidad!")
            else:
                lista_n_facturas = [str(f.get("_N_FAC_REAL", "")) for f in facturas_pendientes]
                n_factura_seleccionada = st.selectbox("Seleccione el N° de Factura a pagar:", [""] + lista_n_facturas)
                
                if n_factura_seleccionada and n_factura_seleccionada != "":
                    datos_factura = next(f for f in facturas_pendientes if str(f.get("_N_FAC_REAL", "")) == n_factura_seleccionada)
                    
                    monto_fac_val = datos_factura.get("_MONTO_REAL", 0.0)
                    
                    monto_pagado_previo = 0.0
                    if not df_tesoreria.empty:
                        for _, p in df_tesoreria.iterrows():
                            try:
                                p_n_fac = str(p.iloc[6]).strip() if len(p) > 6 else ""
                                if p_n_fac == str(n_factura_seleccionada).strip():
                                    monto_pagado_previo += float(p.iloc[8]) if len(p) > 8 and pd.notnull(p.iloc[8]) else 0.0
                            except:
                                pass
                    
                    monto_restante = monto_fac_val - monto_pagado_previo
                    if monto_restante < 0:
                        monto_restante = 0.0
                    
                    proveedor_nombre = ""
                    for col_key in datos_factura.keys():
                        if "PROVEEDOR" in str(col_key).upper() and "N" not in str(col_key).upper():
                            proveedor_nombre = str(datos_factura.get(col_key, ""))
                            break
                    if not proveedor_nombre and len(datos_factura) > 3:
                        proveedor_nombre = str(list(datos_factura.values())[3])
                    
                    st.info(f"**Proveedor:** {proveedor_nombre} | **Monto Total Factura:** {formatear_moneda(monto_fac_val)}")
                    if monto_pagado_previo > 0:
                        st.warning(f"⚠️ Esta factura ya tiene pagos parciales registrados por un total de **{formatear_moneda(monto_pagado_previo)}**.")
                    
                    st.markdown(f"### 💵 El monto a pagar de esta Factura es: **{formatear_moneda(monto_restante)}**")
                    
                    with st.form("form_tesoreria", clear_on_submit=True):
                        st.subheader("Completar datos de Pago")
                        
                        fecha_pago = st.date_input("Fecha de Pago")
                        fecha_pago_str = fecha_pago.strftime("%d/%m/%Y")
                        
                        n_orden_pago = st.text_input("N° Orden de Pago")
                        medio_pago = st.selectbox("Medio de Pago", ["Transferencia", "Cheque", "Efectivo"])
                        banco_pago = st.text_input("Banco")
                        
                        fecha_debito_cheque = st.date_input("Fecha Débito / Cheque")
                        fecha_debito_cheque_str = fecha_debito_cheque.strftime("%d/%m/%Y")
                        
                        tipo_pago = st.selectbox("Tipo de Pago", ["Pago Parcial", "Pago Total"])
                        monto_a_pagar = st.number_input("Monto de este Pago", min_value=0.0, max_value=float(monto_restante), value=float(monto_restante), format="%.2f")
                        
                        submit_teso = st.form_submit_button("Guardar Datos de Tesorería")
                        if submit_teso:
                            val_list = list(datos_factura.values())
                            c_orden = str(val_list[0]) if len(val_list) > 0 else ""
                            c_fecha = str(val_list[1]) if len(val_list) > 1 else ""
                            c_n_prov = str(val_list[2]) if len(val_list) > 2 else ""
                            c_prov = str(proveedor_nombre)
                            
                            c_monto_oc = 0.0
                            try:
                                c_monto_oc = float(val_list[4]) if len(val_list) > 4 and pd.notnull(val_list[4]) else 0.0
                            except:
                                pass
                                
                            c_estado = str(val_list[5]) if len(val_list) > 5 else ""
                            c_n_fac = str(n_factura_seleccionada)
                            c_f_comp = str(val_list[7]) if len(val_list) > 7 else ""
                            c_m_fac = float(monto_fac_val) 
                            c_f_venc = str(val_list[9]) if len(val_list) > 9 else ""
                            
                            valores_teso = [
                                c_orden, c_fecha, c_n_prov, c_prov, c_monto_oc, c_estado,
                                c_n_fac, c_f_comp, c_m_fac, c_f_venc,
                                fecha_pago_str, str(n_orden_pago), str(medio_pago), str(banco_pago), fecha_debito_cheque_str
                            ]
                            
                            guardar_fila("TESORERIA", valores_teso)
                            st.success("¡Datos de tesorería guardados encadenadamente de forma exitosa!")
                            st.rerun()

# ==========================================
# 4. SECCIÓN REPORTES
# ==========================================
elif menu == "Reportes":
    st.header("📈 Módulo de Reportes Financieros")
    
    tipo_reporte = st.selectbox("Seleccione el Reporte a Consultar:", [
        "SÍNTESIS FINANCIERA GENERAL",
        "Facturas Ordenadas por Proveedor", 
        "Facturas Ordenadas por Fecha de Vencimiento", 
        "Pagos con Cheque por Fecha Débito", 
        "Órdenes de Compra Pendientes de Factura",
        "Consolidado: Compras Pendientes por Mes",
        "Consolidado: Saldo de Órdenes Parciales",
        "Consolidado: Facturas No Pagadas (Sin Tesorería)",
        "Consolidado: Pagos con Cheques a la Fecha",
        "Consolidado: Facturas con Pago Parcial Pendiente"
    ])
    
    st.markdown("---")
    st.markdown("### Municipalidad de Sunchales - Seguimiento Financiero")
    st.markdown(f"#### Reporte: {tipo_reporte}")
    
    df_compras = obtener_datos("COMPRAS")
    df_facturas = obtener_datos("FACTURAS")
    df_tesoreria = obtener_datos("TESORERIA")
    
    # Selector unificado de modo para TODOS los reportes
    st.markdown("### 🗂️ Criterio de Período y Acumulado")
    sub_menu_sintesis = st.radio("Modo de Visualización:", [
        "1. Acumulado Total (Anual/Histórico Global)", 
        "2. Acumulado al Mes Seleccionado", 
        "3. Flujo de Caja (Sólo lo del Mes Seleccionado)"
    ], horizontal=True)
    
    anio_sel = 2026
    mes_num_sel = 1
    mes_nombre_sel = "Enero"
    
    if "2." in sub_menu_sintesis or "3." in sub_menu_sintesis:
        col_anio, col_mes = st.columns(2)
        anos_disponibles = [2025, 2026, 2027, 2028]
        anio_sel = col_anio.selectbox("Seleccione el Año:", anos_disponibles, index=1)
        
        meses_dict = {
            "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
            "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
        }
        mes_nombre_sel = col_mes.selectbox("Seleccione el Mes:", list(meses_dict.keys()))
        mes_num_sel = meses_dict[mes_nombre_sel]

    st.markdown("---")

    def es_fecha_valida(val_fecha):
        try:
            if val_fecha is None or str(val_fecha).strip() in ["", "nan", "NaT", "None"]:
                return False, None
            dt = pd.to_datetime(val_fecha, errors='coerce')
            if pd.isnull(dt):
                return False, None
            return True, dt
        except:
            return False, None

    # Lógica general para filtrar DataFrames según el submenú seleccionado
    def cumple_criterio_fecha(val_fecha):
        if "1." in sub_menu_sintesis:
            return True
        val, dt = es_fecha_valida(val_fecha)
        if not val or dt is None:
            return False
        
        if mes_num_sel == 12:
            fecha_limite = datetime(anio_sel + 1, 1, 1)
        else:
            fecha_limite = datetime(anio_sel, mes_num_sel + 1, 1)

        if "2." in sub_menu_sintesis:
            # Acumulado hasta el fin del mes seleccionado
            return dt < fecha_limite
        else:
            # Estrictamente del mes seleccionado
            return dt.year == anio_sel and dt.month == mes_num_sel

    df_rep = pd.DataFrame()
    total_general_num = 0.0

    if tipo_reporte == "SÍNTESIS FINANCIERA GENERAL":
        if "1." in sub_menu_sintesis:
            monto_comp_pend = 0.0
            if not df_compras.empty:
                col_oc_c = df_compras.columns[0]
                col_m_c = df_compras.columns[4]
                facturadas_set = set(df_facturas.iloc[:, 0].astype(str).str.strip()) if not df_facturas.empty else set()
                df_cp = df_compras[(df_compras["PROVEEDOR"].astype(str) != "ANULADO") & (~df_compras[col_oc_c].astype(str).str.strip().isin(facturadas_set))]
                monto_comp_pend = pd.to_numeric(df_cp[col_m_c], errors='coerce').fillna(0.0).sum()
                
            saldo_op_total = 0.0
            if not df_compras.empty and not df_facturas.empty:
                for _, c_row in df_compras.iterrows():
                    if str(c_row.get("PROVEEDOR")) == "ANULADO":
                        continue
                    n_oc = str(c_row.iloc[0]).strip()
                    m_oc = float(c_row.iloc[4] or 0.0)
                    facs_match = df_facturas[df_facturas.iloc[:, 0].astype(str).str.strip() == n_oc]
                    t_fac = sum([float(x or 0.0) for x in facs_match.iloc[:, 8]]) if not facs_match.empty else 0.0
                    s_pend = m_oc - t_fac
                    if t_fac > 0 and s_pend > 0:
                        saldo_op_total += s_pend
                        
            facturas_no_pagadas_monto = 0.0
            if not df_facturas.empty:
                pagadas_set = set(df_tesoreria.iloc[:, 6].astype(str).str.strip()) if not df_tesoreria.empty else set()
                df_f_np = df_facturas[~df_facturas.iloc[:, 6].astype(str).str.strip().isin(pagadas_set)]
                facturas_no_pagadas_monto = pd.to_numeric(df_f_np.iloc[:, 8], errors='coerce').fillna(0.0).sum()
                
            parciales_pend_monto = 0.0
            if not df_facturas.empty:
                for _, f_row in df_facturas.iterrows():
                    n_f = str(f_row.iloc[6]).strip()
                    m_f = float(f_row.iloc[8] or 0.0)
                    t_pag = 0.0
                    if not df_tesoreria.empty:
                        pagos_f = df_tesoreria[df_tesoreria.iloc[:, 6].astype(str).str.strip() == n_f]
                        t_pag = sum([float(p.iloc[8] or 0.0) for _, p in pagos_f.iterrows()])
                    if 0 < t_pag < m_f:
                        parciales_pend_monto += (m_f - t_pag)
                        
            cheques_monto = 0.0
            if not df_tesoreria.empty:
                col_med = df_tesoreria.columns[12] if len(df_tesoreria.columns) > 12 else None
                if col_med:
                    df_ch = df_tesoreria[df_tesoreria.iloc[:, 12].astype(str).str.strip().str.lower() == "cheque"]
                    cheques_monto = pd.to_numeric(df_ch.iloc[:, 8], errors='coerce').fillna(0.0).sum()
                    
            df_rep = pd.DataFrame([
                {"Concepto": "Monto de Compras Pendientes (Sin Factura)", "Importe": formatear_moneda(monto_comp_pend)},
                {"Concepto": "Saldo Pendiente de Órdenes Parciales", "Importe": formatear_moneda(saldo_op_total)},
                {"Concepto": "Facturas No Pagadas (Sin Registro en Tesorería)", "Importe": formatear_moneda(facturas_no_pagadas_monto)},
                {"Concepto": "Saldo Pendiente de Facturas con Pago Parcial", "Importe": formatear_moneda(parciales_pend_monto)},
                {"Concepto": "Total de Cheques Emitidos a Debitar", "Importe": formatear_moneda(cheques_monto)}
            ])
            total_general_num = monto_comp_pend + saldo_op_total + facturas_no_pagadas_monto + parciales_pend_monto + cheques_monto

        elif "2." in sub_menu_sintesis:
            if mes_num_sel == 12:
                fecha_limite = datetime(anio_sel + 1, 1, 1)
            else:
                fecha_limite = datetime(anio_sel, mes_num_sel + 1, 1)
            hoy = datetime.now()

            monto_comp_pend_mes = 0.0
            if not df_compras.empty:
                col_oc_c = df_compras.columns[0]
                col_f_c = df_compras.columns[1]
                col_m_c = df_compras.columns[4]
                facturadas_set = set(df_facturas.iloc[:, 0].astype(str).str.strip()) if not df_facturas.empty else set()
                df_cp = df_compras[(df_compras["PROVEEDOR"].astype(str) != "ANULADO") & (~df_compras[col_oc_c].astype(str).str.strip().isin(facturadas_set))].copy()
                if not df_cp.empty and col_f_c:
                    for _, row in df_cp.iterrows():
                        val, dt = es_fecha_valida(row.get(col_f_c))
                        if val and dt is not None and dt < fecha_limite:
                            monto_comp_pend_mes += float(row.get(col_m_c, 0.0) or 0.0)

            saldo_op_mes = 0.0
            if not df_compras.empty and not df_facturas.empty:
                for _, c_row in df_compras.iterrows():
                    if str(c_row.get("PROVEEDOR")) == "ANULADO":
                        continue
                    val, dt = es_fecha_valida(c_row.iloc[1])
                    if val and dt is not None and dt < fecha_limite:
                        n_oc = str(c_row.iloc[0]).strip()
                        m_oc = float(c_row.iloc[4] or 0.0)
                        facs_match = df_facturas[df_facturas.iloc[:, 0].astype(str).str.strip() == n_oc]
                        t_fac = sum([float(x or 0.0) for x in facs_match.iloc[:, 8]]) if not facs_match.empty else 0.0
                        s_pend = m_oc - t_fac
                        if t_fac > 0 and s_pend > 0:
                            saldo_op_mes += s_pend

            facturas_vencidas_monto = 0.0
            facturas_a_vencer_monto = 0.0
            if not df_facturas.empty:
                pagadas_set = set(df_tesoreria.iloc[:, 6].astype(str).str.strip()) if not df_tesoreria.empty else set()
                df_f_np = df_facturas[~df_facturas.iloc[:, 6].astype(str).str.strip().isin(pagadas_set)].copy()
                col_venc = df_facturas.columns[9] if len(df_facturas.columns) > 9 else None
                col_m_fac = df_facturas.columns[8] if len(df_facturas.columns) > 8 else None
                if not df_f_np.empty and col_venc and col_m_fac:
                    for _, frow in df_f_np.iterrows():
                        val, dt_v = es_fecha_valida(frow.get(col_venc))
                        if val and dt_v is not None and dt_v < fecha_limite:
                            monto_f = float(frow.get(col_m_fac, 0.0) or 0.0)
                            if dt_v < hoy:
                                facturas_vencidas_monto += monto_f
                            else:
                                facturas_a_vencer_monto += monto_f

            parciales_pend_mes = 0.0
            if not df_facturas.empty:
                for _, f_row in df_facturas.iterrows():
                    val, dt_v = es_fecha_valida(f_row.iloc[9] if len(f_row) > 9 else None)
                    if val and dt_v is not None and dt_v < fecha_limite:
                        n_f = str(f_row.iloc[6]).strip()
                        m_f = float(f_row.iloc[8] or 0.0)
                        t_pag = 0.0
                        if not df_tesoreria.empty:
                            pagos_f = df_tesoreria[df_tesoreria.iloc[:, 6].astype(str).str.strip() == n_f]
                            t_pag = sum([float(p.iloc[8] or 0.0) for _, p in pagos_f.iterrows()])
                        if 0 < t_pag < m_f:
                            parciales_pend_mes += (m_f - t_pag)

            df_rep = pd.DataFrame([
                {"Concepto Acumulado": "Monto de Órdenes de Compra Sin Factura", "Importe": formatear_moneda(monto_comp_pend_mes)},
                {"Concepto Acumulado": "Saldo de Órdenes de Compra Parciales", "Importe": formatear_moneda(saldo_op_mes)},
                {"Concepto Acumulado": "Facturas No Pagadas Vencidas", "Importe": formatear_moneda(facturas_vencidas_monto)},
                {"Concepto Acumulado": "Facturas No Pagadas a Vencer", "Importe": formatear_moneda(facturas_a_vencer_monto)},
                {"Concepto Acumulado": "Saldo Pendiente de Facturas con Pago Parcial", "Importe": formatear_moneda(parciales_pend_mes)}
            ])
            total_general_num = monto_comp_pend_mes + saldo_op_mes + facturas_vencidas_monto + facturas_a_vencer_monto + parciales_pend_mes

        else:
            facturas_vencidas_mes = 0.0
            cheques_debito_mes = 0.0
            if not df_facturas.empty:
                pagadas_set = set(df_tesoreria.iloc[:, 6].astype(str).str.strip()) if not df_tesoreria.empty else set()
                df_f_np = df_facturas[~df_facturas.iloc[:, 6].astype(str).str.strip().isin(pagadas_set)].copy()
                col_venc = df_facturas.columns[9] if len(df_facturas.columns) > 9 else None
                col_m_fac = df_facturas.columns[8] if len(df_facturas.columns) > 8 else None
                if not df_f_np.empty and col_venc and col_m_fac:
                    for _, frow in df_f_np.iterrows():
                        val, dt_v = es_fecha_valida(frow.get(col_venc))
                        if val and dt_v is not None and dt_v.year == anio_sel and dt_v.month == mes_num_sel:
                            facturas_vencidas_mes += float(frow.get(col_m_fac, 0.0) or 0.0)

            if not df_tesoreria.empty:
                col_medio = df_tesoreria.columns[12] if len(df_tesoreria.columns) > 12 else None
                col_f_deb = df_tesoreria.columns[14] if len(df_tesoreria.columns) > 14 else None
                col_m_pago = df_tesoreria.columns[8] if len(df_tesoreria.columns) > 8 else None
                if col_medio and col_f_deb and col_m_pago:
                    df_ch = df_tesoreria[df_tesoreria[col_medio].astype(str).str.strip().str.lower() == "cheque"].copy()
                    for _, crow in df_ch.iterrows():
                        val, dt_d = es_fecha_valida(crow.get(col_f_deb))
                        if val and dt_d is not None and dt_d.year == anio_sel and dt_d.month == mes_num_sel:
                            cheques_debito_mes += float(crow.get(col_m_pago, 0.0) or 0.0)

            df_rep = pd.DataFrame([
                {"Concepto del Mes": "Facturas con Vencimiento en el Mes", "Importe": formatear_moneda(facturas_vencidas_mes)},
                {"Concepto del Mes": "Cheques con Fecha de Débito en el Mes", "Importe": formatear_moneda(cheques_debito_mes)}
            ])
            total_general_num = facturas_vencidas_mes + cheques_debito_mes

    elif tipo_reporte == "Facturas Ordenadas por Proveedor":
        if not df_facturas.empty:
            col_prov = next((c for c in df_facturas.columns if "PROVEEDOR" in c.upper() and "N" not in c.upper()), df_facturas.columns[3] if len(df_facturas.columns) > 3 else None)
            col_monto = next((c for c in df_facturas.columns if "MONTO FACTURA" in c.upper() or "MONTO COMP" in c.upper()), df_facturas.columns[8] if len(df_facturas.columns) > 8 else None)
            col_venc = next((c for c in df_facturas.columns if "VENCIMIENTO" in c.upper()), df_facturas.columns[9] if len(df_facturas.columns) > 9 else None)
            
            if col_prov and col_monto:
                df_temp = df_facturas.copy()
                if col_venc and "1." not in sub_menu_sintesis:
                    df_temp = df_temp[df_temp[col_venc].apply(cumple_criterio_fecha)]
                
                df_temp[col_monto] = pd.to_numeric(df_temp[col_monto], errors='coerce').fillna(0.0)
                df_rep = df_temp.sort_values(by=col_prov)
                
                if col_venc:
                    df_rep[col_venc] = pd.to_datetime(df_rep[col_venc], errors='coerce').dt.strftime('%d/%m/%Y').fillna(df_rep[col_venc])

                df_rep = df_rep[[col_prov, 'N FACTURA', col_monto, col_venc]]
                total_general_num = df_rep[col_monto].sum()
                df_rep[col_monto] = df_rep[col_monto].apply(formatear_moneda)

    elif tipo_reporte == "Facturas Ordenadas por Fecha de Vencimiento":
        if not df_facturas.empty:
            col_prov = next((c for c in df_facturas.columns if "PROVEEDOR" in c.upper() and "N" not in c.upper()), df_facturas.columns[3] if len(df_facturas.columns) > 3 else None)
            col_monto = next((c for c in df_facturas.columns if "MONTO FACTURA" in c.upper() or "MONTO COMP" in c.upper()), df_facturas.columns[8] if len(df_facturas.columns) > 8 else None)
            col_venc = next((c for c in df_facturas.columns if "VENCIMIENTO" in c.upper()), df_facturas.columns[9] if len(df_facturas.columns) > 9 else None)
            
            if col_venc and col_monto:
                df_temp = df_facturas.copy()
                if "1." not in sub_menu_sintesis:
                    df_temp = df_temp[df_temp[col_venc].apply(cumple_criterio_fecha)]
                
                df_temp[col_monto] = pd.to_numeric(df_temp[col_monto], errors='coerce').fillna(0.0)
                df_temp_fecha = pd.to_datetime(df_temp[col_venc], errors='coerce')
                df_temp["_temp_sort"] = df_temp_fecha
                df_rep = df_temp.sort_values(by="_temp_sort")
                df_rep.drop(columns=["_temp_sort"], inplace=True, errors='ignore')
                
                df_rep[col_venc] = df_temp_fecha.dt.strftime('%d/%m/%Y').fillna(df_rep[col_venc])
                df_rep = df_rep[[col_venc, col_prov, 'N FACTURA', col_monto]]
                total_general_num = df_rep[col_monto].sum()
                df_rep[col_monto] = df_rep[col_monto].apply(formatear_moneda)

    elif tipo_reporte == "Pagos con Cheque por Fecha Débito":
        if not df_tesoreria.empty:
            col_medio = next((c for c in df_tesoreria.columns if "MEDIO" in c.upper()), df_tesoreria.columns[12] if len(df_tesoreria.columns) > 12 else None)
            col_banco = next((c for c in df_tesoreria.columns if "BANCO" in c.upper()), df_tesoreria.columns[13] if len(df_tesoreria.columns) > 13 else None)
            col_f_deb = next((c for c in df_tesoreria.columns if "DÉBITO" in c.upper() or "DEBITO" in c.upper() or "CHEQUE" in c.upper()), df_tesoreria.columns[14] if len(df_tesoreria.columns) > 14 else None)
            col_m_pago = df_tesoreria.columns[8] if len(df_tesoreria.columns) > 8 else None
            col_prov = next((c for c in df_tesoreria.columns if "PROVEEDOR" in c.upper() and "N" not in c.upper()), df_tesoreria.columns[3] if len(df_tesoreria.columns) > 3 else None)
            
            if col_medio:
                df_cheques = df_tesoreria[df_tesoreria[col_medio].astype(str).str.strip().str.lower() == "cheque"].copy()
                if not df_cheques.empty and col_f_deb:
                    if "1." not in sub_menu_sintesis:
                        df_cheques = df_cheques[df_cheques[col_f_deb].apply(cumple_criterio_fecha)]
                    
                    df_cheques[col_m_pago] = pd.to_numeric(df_cheques[col_m_pago], errors='coerce').fillna(0.0)
                    df_temp_fdeb = pd.to_datetime(df_cheques[col_f_deb], errors='coerce')
                    df_cheques["_temp_sort"] = df_temp_fdeb
                    df_cheques = df_cheques.sort_values(by="_temp_sort")
                    df_cheques.drop(columns=["_temp_sort"], inplace=True, errors='ignore')
                    
                    df_cheques[col_f_deb] = df_temp_fdeb.dt.strftime('%d/%m/%Y').fillna(df_cheques[col_f_deb])
                    columnas_mostrar = [c for c in [col_f_deb, col_prov, col_m_pago, col_banco, 'N FACTURA'] if c in df_cheques.columns]
                    df_rep = df_cheques[columnas_mostrar].copy()
                    total_general_num = df_cheques[col_m_pago].sum() if col_m_pago else 0.0
                    df_rep[col_m_pago] = df_rep[col_m_pago].apply(formatear_moneda)

    elif tipo_reporte == "Órdenes de Compra Pendientes de Factura":
        if not df_compras.empty:
            col_oc_compra = next((c for c in df_compras.columns if "ORDEN" in c.upper()), df_compras.columns[0])
            col_monto_oc = next((c for c in df_compras.columns if c.upper() == "MONTO"), df_compras.columns[4] if len(df_compras.columns) > 4 else None)
            col_fecha_c = next((c for c in df_compras.columns if "FECHA" in c.upper()), df_compras.columns[1] if len(df_compras.columns) > 1 else None)
            
            facturadas = set()
            if not df_facturas.empty:
                col_oc_fac = next((c for c in df_facturas.columns if "ORDEN" in c.upper()), df_facturas.columns[0])
                facturadas = set(df_facturas[col_oc_fac].astype(str).str.strip())
            
            df_validas = df_compras[df_compras["PROVEEDOR"].astype(str) != "ANULADO"].copy()
            df_pendientes = df_validas[~df_validas[col_oc_compra].astype(str).str.strip().isin(facturadas)].copy()
            
            if not df_pendientes.empty and col_fecha_c:
                if "1." not in sub_menu_sintesis:
                    df_pendientes = df_pendientes[df_pendientes[col_fecha_c].apply(cumple_criterio_fecha)]
                
                df_pendientes[col_monto_oc] = pd.to_numeric(df_pendientes[col_monto_oc], errors='coerce').fillna(0.0)
                df_pendientes[col_fecha_c] = pd.to_datetime(df_pendientes[col_fecha_c], errors='coerce').dt.strftime('%d/%m/%Y').fillna(df_pendientes[col_fecha_c])
                df_rep = df_pendientes.copy()
                total_general_num = df_pendientes[col_monto_oc].sum() if col_monto_oc else 0.0
                df_rep[col_monto_oc] = df_rep[col_monto_oc].apply(formatear_moneda)

    elif tipo_reporte == "Consolidado: Compras Pendientes por Mes":
        if not df_compras.empty:
            col_oc_compra = next((c for c in df_compras.columns if "ORDEN" in c.upper()), df_compras.columns[0])
            col_fecha = next((c for c in df_compras.columns if "FECHA" in c.upper()), df_compras.columns[1] if len(df_compras.columns) > 1 else None)
            col_monto_oc = next((c for c in df_compras.columns if c.upper() == "MONTO"), df_compras.columns[4] if len(df_compras.columns) > 4 else None)
            
            facturadas = set()
            if not df_facturas.empty:
                col_oc_fac = next((c for c in df_facturas.columns if "ORDEN" in c.upper()), df_facturas.columns[0])
                facturadas = set(df_facturas[col_oc_fac].astype(str).str.strip())
            
            df_validas = df_compras[df_compras["PROVEEDOR"].astype(str) != "ANULADO"].copy()
            df_pendientes = df_validas[~df_validas[col_oc_compra].astype(str).str.strip().isin(facturadas)].copy()
            
            if not df_pendientes.empty and col_fecha and col_monto_oc:
                if "1." not in sub_menu_sintesis:
                    df_pendientes = df_pendientes[df_pendientes[col_fecha].apply(cumple_criterio_fecha)]
                
                df_pendientes[col_monto_oc] = pd.to_numeric(df_pendientes[col_monto_oc], errors='coerce').fillna(0.0)
                df_pendientes["MES"] = pd.to_datetime(df_pendientes[col_fecha], errors='coerce').dt.to_period('M').astype(str)
                df_rep = df_pendientes.groupby("MES")[col_monto_oc].sum().reset_index()
                df_rep.columns = ["Mes", "Monto Pendiente de Factura"]
                total_general_num = df_rep["Monto Pendiente de Factura"].sum()
                df_rep["Monto Pendiente de Factura"] = df_rep["Monto Pendiente de Factura"].apply(formatear_moneda)

    elif tipo_reporte == "Consolidado: Saldo de Órdenes Parciales":
        if not df_compras.empty and not df_facturas.empty:
            col_oc_compra = df_compras.columns[0]
            col_monto_oc = df_compras.columns[4]
            col_oc_fac = df_facturas.columns[0]
            col_fecha_c = df_compras.columns[1]
            
            datos_parciales = []
            for _, compra in df_compras.iterrows():
                if str(compra.get("PROVEEDOR")) == "ANULADO":
                    continue
                if "1." not in sub_menu_sintesis and not cumple_criterio_fecha(compra.get(col_fecha_c)):
                    continue
                
                n_oc = str(compra.get(col_oc_compra)).strip()
                monto_total_oc = float(compra.get(col_monto_oc, 0.0) or 0.0)
                
                facs_asociadas = df_facturas[df_facturas[col_oc_fac].astype(str).str.strip() == n_oc]
                total_facturado = 0.0
                for _, f_row in facs_asociadas.iterrows():
                    try:
                        total_facturado += float(f_row.iloc[8] or 0.0)
                    except:
                        pass
                
                saldo_pendiente = monto_total_oc - total_facturado
                if saldo_pendiente < 0:
                    saldo_pendiente = 0.0
                
                if total_facturado > 0 and saldo_pendiente > 0:
                    datos_parciales.append({
                        "N° Orden": n_oc,
                        "Proveedor": compra.get("PROVEEDOR"),
                        "Monto Total OC": monto_total_oc,
                        "Total Facturado": total_facturado,
                        "Saldo Disponible": saldo_pendiente
                    })
            
            if datos_parciales:
                df_rep = pd.DataFrame(datos_parciales)
                total_general_num = df_rep["Saldo Disponible"].sum()
                df_rep["Monto Total OC"] = df_rep["Monto Total OC"].apply(formatear_moneda)
                df_rep["Total Facturado"] = df_rep["Total Facturado"].apply(formatear_moneda)
                df_rep["Saldo Disponible"] = df_rep["Saldo Disponible"].apply(formatear_moneda)

    elif tipo_reporte == "Consolidado: Facturas No Pagadas (Sin Tesorería)":
        if not df_facturas.empty:
            col_m_fac = df_facturas.columns[8]
            col_venc = next((c for c in df_facturas.columns if "VENCIMIENTO" in c.upper()), df_facturas.columns[9] if len(df_facturas.columns) > 9 else None)
            
            facturas_pagadas = set()
            if not df_tesoreria.empty:
                facturas_pagadas = set(df_tesoreria.iloc[:, 6].astype(str).str.strip())
            
            df_temp = df_facturas[~df_facturas.iloc[:, 6].astype(str).str.strip().isin(facturas_pagadas)].copy()
            if not df_temp.empty and col_venc:
                if "1." not in sub_menu_sintesis:
                    df_temp = df_temp[df_temp[col_venc].apply(cumple_criterio_fecha)]
                
                df_temp[col_m_fac] = pd.to_numeric(df_temp[col_m_fac], errors='coerce').fillna(0.0)
                df_temp[col_venc] = pd.to_datetime(df_temp[col_venc], errors='coerce').dt.strftime('%d/%m/%Y').fillna(df_temp[col_venc])
                df_rep = df_temp.copy()
                total_general_num = df_rep[col_m_fac].sum()
                df_rep[col_m_fac] = df_rep[col_m_fac].apply(formatear_moneda)

    elif tipo_reporte == "Consolidado: Pagos con Cheques a la Fecha":
        if not df_tesoreria.empty:
            col_medio = df_tesoreria.columns[12] if len(df_tesoreria.columns) > 12 else None
            col_f_deb = df_tesoreria.columns[14] if len(df_tesoreria.columns) > 14 else None
            col_monto_pago = df_tesoreria.columns[8] if len(df_tesoreria.columns) > 8 else None
            
            if col_medio:
                df_cheques = df_tesoreria[df_tesoreria[col_medio].astype(str).str.strip().str.lower() == "cheque"].copy()
                if not df_cheques.empty and col_f_deb:
                    if "1." not in sub_menu_sintesis:
                        df_cheques = df_cheques[df_cheques[col_f_deb].apply(cumple_criterio_fecha)]
                    
                    df_cheques[col_monto_pago] = pd.to_numeric(df_cheques[col_monto_pago], errors='coerce').fillna(0.0)
                    df_cheques[col_f_deb] = pd.to_datetime(df_cheques[col_f_deb], errors='coerce').dt.strftime('%d/%m/%Y').fillna(df_cheques[col_f_deb])
                    df_rep = df_cheques.copy()
                    total_general_num = df_cheques[col_monto_pago].sum()
                    df_rep[col_monto_pago] = df_rep[col_monto_pago].apply(formatear_moneda)

    elif tipo_reporte == "Consolidado: Facturas con Pago Parcial Pendiente":
        if not df_facturas.empty:
            col_venc = df_facturas.columns[9] if len(df_facturas.columns) > 9 else None
            datos_parciales_teso = []
            for _, fac in df_facturas.iterrows():
                if "1." not in sub_menu_sintesis and col_venc and not cumple_criterio_fecha(fac.get(col_venc)):
                    continue
                
                n_fac = str(fac.iloc[6]).strip()
                monto_fac = float(fac.iloc[8] or 0.0)
                
                total_pagado = 0.0
                if not df_tesoreria.empty:
                    pagos = df_tesoreria[df_tesoreria.iloc[:, 6].astype(str).str.strip() == n_fac]
                    for _, p in pagos.iterrows():
                        try:
                            total_pagado += float(p.iloc[8] or 0.0)
                        except:
                            pass
                
                saldo_restante = monto_fac - total_pagado
                if 0 < total_pagado < monto_fac:
                    datos_parciales_teso.append({
                        "N° Factura": n_fac,
                        "Proveedor": fac.get("PROVEEDOR"),
                        "Monto Factura": monto_fac,
                        "Total Pagado": total_pagado,
                        "Saldo Pendiente Pago": saldo_restante
                    })
            
            if datos_parciales_teso:
                df_rep = pd.DataFrame(datos_parciales_teso)
                total_general_num = df_rep["Saldo Pendiente Pago"].sum()
                df_rep["Monto Factura"] = df_rep["Monto Factura"].apply(formatear_moneda)
                df_rep["Total Pagado"] = df_rep["Total Pagado"].apply(formatear_moneda)
                df_rep["Saldo Pendiente Pago"] = df_rep["Saldo Pendiente Pago"].apply(formatear_moneda)

    # Renderizado final del DataFrame, Totales y Botones de Exportación / Impresión
    if not df_rep.empty:
        st.markdown(f"### 📊 Reporte: {tipo_reporte} ({sub_menu_sintesis})")
        st.dataframe(df_rep, use_container_width=True)
        st.markdown(f"### **Total General:** {formatear_moneda(total_general_num)}")
        
        csv = df_rep.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Reporte en Excel (CSV)", csv, "reporte_financiero.csv", "text/csv")
        
        html_content = f"""
        <html>
        <head>
            <title>Municipalidad de Sunchales - Reporte</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h2, h3, h4 {{ text-align: center; color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }}
                th {{ background-color: #f2f2f2; }}
                td:nth-child(n+3), th:nth-child(n+3) {{ text-align: right; }}
                .total {{ margin-top: 20px; font-size: 16px; font-weight: bold; text-align: right; }}
            </style>
        </head>
        <body>
            <h2>Municipalidad de Sunchales</h2>
            <h3>Seguimiento Financiero - {tipo_reporte}</h3>
            <h4>{sub_menu_sintesis}</h4>
            {df_rep.to_html(index=False, classes='table')}
            <div class="total">Total General: {formatear_moneda(total_general_num)}</div>
            <script>window.print();</script>
        </body>
        </html>
        """
        
        st.markdown("---")
        if st.button("🖨️ Imprimir / Guardar como PDF"):
            st.components.v1.html(html_content, height=600)
    else:
        st.info("No hay datos disponibles para este reporte con los criterios seleccionados.")
        
