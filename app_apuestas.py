import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime

st.set_page_config(page_title="Prototipo de Apuestas", layout="wide")

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
        return momio / 100 + 1 if momio > 0 else 100 / abs(momio) + 1

    @staticmethod
    def aplicar_dixon_coles(prob_matrix, lambda_h, lambda_a, rho):
        if rho == 0: return prob_matrix
        # Ajuste para corregir la subestimacion de empates en marcadores bajos
        prob_matrix[0, 0] *= (1 - lambda_h * lambda_a * rho)
        prob_matrix[0, 1] *= (1 + lambda_h * rho)
        prob_matrix[1, 0] *= (1 + lambda_a * rho)
        prob_matrix[1, 1] *= (1 - rho)
        return prob_matrix / prob_matrix.sum()

    @staticmethod
    def calcular_probabilidades(media_h, media_a, rho=0.13):
        max_goles = 8
        prob_h = [poisson.pmf(i, media_h) for i in range(max_goles)]
        prob_a = [poisson.pmf(i, media_a) for i in range(max_goles)]
        matriz = np.outer(prob_h, prob_a)
        
        # Aplicacion de ajuste tecnico
        matriz = MotorAnalisis.aplicar_dixon_coles(matriz, media_h, media_a, rho)
        
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
    
    # Identificacion de columnas
    c_home = "Home" if "Home" in df.columns else "HomeTeam"
    c_away = "Away" if "Away" in df.columns else "AwayTeam"
    c_hg = "HG" if "HG" in df.columns else "FTHG"
    c_ag = "AG" if "AG" in df.columns else "FTAG"
    c_date = "Date" if "Date" in df.columns else None

    df[c_home] = df[c_home].apply(MotorAnalisis.limpiar_texto)
    df[c_away] = df[c_away].apply(MotorAnalisis.limpiar_texto)

    # Ponderacion por Recencia (Time-Decay)
    if c_date:
        df[c_date] = pd.to_datetime(df[c_date])
        max_date = df[c_date].max()
        df['days_diff'] = (max_date - df[c_date]).dt.days
        # Los partidos mas recientes tienen un peso de 1.0, los antiguos disminuyen
        df['weight'] = np.exp(-0.005 * df['days_diff'])
    else:
        df['weight'] = 1.0

    # Promedios de la Liga Ponderados
    p_goles_home = (df[c_hg] * df['weight']).sum() / df['weight'].sum()
    p_goles_away = (df[c_ag] * df['weight']).sum() / df['weight'].sum()

    equipos = sorted(df[c_home].unique())
    local = st.sidebar.selectbox("Equipo Local", equipos)
    visitante = st.sidebar.selectbox("Equipo Visitante", equipos, index=1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("GESTIÓN DE CAPITAL")
    capital_total = st.sidebar.number_input("Capital Total $", value=1000, step=100)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("MOMIOS AMERICANOS")
    m_local = st.sidebar.number_input(f"Momio {local}", value=100)
    m_empate = st.sidebar.number_input("Momio Empate", value=100)
    m_visita = st.sidebar.number_input(f"Momio {visitante}", value=100)
    m_over = st.sidebar.number_input("Momio Over 2.5", value=100)

    # Calculo de Fuerza Relativa con Ponderacion
    def get_weighted_avg(team, col_team, col_goals):
        mask = df[col_team] == team
        return (df[mask][col_goals] * df[mask]['weight']).sum() / df[mask]['weight'].sum()

    att_h = get_weighted_avg(local, c_home, c_hg) / p_goles_home
    def_v = get_weighted_avg(visitante, c_away, c_hg) / p_goles_home
    esp_h = att_h * def_v * p_goles_home

    att_v = get_weighted_avg(visitante, c_away, c_ag) / p_goles_away
    def_h = get_weighted_avg(local, c_home, c_ag) / p_goles_away
    esp_v = att_v * def_h * p_goles_away

    p_w, p_d, p_l, p_o25 = MotorAnalisis.calcular_probabilidades(esp_h, esp_v)

    st.title("Prototipo de Apuestas")
    st.markdown("### RESULTADOS DEL ANÁLISIS")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(local.upper(), f"{p_w:.2%}")
    c2.metric("EMPATE", f"{p_d:.2%}")
    c3.metric(visitante.upper(), f"{p_l:.2%}")
    c4.metric("OVER 2.5", f"{p_o25:.2%}")

    st.markdown("---")
    st.markdown("### RECOMENDACIONES DE INVERSIÓN")
    
    def procesar_apuesta(prob, momio, nombre_mercado):
        dec = MotorAnalisis.momio_a_decimal(momio)
        ventaja = prob - 1 / dec
        col_a, col_b = st.columns([1, 2])
        with col_a: st.write(f"**{nombre_mercado.upper()}**")
        with col_b:
            if ventaja > 0:
                f_kelly = (dec * prob - 1) / (dec - 1) * 0.25
                monto = capital_total * f_kelly
                st.success(f"VENTAJA: {ventaja:.2%} | APUESTA SUGERIDA: ${monto:.2f}")
            else:
                st.write("Sin valor matemático")

    procesar_apuesta(p_w, m_local, local)
    procesar_apuesta(p_d, m_empate, "Empate")
    procesar_apuesta(p_l, m_visita, visitante)
    procesar_apuesta(p_o25, m_over, "Over 2.5")

except Exception as e:
    st.error(f"Fallo en la ejecución: {e}")