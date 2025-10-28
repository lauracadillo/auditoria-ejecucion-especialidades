# === Importación de librerías necesarias ===
import streamlit as st     
import pandas as pd        

# === CONFIGURACIÓN GENERAL DE LA PÁGINA ===
# Definir el título de la pestaña del navegador y el formato de la página
st.set_page_config(page_title="Control de Mantenimientos", layout="wide")

# Título principal 
st.title("Herramienta para la auditoria de ejecución de especialidades")

# === SUBIR ARCHIVO ===
# por si se desea que se pueda subir el archivo en la pagina 
# archivo = st.file_uploader("Sube el archivo Excel con la data", type=["xlsx"])

# archivo excel fijo que se usará
archivo = "libroTest.xlsx" 

if archivo:
    # Nombre de la hoja dentro del archivo Excel (ajustar si cambia)
    hoja = "Hoja2"

    df = pd.read_excel(archivo, sheet_name=hoja)

    # Quita espacios extra en los nombres de las columnas
    df.columns = df.columns.str.strip()

    # === DEFINICIÓN DE COLUMNAS ===
    #Ajustar estos nombres para que coincidan con los nombres de las columnas por si cambian
    columnaEspecialidades = "SUB_ESPECIALIDAD"
    columnaSites = "Site Id Name"
    columnaPrioridad = "Site Priority"
    columnaFLM = "Contratista Sitio"
    columnaEstado = "ESTADO"
    columnaFecha = "2_MES_PROGRA"
    columnaFLMEspecifico = "SUP_FLM_2"

    # Lista general con las subespecialidades que se analizarán (extraidas del archivo de mtto preventivo)
    SubEspecialidadesGenerales = [
        "AA", "GE-TTA-TK", "IE", "SE-LT", "REC-BB", "TX", "TX-BH",
        "UPS", "INV-AVR", "LT", "RADIO", "SOL-EOL", "#N/D", "0"
    ]

    # === CONVERSIÓN DE FECHAS ===

    # convertir fechas a texto y eliminar los espacios
    df[columnaFecha] = df[columnaFecha].astype(str).str.strip().str.lower()

    # Diccionario que traduce abreviaturas de meses a su número (ej. 'ene' -> '01')
    meses = {
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'oct': '10', 'nov': '11', 'dic': '12',
    }

    # Función para convertir los valores tipo "jul-25" en formato "2025-07"
    def convertir_mes_ano(valor):
        # Se valida que el valor sea texto y tenga un guion (mes-año)
        if isinstance(valor, str) and '-' in valor:
            mes_abrev, anio = valor.split('-')     # Se separa el mes y el año
            mes_abrev = mes_abrev.strip().lower()
            anio = anio.strip()
            mes = meses.get(mes_abrev, None)       # Se obtiene el número del mes
            if mes:
                return f"20{anio}-{mes}"           # Se arma el formato final (YYYY-MM)
        return "Fecha desconocida"                       # Si no se puede convertir, se marca así

    # Se crea una nueva columna "MES" con las fechas ya convertidas
    df["MES"] = df[columnaFecha].apply(convertir_mes_ano)

    # === FILTRAR SUBESPECIALIDADES DE LA LISTA ===
    # df = df[df[columnaEspecialidades].isin(SubEspecialidadesGenerales)]

    # === CONTEO DE SUBESPECIALIDADES POR SITE Y MES ===
    # Agrupa los datos por sitio, mes y subespecialidad, y cuenta cuántos registros hay
    conteo = (
        df.groupby([columnaSites, "MES", columnaEspecialidades])
        .size()
        .unstack(fill_value=0)  # Pivotea la tabla para tener cada subespecialidad como columna
    )

    # Agrega 0 si una subespecialidad no se revisó ese mes en ese sitio
    for sub in SubEspecialidadesGenerales:
        if sub not in conteo.columns:
            conteo[sub] = 0

    # Da un orden consistente a las columnas de subespecialidades
    conteo = conteo[SubEspecialidadesGenerales]

    # Suma de todas las especialidades del sitio y mes
    conteo["TOTAL"] = conteo.sum(axis=1)

    # Restablece el índice para que las columnas vuelvan a ser normales (no parte del índice)
    conteo.reset_index(inplace=True)

    # === CAMBIO MES A MES ===
    # Calcula cuánto cambia el total de especialidades de un mes al siguiente para cada site
    conteo["CAMBIO_MES_A_MES"] = conteo.groupby(columnaSites)["TOTAL"].diff().fillna(0)

    # === ESTADOS (Ejecutado vs Total) ===
    # Cuenta cuántos mantenimientos hay por estado (Ejecutado, Pendiente, etc.)
    estado = (
        df.groupby([columnaSites, "MES", columnaEspecialidades, columnaEstado])
        .size()
        .unstack(fill_value=0)
    )

    # Si existe la columna "Cancelado", se calcula el porcentaje de mttos cancelados 

    if "Cancelado" in estado.columns:
        estado["Total"] = estado.sum(axis=1)
        estado["% Cancelado"] = (estado["Cancelado"] / estado["Total"]).round(2)
    else:
        # Si no hay columna ejecutado, se asume 0%
        estado["% Cancelado"] = 0

    # Convierte los índices nuevamente a columnas
    estado.reset_index(inplace=True)

    # === CONTRATISTA ===
    # Agrupa los datos por contratista, site y mes, y cuenta cuántos registros tiene cada uno
    contratista = (
        df.groupby([columnaFLM, columnaSites, "MES"])
        .size()
        .reset_index(name="Cantidad")
    )

   
    # === ALARMAS ===
    # Se usa para detectar disminuciones en la cantidad de especialidades 
    prioridad = df[[columnaSites, columnaPrioridad]].drop_duplicates()

    # Se combina la tabla de prioridades con el conteo de especialidades
    alarma = pd.merge(prioridad, conteo, on=columnaSites, how="left")

    # Función para generar una alerta si hay una disminución de especialidades en un sitio prioritario (P_1)
    def generar_alarma(row):
        if row[columnaPrioridad] == "P_1" and row["CAMBIO_MES_A_MES"] < 0:
            return f"⚠️ Disminución de especialidades ({row['CAMBIO_MES_A_MES']}) respecto al mes anterior"
        return ""
    
    # Aplica la función a cada fila y crea una nueva columna llamada "ALARMA"
    alarma["ALARMA"] = alarma.apply(generar_alarma, axis=1)

    # === VISUALIZACIÓN DE RESULTADOS  ===


    # === 🚨 SECCIÓN DE ALARMAS (sitios con disminución de especialidades) ===
    st.subheader("🚨 Alarmas por prioridad (Sitios con disminución de especialidades de mes a mes)")

    # Filtra los sitios que tienen una alerta (es decir, una disminución de subespecialidades detectada)
    sitios_con_baja = alarma[alarma["ALARMA"] != ""][columnaSites].unique()

    # Para cada sitio con alerta, muestra su evolución histórica mes a mes
    for site in sitios_con_baja:

        # Extrae los datos solo de ese sitio y los ordena cronológicamente
        site_data = conteo[conteo[columnaSites] == site].sort_values("MES")

        # Obtiene el texto de la alerta asociada
        site_alertas = alarma[alarma[columnaSites] == site]

        # Selecciona las columnas que se van a mostrar (mes y total)
        cambios = site_data[["MES", "TOTAL"]]


        # Crea una sección desplegable (expander) que se abre al hacer clic
        with st.expander(f"📉 {site} — {list(site_alertas['ALARMA'])[0]}"):
            
            # Muestra un gráfico de barras con la evolución mensual
            tab1, tab2 = st.tabs(["Conteo mensual", "Detalle subespecialidades"])
            with tab1:
                st.subheader("Conteo mensual")
                #hacer que solo se muestre para el site definido
                st.bar_chart(cambios.set_index("MES"))
            with tab2:
                st.subheader("Detalle de los mantenimientos ")
                # Muestra una tabla con los totales por mes
                st.dataframe(site_data.set_index("MES"))

    st.markdown("-------")

    # === DESCARGA DE RESULTADOS ===
    # Guarda todos los resultados en un archivo Excel con varias hojas
    with pd.ExcelWriter("Reporte_Control_Streamlit.xlsx") as writer:
        conteo.to_excel(writer, sheet_name="Conteo", index=False)
        estado.to_excel(writer, sheet_name="Estados", index=False)
        contratista.to_excel(writer, sheet_name="Contratistas", index=False)
        alarma.to_excel(writer, sheet_name="Alarmas", index=False)

    # Crea un botón en la interfaz para descargar el archivo Excel generado
    with open("Reporte_Control_Streamlit.xlsx", "rb") as file:
        st.download_button(
            label="⬇️ Descargar reporte completo en Excel",  # Texto del botón
            data=file,                                     # Contenido del archivo
            file_name="Reporte_Control_Streamlit.xlsx",    # Nombre del archivo descargado
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  # Tipo de archivo
        )

# Si no hay archivo cargado, muestra un mensaje informativo en pantalla
else:
    st.info("Por favor sube un archivo Excel para comenzar el análisis.")
