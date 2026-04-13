import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Prototio de Apuestas", layout="wide")

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

st.sidebar.header("CONFIGURACIÓN")
liga = st.sidebar.selectbox("División", ["Bundesliga", "Championship"])
archivo = f"Data/BL1_2026.csv" if liga == "Bundesliga" else "Data/ELC_2026.csv"

try:
    df = pd.read_csv(archivo)
    
    c_home = "Home" if "Home" in df.columns else "HomeTeam"
    c_away = "Away" if "Away" in df.columns else "AwayTeam"
    c_hg = "HG" if "HG" in df.columns else "FTHG"
    c_ag = "AG" if "AG" in df.columns else "FTAG"

    df[c_home] = df[c_home].apply(MotorAnalisis.limpiar_texto)
    df[c_away] = df[c_away].apply(MotorAnalisis.limpiar_texto)

    p_goles_home = df[c_hg].mean()
    p_goles_away = df[c_ag].mean()

    equipos = sorted(df[c_home].unique())
    
    local = st.sidebar.selectbox("Equipo Local", equipos)
    visitante = st.sidebar.selectbox("Equipo Visitante", equipos, index=1)
    m_local = st.sidebar.number_input(f"Momio Americano {local}", value=100)

    f_ataque_local = df[df[c_home] == local][c_hg].mean() / p_goles_home
    f_defensa_visitante = df[df[c_away] == visitante][c_hg].mean() / p_goles_home
    esp_goles_local = f_ataque_local * f_defensa_visitante * p_goles_home

    f_ataque_visitante = df[df[c_away] == visitante][c_ag].mean() / p_goles_away
    f_defensa_local = df[df[c_home] == local][c_ag].mean() / p_goles_away
    esp_goles_visitante = f_ataque_visitante * f_defensa_local * p_goles_away

    p_w, p_d, p_l, p_o25 = MotorAnalisis.calcular_probabilidades(esp_goles_local, esp_goles_visitante)

    st.title("SISTEMA DE ANÁLISIS")
    st.markdown("### RESULTADOS DEL ANÁLISIS")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(local.upper(), f"{p_w:.2%}")
    c2.metric("EMPATE", f"{p_d:.2%}")
    c3.metric(visitante.upper(), f"{p_l:.2%}")
    c4.metric("OVER 2.5", f"{p_o25:.2%}")

    st.markdown("---")
    
    decimal_mercado = MotorAnalisis.momio_a_decimal(m_local)
    prob_mercado = 1 / decimal_mercado
    ventaja = p_w - prob_mercado

    if ventaja > 0:
        st.success(f"VENTAJA DETECTADA: {ventaja:.2%}")
        kelly = ((decimal_mercado * p_w - 1) / (decimal_mercado - 1)) * 0.25
        st.info(f"INVERSIÓN SUGERIDA: {max(0, kelly):.2%} DEL CAPITAL TOTAL")
    else:
        st.error("SIN VALOR MATEMÁTICO DETECTADO")

except Exception as e:
    st.error(f"FALLO EN LA EJECUCIÓN: {e}")