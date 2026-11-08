import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Seguimiento Cierre Anual", layout="wide")

st.title("📊 Panel de Compras y Pagos")

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
            
            monto_compra_fmt = f"${monto_compra_total:,.2f}"
            col2.write(f"**Monto Compra:** {monto_compra_fmt}")
            
            col3.write(f"**Estado Actual:** {estado_actual_fac}")
            
            if total_facturado_previo > 0:
                st.warning(f"⚠️ Ya se facturó un total de **${total_facturado_previo:,.2f}** para esta orden.")
            
            st.markdown(f"### 💵 Monto disponible para facturar: **${monto_disponible:,.2f}**")
            
            with st.form("form_facturas", clear_on_submit=True):
                st.subheader("Completar datos de Facturación y Estado")
                n_factura = st.text_input("N° de Factura")
                fecha_comprobante = st.date_input("Fecha de Comprobante")
                monto_factura = st.number_input("Monto Factura", min_value=0.0, max_value=float(monto_disponible) if monto_disponible > 0 else 0.0, value=min(100.0, monto_disponible) if monto_disponible > 0 else 0.0, format="%.2f")
                fecha_vencimiento = st.date_input("Fecha de Vencimiento")
                
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
                        str(fecha_comprobante),   
                        float(monto_factura),     
                        str(fecha_vencimiento)    
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
                    
                    st.info(f"**Proveedor:** {proveedor_nombre} | **Monto Total Factura:** ${monto_fac_val:,.2f}")
                    if monto_pagado_previo > 0:
                        st.warning(f"⚠️ Esta factura ya tiene pagos parciales registrados por un total de **${monto_pagado_previo:,.2f}**.")
                    
                    st.markdown(f"### 💵 El monto a pagar de esta Factura es: **${monto_restante:,.2f}**")
                    
                    with st.form("form_tesoreria", clear_on_submit=True):
                        st.subheader("Completar datos de Pago")
                        fecha_pago = st.date_input("Fecha de Pago")
                        n_orden_pago = st.text_input("N° Orden de Pago")
                        medio_pago = st.selectbox("Medio de Pago", ["Transferencia", "Cheque", "Efectivo"])
                        banco_pago = st.text_input("Banco")
                        fecha_debito_cheque = st.date_input("Fecha Débito / Cheque")
                        
                        tipo_pago = st.selectbox("Tipo de Pago", ["Pago Parcial", "Pago Total"])
                        monto_a_pagar = st.number_input("Monto de este Pago", min_value=0.0, max_value=float(monto_restante), value=float(monto_restante), format="%.2f")
                        
                        submit_teso = st.form_submit_button("Guardar Datos de Tesorería")
                        if submit_submit := submit_teso:
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
                                str(fecha_pago), str(n_orden_pago), str(medio_pago), str(banco_pago), str(fecha_debito_cheque)
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
        "REPORTE OC",
        "REPORTE FACTURAS",
        "REPORTE COMPROBANTES POR VENCIMIENTO",
        "TESORERÍA - PAGOS (Cheque, Banco y Fecha)",
        "TESORERÍA - Pagos Ordenados y Acumulados por Mes de Débito"
    ])
    
    st.markdown("---")
    st.markdown("### Municipalidad de Sunchales - Seguimiento Financiero")
    st.markdown(f"#### Reporte: {tipo_reporte}")
    
    if tipo_reporte == "TESORERÍA - PAGOS (Cheque, Banco y Fecha)":
        df_raw = obtener_datos("TESORERIA")
        if not df_raw.empty:
            cols_deseadas = []
            for c in df_raw.columns:
                c_up = str(c).upper()
                if any(x in c_up for x in ["PROVEEDOR", "PAGADO", "MONTO", "MEDIO", "BANCO", "DÉBITO", "DEBITO", "CHEQUE", "FACTURA", "ORDEN"]):
                    cols_deseadas.append(c)
            df_rep = df_raw[cols_deseadas].copy() if cols_deseadas else df_raw.copy()
        else:
            df_rep = pd.DataFrame()
            
    elif tipo_reporte == "TESORERÍA - Pagos Ordenados y Acumulados por Mes de Débito":
        df_raw = obtener_datos("TESORERIA")
        if not df_raw.empty:
            col_monto = next((c for c in df_raw.columns if any(k in str(c).upper() for k in ["PAGADO", "MONTO"])), df_raw.columns[8] if len(df_raw.columns) > 8 else None)
            col_fdeb = next((c for c in df_raw.columns if any(k in str(c).upper() for k in ["DÉBITO", "DEBITO", "CHEQUE"])), df_raw.columns[14] if len(df_raw.columns) > 14 else None)
            
            if col_monto and col_fdeb:
                df_temp = df_raw.copy()
                primera_c = df_temp.columns[0]
                df_temp = df_temp[
                    df_temp[primera_c].notna() & 
                    (df_temp[primera_c].astype(str).str.strip() != "") & 
                    (df_temp[primera_c].astype(str).str.strip() != "0") & 
                    (df_temp[primera_c].astype(str).str.lower() != "nan")
                ].copy()
                
                df_temp["_MONTO_NUM"] = pd.to_numeric(df_temp[col_monto], errors='coerce').fillna(0.0)
                df_temp["_DT"] = pd.to_datetime(df_temp[col_fdeb], errors='coerce')
                df_temp["MES_DEBITO"] = df_temp["_DT"].dt.to_period('M').astype(str)
                df_temp = df_temp[df_temp["MES_DEBITO"] != "NaT"].copy()
                
                df_rep = df_temp.groupby("MES_DEBITO")["_MONTO_NUM"].sum().reset_index()
                df_rep.columns = ["Mes de Débito", "Total Pagado"]
                df_rep = df_rep.sort_values(by="Mes de Débito")
            else:
                df_rep = pd.DataFrame()
        else:
            df_rep = pd.DataFrame()
    else:
        df_rep = obtener_datos(tipo_reporte)
    
    if not df_rep.empty and tipo_reporte != "TESORERÍA - Pagos Ordenados y Acumulados por Mes de Débito":
        primera_col = df_rep.columns[0]
        df_rep = df_rep[
            df_rep[primera_col].notna() & 
            (df_rep[primera_col].astype(str).str.strip() != "") & 
            (df_rep[primera_col].astype(str).str.strip() != "0") & 
            (df_rep[primera_col].astype(str).str.lower() != "nan")
        ].copy()
        
        for col in df_rep.columns:
            col_up = str(col).upper()
            if any(k in col_up for k in ["FECHA", "VENCIMIENTO", "DÉBITO", "DEBITO"]):
                df_rep[col] = pd.to_datetime(df_rep[col], errors='coerce').dt.strftime('%d/%m/%Y').fillna(df_rep[col])
        
    totales_dict = {}
    if not df_rep.empty:
        for col in df_rep.columns:
            col_up = str(col).upper()
            if any(k in col_up for k in ["MONTO", "PAGADO", "TOTAL", "IMPORTE", "SALDO"]):
                vals_num = pd.to_numeric(df_rep[col], errors='coerce').fillna(0.0)
                totales_dict[col] = vals_num.sum()
                df_rep[col] = vals_num.apply(lambda x: f"${x:,.2f}")

    if not df_rep.empty:
        # Estilo CSS inyectado para alinear a la derecha todas las celdas numéricas en la interfaz de Streamlit
        st.markdown("""
            <style>
                [data-testid="stDataFrame"] td:nth-child(n+3), 
                [data-testid="stDataFrame"] th:nth-child(n+3) {
                    text-align: right !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.dataframe(df_rep, use_container_width=True)
        
        if totales_dict:
            st.markdown("### 📌 Totales del Reporte:")
            cols_totales = st.columns(len(totales_dict))
            for i, (col_nombre, val_total) in enumerate(totales_dict.items()):
                cols_totales[i].metric(label=f"Total {col_nombre}", value=f"${val_total:,.2f}")
        
        csv = df_rep.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Reporte en Excel (CSV)", csv, f"{tipo_reporte.lower().replace(' ', '_').replace('(', '').replace(')', '')}.csv", "text/csv")
        
        html_totales_tr = ""
        if totales_dict:
            html_totales_tr = "<tr style='font-weight: bold; background-color: #e9ecef;'>"
            for col in df_rep.columns:
                if col in totales_dict:
                    html_totales_tr += f"<td style='text-align: right;'>${totales_dict[col]:,.2f}</td>"
                elif col == df_rep.columns[0]:
                    html_totales_tr += "<td>TOTAL GENERAL</td>"
                else:
                    html_totales_tr += "<td></td>"
            html_totales_tr += "</tr>"

        html_content = f"""
        <html>
        <head>
            <title>Municipalidad de Sunchales - Reporte</title>
            <style>
                @page {{
                    size: landscape;
                    margin: 10mm;
                }}
                body {{ font-family: Arial, sans-serif; padding: 10px; }}
                h2, h4 {{ text-align: center; color: #333; margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #bbb; padding: 6px 8px; text-align: left; font-size: 11px; }}
                th {{ background-color: #f2f2f2; text-align: center; }}
                /* Fuerza absoluta de alineación a la derecha en la impresión para columnas contables */
                td:nth-child(n+3), th:nth-child(n+3) {{ text-align: right !important; }}
            </style>
        </head>
        <body>
            <h2>Municipalidad de Sunchales</h2>
            <h4>Seguimiento Financiero - {tipo_reporte}</h4>
            {df_rep.to_html(index=False, classes='table', escape=False).replace("</tbody>", html_totales_tr + "</tbody>")}
            <script>
                window.onload = function() {{
                    window.print();
                }};
            </script>
        </body>
        </html>
        """
        
        st.markdown("---")
        if st.button("🖨️ Imprimir / Guardar como PDF (Horizontal)"):
            st.components.v1.html(html_content, height=600)
    else:
        st.info(f"No hay datos disponibles en el reporte '{tipo_reporte}' o la hoja se encuentra vacía.")
        
