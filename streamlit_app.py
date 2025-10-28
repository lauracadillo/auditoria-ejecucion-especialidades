# === Importación de librerías necesarias === 
import streamlit as st     
import pandas as pd   


# === CONFIGURACIÓN GENERAL DE LA PÁGINA ===
st.set_page_config(page_title="Control de Mantenimientos", layout="wide")
st.title("Herramienta para la auditoria de ejecución de especialidades")

# === CONFIGURACIÓN DEL ARCHIVO ===
archivo = "libroTest.xlsx"
if archivo:
    hoja = "Hoja2"
    df = pd.read_excel(archivo, sheet_name=hoja)
    df.columns = df.columns.str.strip()

    # === DEFINICIÓN DE COLUMNAS ===
    columnaEspecialidades = "SUB_ESPECIALIDAD"
    columnaSites = "Site Id Name"
    columnaPrioridad = "Site Priority"
    columnaFLM = "Contratista Sitio"
    columnaEstado = "ESTADO"
    columnaFecha = "2_MES_PROGRA"
    columnaFLMEspecifico = "SUP_FLM_2"

    SubEspecialidadesGenerales = [
        "AA", "GE-TTA-TK", "IE", "SE-LT", "REC-BB", "TX", "TX-BH",
        "UPS", "INV-AVR", "LT", "RADIO", "SOL-EOL", "#N/D", "0"
    ]

    # === CONVERSIÓN DE FECHAS ===
    df[columnaFecha] = df[columnaFecha].astype(str).str.strip().str.lower()
    meses = {'ene':'01','feb':'02','mar':'03','abr':'04','may':'05','jun':'06',
             'jul':'07','ago':'08','set':'09','oct':'10','nov':'11','dic':'12'}

    def convertir_mes_ano(valor):
        if isinstance(valor, str) and '-' in valor:
            mes_abrev, anio = valor.split('-')
            mes = meses.get(mes_abrev.strip(), None)
            if mes:
                return f"20{anio.strip()}-{mes}"
        return "Fecha desconocida"

    df["MES"] = df[columnaFecha].apply(convertir_mes_ano)

    # === CONTEO DE SUBESPECIALIDADES POR SITE Y MES ===
    conteo = (
        df.groupby([columnaSites, "MES", columnaEspecialidades])
        .size()
        .unstack(fill_value=0)
    )

    for sub in SubEspecialidadesGenerales:
        if sub not in conteo.columns:
            conteo[sub] = 0

    conteo = conteo[SubEspecialidadesGenerales]
    conteo["TOTAL"] = conteo.sum(axis=1)
    conteo.reset_index(inplace=True)
    conteo["CAMBIO_MES_A_MES"] = conteo.groupby(columnaSites)["TOTAL"].diff().fillna(0)

    
    

    # === ESTADOS ===
    estado = (
        df.groupby([columnaSites, "MES", columnaEspecialidades, columnaEstado])
        .size()
        .unstack(fill_value=0)
    )
    if "Cancelado" in estado.columns:
        estado["Total"] = estado.sum(axis=1)
        estado["% Cancelado"] = (estado["Cancelado"] / estado["Total"]).round(2)
    else:
        estado["% Cancelado"] = 0
    estado.reset_index(inplace=True)

    # === CONTRATISTA ===
    contratista = (
        df.groupby([columnaFLM, columnaSites, "MES"])
        .size()
        .reset_index(name="Cantidad")
    )

    # === ALARMAS ===
    prioridad = df[[columnaSites, columnaPrioridad]].drop_duplicates()
    alarma = pd.merge(prioridad, conteo, on=columnaSites, how="left")

    def generar_alarma(row, prioridad):
        if row[columnaPrioridad] == prioridad and row["CAMBIO_MES_A_MES"] < 0:
            return f"⚠️ Disminución de especialidades ({row['CAMBIO_MES_A_MES']}) respecto al mes anterior"
        return ""

    # === FUNCIÓN REUTILIZABLE PARA MOSTRAR CADA TAB ===

    def mostrar_tab(nombre_tab, codigo_prioridad):
        st.subheader(f"🚨 Alarmas en sitio {nombre_tab}")
        alarma[f"ALARMA_{nombre_tab}"] = alarma.apply(
            lambda row: generar_alarma(row, codigo_prioridad), axis=1
        )

        sitios_con_baja = alarma[alarma[f"ALARMA_{nombre_tab}"] != ""][columnaSites].unique()
        for site in sitios_con_baja:
            site_data = conteo[conteo[columnaSites] == site].sort_values("MES")
            site_alertas = alarma[alarma[columnaSites] == site]
            cambios = site_data[["MES", "TOTAL"]]

            alerta_texto = list(site_alertas[f"ALARMA_{nombre_tab}"])[0]
            with st.expander(f"{site} — {alerta_texto}"):
               
                st.subheader("Detalle de los mantenimientos")
                
                # === NUEVO GRÁFICO DE BARRAS POR SUBESPECIALIDAD ===
                columnas_no_especialidades = ["Site Id Name", "MES", "TOTAL", "CAMBIO_MES_A_MES"]
                df_long = site_data.melt(
                    id_vars=["MES"],
                    value_vars=[c for c in site_data.columns if c not in columnas_no_especialidades],
                    var_name="Subespecialidad",
                    value_name="Cantidad"
                )

                st.bar_chart(
                    df_long,
                    x="MES",
                    y="Cantidad",
                    color="Subespecialidad",
                    horizontal=True
                )


    # === CREACIÓN DE TABS ===
    grupos_prioridades = {
        "P1": "P_1", "P2": "P_2", "P3": "P_3",
        "D1": "D_1", "D2": "D_2", "D3": "D_3",
        "B1": "B_1", "B2": "B_2", "B3": "B_3"
    }

    tabs = st.tabs([f"Sites {k}" for k in grupos_prioridades.keys()])
    for (nombre_tab, codigo_prioridad), tab in zip(grupos_prioridades.items(), tabs):
        with tab:
            mostrar_tab(nombre_tab, codigo_prioridad)

    st.markdown("-------")

    # === DESCARGA DE RESULTADOS ===
    with pd.ExcelWriter("Reporte_Control_Streamlit.xlsx") as writer:
        conteo.to_excel(writer, sheet_name="Conteo", index=False)
        estado.to_excel(writer, sheet_name="Estados", index=False)
        contratista.to_excel(writer, sheet_name="Contratistas", index=False)
        alarma.to_excel(writer, sheet_name="Alarmas", index=False)

    with open("Reporte_Control_Streamlit.xlsx", "rb") as file:
        st.download_button(
            label="⬇️ Descargar reporte completo en Excel",
            data=file,
            file_name="Reporte_Control_Streamlit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Por favor sube un archivo Excel para comenzar el análisis.")
