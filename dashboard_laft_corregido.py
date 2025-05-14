import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from itertools import combinations

st.set_page_config(layout="wide", page_title="Dashboard LA/FT")

st.title("Dashboard de Segmentación y Alertas LA/FT")
st.write("Sube un archivo con tus datos para aplicar las reglas de segmentación.")

uploaded_file = st.file_uploader("Cargar archivo Excel o CSV", type=["xlsx", "csv"])

def aplicar_reglas_segmentacion(df):
    df["Valor transacción"] = pd.to_numeric(df["Valor transacción"], errors='coerce')
    df = df.dropna(subset=["Valor transacción"])
    mean_val = df["Valor transacción"].mean()
    std_val = df["Valor transacción"].std()
    df["Desviación"] = (df["Valor transacción"] - mean_val) / std_val
    df["Transacción Atípica"] = df["Desviación"].abs() > 2
    df.rename(columns={"Producto ": "Producto"}, inplace=True)

    reglas = pd.DataFrame()
    reglas["ID Cliente"] = df["ID Cliente"]
    reglas["Valor transacción"] = df["Valor transacción"]
    reglas["Transacción Atípica"] = df["Transacción Atípica"]

    reglas["Regla 1"] = df["Desviación"] > 2
    reglas["Regla 2"] = df["Desviación"] < -2
    reglas["Regla 3"] = (df["Activos"] > 50000000) & (df["Valor transacción"] > mean_val + std_val)
    reglas["Regla 4"] = (df["Pasivos"] > df["Activos"]) & (df["Valor transacción"] < mean_val)
    reglas["Regla 5"] = (df["Ingresos"] > df["Egresos"]) & (df["Valor transacción"] > mean_val + 1.5 * std_val)
    reglas["Regla 6"] = (df["Balance_Flujo"] < 0) & (df["Valor transacción"] > mean_val)
    reglas["Regla 7"] = (df["PEP"] == "Si") & (df["Transacción Atípica"])
    reglas["Regla 8"] = (df["Canal de pago"] == "Cripto") & (df["Valor transacción"] > mean_val + 2 * std_val)
    reglas["Regla 9"] = (df["Segmento"] == "Alto") & (df["Valor transacción"] < mean_val - std_val)
    reglas["Regla 10"] = (df["Clase transacción"] == "Crédito") & (df["Canal de pago"] == "Cheque") & (df["Valor transacción"] > mean_val)
    reglas["Regla 11"] = (df["Ingresos"] > 30000000) & df["ID Cliente"].map(df[df["Transacción Atípica"]].groupby("ID Cliente").size()) > 1
    reglas["Regla 12"] = (df["Egresos"] > 40000000) & (df["Canal de pago"] == "Transferencia")
    reglas["Regla 13"] = (df["Código ocupación"] == 8) & (df["Canal de pago"] == "Cripto")
    reglas["Regla 14"] = df["ID Cliente"].map(df[df["Transacción Atípica"]].groupby("ID Cliente").size()) > 3
    reglas["Regla 15"] = df["Ciudad"].isin(["ABEJORRAL", "PUERTO CARREÑO", "LETICIA"]) & (df["Valor transacción"] > mean_val + 2 * std_val)
    reglas["Regla 16"] = (df["Balance_Flujo"] > 0) & (df["Clase transacción"] == "Débito")
    reglas["Regla 17"] = (df["Segmento"] == "Bajo") & (df["Valor transacción"] > mean_val + 1.5 * std_val)
    reglas["Regla 18"] = pd.to_datetime("today") - pd.to_datetime(df["Fecha de vinculación"]) < pd.Timedelta(days=365)
    reglas["Regla 19"] = df["ID Cliente"].map(df.groupby("ID Cliente")["Producto"].nunique()) > 1
    reglas["Regla 20"] = df["Código CIIU"].isin([8639, 6275]) & df["Transacción Atípica"]

    reglas["Suma Reglas Cumplidas"] = reglas.drop(columns=["ID Cliente", "Valor transacción", "Transacción Atípica"]).sum(axis=1)
    reglas["Alerta LAFT"] = reglas["Suma Reglas Cumplidas"] >= 2

    # Generar combinaciones 2 a 2 entre las 20 reglas
    reglas_binarias = [col for col in reglas.columns if col.startswith("Regla ")]
    for r1, r2 in combinations(reglas_binarias, 2):
        nombre_columna = f"Combinación_{r1[-2:].strip()}_{r2[-2:].strip()}"
        reglas[nombre_columna] = reglas[r1] & reglas[r2]

    return pd.concat([df.reset_index(drop=True), reglas.drop(columns=["ID Cliente", "Valor transacción"])], axis=1)

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    resultados = aplicar_reglas_segmentacion(df)

    # Verificar y renombrar columnas duplicadas
    if resultados.columns.duplicated().any():
        st.warning("Se encontraron columnas duplicadas en los resultados. Se renombrarán automáticamente.")
        resultados.columns = [
            f"{col}_{i}" if resultados.columns.duplicated()[j] else col
            for j, (col, i) in enumerate(zip(resultados.columns, range(len(resultados.columns))))
        ]

    st.subheader("Resumen de Alertas")
    st.metric("Transacciones Analizadas", len(resultados))
    st.metric("Alertas LAFT Generadas", resultados["Alerta LAFT"].sum())

    if "Transacción Atípica" in resultados.columns:
        if resultados["Transacción Atípica"].ndim == 1:
            st.subheader("Distribución de Transacciones Atípicas")
            st.bar_chart(resultados["Transacción Atípica"].value_counts())
        else:
            st.error("La columna 'Transacción Atípica' no es unidimensional.")
    else:
        st.error("La columna 'Transacción Atípica' no se encuentra en los resultados.")

    st.subheader("Visualizaciones por Factores de Riesgo")
    for campo in ["Ciudad", "Código CIIU", "Canal de pago", "Segmento", "Producto", "Código ocupación"]:
        if campo in resultados.columns:
            fig = px.histogram(resultados, x=campo, color="Alerta LAFT", barmode="group", title=f"Distribución por {campo}")
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Filtrar por Combinaciones de Reglas")

    combinaciones_cols = [col for col in resultados.columns if col.startswith("Combinación_")]
    seleccionadas = st.multiselect("Selecciona combinaciones específicas", combinaciones_cols)

    filtro = pd.Series([True] * len(resultados))
    tipo_filtro = st.radio("Tipo de filtro por combinaciones", ["Cumple todas", "Cumple al menos una"])

    if seleccionadas:
        if tipo_filtro == "Cumple todas":
            filtro = resultados[seleccionadas].all(axis=1)
        else:
            filtro = resultados[seleccionadas].any(axis=1)
        st.write(f"Mostrando {filtro.sum()} registros que cumplen el criterio seleccionado.")
        resultados = resultados[filtro]

    st.subheader("Filtros adicionales por columnas")

    if "Ciudad" in resultados.columns:
        ciudad_filtro = st.multiselect("Filtrar por ciudad", resultados["Ciudad"].dropna().unique())
        if ciudad_filtro:
            resultados = resultados[resultados["Ciudad"].isin(ciudad_filtro)]

    if "Fecha de vinculación" in resultados.columns:
        resultados["Fecha de vinculación"] = pd.to_datetime(resultados["Fecha de vinculación"], errors='coerce')
        fecha_min = resultados["Fecha de vinculación"].min()
        fecha_max = resultados["Fecha de vinculación"].max()
        fecha_range = st.date_input("Rango de fechas de vinculación", [fecha_min, fecha_max])
        if len(fecha_range) == 2:
            resultados = resultados[
                (resultados["Fecha de vinculación"] >= pd.to_datetime(fecha_range[0])) &
                (resultados["Fecha de vinculación"] <= pd.to_datetime(fecha_range[1]))
            ]

    if "Canal de pago" in resultados.columns:
        canal_filtro = st.multiselect("Filtrar por canal de pago", resultados["Canal de pago"].dropna().unique())
        if canal_filtro:
            resultados = resultados[resultados["Canal de pago"].isin(canal_filtro)]

    if "Segmento" in resultados.columns:
        segmento_filtro = st.multiselect("Filtrar por segmento", resultados["Segmento"].dropna().unique())
        if segmento_filtro:
            resultados = resultados[resultados["Segmento"].isin(segmento_filtro)]

    st.subheader("Casos con Alerta LAFT")
    st.dataframe(resultados[resultados["Alerta LAFT"] == True])

    st.subheader("Todos los Resultados")
    st.dataframe(resultados)

    st.download_button("Descargar resultados en CSV", data=resultados.to_csv(index=False), file_name="resultados_laft.csv")
