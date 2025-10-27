import streamlit as st
import pandas as pd

# === CONFIGURACIÓN GENERAL ===
st.set_page_config(page_title="Control de Mantenimientos", layout="wide")

st.title(" Herramienta para la auditoria de ejecución especialidades")

# === SUBIR ARCHIVO ===
archivo = st.file_uploader("Sube el archivo Excel con la data", type=["xlsx"])

if archivo:
    hoja = "Hoja1"  # puedes permitir que el usuario seleccione si lo deseas
    df = pd.read_excel(archivo, sheet_name=hoja)
    df.columns = df.columns.str.strip()

    # === COLUMNAS ===
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
    meses = {
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'oct': '10', 'nov': '11', 'dic': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }

    def convertir_mes_ano(valor):
        if isinstance(valor, str) and '-' in valor:
            mes_abrev, anio = valor.split('-')
            mes_abrev = mes_abrev.strip().lower()
            anio = anio.strip()
            mes = meses.get(mes_abrev, None)
            if mes:
                return f"20{anio}-{mes}"
        return "Desconocido"

    df["MES"] = df[columnaFecha].apply(convertir_mes_ano)

    # === FILTRAR ===
    df = df[df[columnaEspecialidades].isin(SubEspecialidadesGenerales)]

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

    # === ESTADOS CLOSED ===
    estado = (
        df.groupby([columnaSites, "MES", columnaEspecialidades, columnaEstado])
        .size()
        .unstack(fill_value=0)
    )
    if "Closed" in estado.columns:
        estado["Total"] = estado.sum(axis=1)
        estado["% Closed"] = (estado["Closed"] / estado["Total"]).round(2)
    else:
        estado["% Closed"] = 0
    estado.reset_index(inplace=True)

    # === CONTRATISTA ===
    contratista = (
        df.groupby([columnaFLM, columnaSites, "MES"])
        .size()
        .reset_index(name="Cantidad")
    )

    # === OFICINA ===
    oficina = (
        df.groupby([columnaFLMEspecifico, columnaSites, "MES"])
        .size()
        .reset_index(name="Cantidad")
    )

    # === ALARMAS ===
    prioridad = df[[columnaSites, columnaPrioridad]].drop_duplicates()
    alarma = pd.merge(prioridad, estado, on=columnaSites, how="left")

    def generar_alarma(row):
        if row.get(columnaPrioridad, "") == "alta" and row.get("% Closed", 1) < 0.8:
            return "⚠️ Cierre bajo en sitio prioritario"
        return ""

    alarma["ALARMA"] = alarma.apply(generar_alarma, axis=1)

    # === VISUALIZACIÓN ===
    st.subheader("📈 Conteo de subespecialidades por Site y Mes")
    st.dataframe(conteo)

    st.subheader("🧾 Estado de mantenimiento (Closed vs Total)")
    st.dataframe(estado)

    st.subheader("🏗️ Reporte por Contratista")
    st.dataframe(contratista)

    st.subheader("🏢 Reporte por Oficina")
    st.dataframe(oficina)

    st.subheader("🚨 Alarmas por prioridad")
    st.dataframe(alarma[alarma["ALARMA"] != ""])

    # === DESCARGA DE RESULTADOS ===
    with pd.ExcelWriter("Reporte_Control_Streamlit.xlsx") as writer:
        conteo.to_excel(writer, sheet_name="Conteo", index=False)
        estado.to_excel(writer, sheet_name="Estados", index=False)
        contratista.to_excel(writer, sheet_name="Contratistas", index=False)
        oficina.to_excel(writer, sheet_name="Oficinas", index=False)
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
