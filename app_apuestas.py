import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# Configuración de interfaz profesional
st.set_page_config(page_title="Prototipo de Apuestas 2026", layout="wide")

class MotorAnalisis:
    @staticmethod
    def limpiar_texto(texto):
        t = str(texto).lower().strip()
        basura = ["fc ", "vfl ", "sv ", "1. ", "rb ", "tsg ", "04 ", "1899 ", "1910 ", "vfb ", "afc ", "sc ", "bayer 04 "]
        for b in basura:
            t = t.replace(b, "")
        return t.replace("ü", "u").replace("ö", "o").replace("ä", "a")

    @staticmethod
    def momio_a_decimal(momio):
        if momio == 0: return 1.0
        if momio > 0:
            return momio / 100 + 1
        return 100 / abs(momio) + 1

    @staticmethod
    def calcular_probabilidades(media_home, media_away):
        max_goles = 8
        prob_h = [poisson.pmf(i, media_home) for i in range(max_goles)]
        prob_a = [poisson.pmf(i, media_away) for i in range(max_goles)]
        matriz = np.outer(prob_h, prob_a)
        
        win = np.sum(np.tril(matriz, -1))
        draw = np.sum(np.diag(matriz))
        loss = np.sum(np.triu(matriz, 1))
        over25 = 1 - np.sum(matriz[:2, :2]) - matriz[0, 2] - matriz[2, 0]
        
        return win, draw, loss, over25

# Carga de datos
st.title("SISTEMA DE ANÁLISIS PREDICTIVO")
liga = st.sidebar.selectbox("División", ["Bundesliga", "Championship"])
archivo = f"Data/BL1_2026.csv" if liga == "Bundesliga" else "Data/ELC_2026.csv"

try:
    df = pd.read_csv(archivo)
    df["Home"] = df["Home"].apply(MotorAnalisis.limpiar_texto)
    df["Away"] = df["Away"].apply(MotorAnalisis.limpiar_texto)

    # Estadísticas Globales de la Liga
    promedio_goles_home = df["HG"].mean()
    promedio_goles_away = df["AG"].mean()

    # Selección de Equipos
    equipos = sorted(df["Home"].unique())
    col_l, col_v = st.columns(2)
    local = col_l.selectbox("Equipo Local", equipos)
    visitante = col_v.selectbox("Equipo Visitante", equipos, index=1)

    # Cálculo de Fuerza Relativa
    # Local: Capacidad de ataque contra promedio liga
    fuerza_ataque_local = df[df["Home"] == local]["HG"].mean() / promedio_goles_home
    fuerza_defensa_visitante = df[df["Away"] == visitante]["HG"].mean() / promedio_goles_home
    esperanza_goles_local = fuerza_ataque_local * fuerza_defensa_visitante * promedio_goles_home

    # Visitante: Capacidad de ataque contra promedio liga
    fuerza_ataque_visitante = df[df["Away"] == visitante]["AG"].mean() / promedio_goles_away
    fuerza_defensa_local = df[df["Home"] == local]["AG"].mean() / promedio_goles_away
    esperanza_goles_visitante = fuerza_ataque_visitante * fuerza_defensa_local * promedio_goles_away

    p_w, p_d, p_l, p_o25 = MotorAnalisis.calcular_probabilidades(esperanza_goles_local, esperanza_goles_visitante)

    # Dashboard de Métricas
    st.markdown("Probabilidades de Victoria")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(local.upper(), f"{p_w:.2%}")
    c2.metric("EMPATE", f"{p_d:.2%}")
    c3.metric(visitante.upper(), f"{p_l:.2%}")
    c4.metric("OVER 2.5", f"{p_o25:.2%}")

    # Análisis de Valor
    st.markdown("Comparativa contra Mercado")
    m_local = st.number_input(f"Momio Americano {local}", value=100)
    
    decimal_mercado = MotorAnalisis.momio_a_decimal(m_local)
    prob_mercado = 1 / decimal_mercado
    ventaja = p_w - prob_mercado

    if ventaja > 0:
        st.success(f"Ventaja detectada: {ventaja:.2%}. El momio tiene valor matemático.")
        # Criterio de Kelly fraccionado al 25 por ciento para gestión de riesgo
        kelly = ((decimal_mercado * p_w - 1) / (decimal_mercado - 1)) * 0.25
        st.info(f"Sugerencia de inversión: {max(0, kelly):.2%} del capital total.")
    else:
        st.error("Sin valor. La probabilidad del mercado es mayor a la calculada.")

except Exception as e:
    st.error(f"Fallo en la ejecución: {e}")