import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import os

# --- 1. CONFIGURACION DE LA INTERFAZ ---
st.set_page_config(page_title="Sistema de Apuestas", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; }
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; }
    .safe-bet { border-left: 8px solid #10b981; }
    .risky-bet { border-left: 8px solid #f59e0b; }
    .custom-progress-bg { background-color: #374151; border-radius: 10px; height: 12px; width: 100%; margin-bottom: 15px; overflow: hidden; }
    .custom-progress-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CALCULO Y CONVERSOR ---
class AnalysisEngine:
    @staticmethod
    def american_to_decimal(momio):
        if momio is None or momio == 0: return None
        if momio > 0: return (momio / 100) + 1
        return (100 / abs(momio)) + 1

    @staticmethod
    def calcular_stats_completas(media_h, media_v):
        media_h = 0.001 if pd.isna(media_h) or media_h <= 0 else media_h
        media_v = 0.001 if pd.isna(media_v) or media_v <= 0 else media_v
        prob_h, prob_e, prob_v, over25, btts = 0, 0, 0, 0, 0
        for g_h in range(9):
            for g_v in range(9):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                if g_h > g_v: prob_h += p
                elif g_h == g_v: prob_e += p
                else: prob_v += p
                if (g_h + g_v) > 2.5: over25 += p
                if g_h > 0 and g_v > 0: btts += p
        return {"Win_H": prob_h, "Draw": prob_e, "Win_V": prob_v, "Over25": over25, "BTTS": btts}

    @staticmethod
    def kelly_criterion(prob, cuota_decimal, bankroll):
        if cuota_decimal is None or cuota_decimal <= 1: return 0
        b, q = cuota_decimal - 1, 1 - prob
        f = (b * prob - q) / b
        return max(0, f * bankroll * 0.5)

# --- 3. LISTAS OFICIALES DE EQUIPOS (TEMPORADA 25/26) ---
EQUIPOS_BUNDESLIGA = [
    "1. FC Heidenheim 1846", "1. FC Union Berlin", "1. FSV Mainz 05", "Bayer 04 Leverkusen",
    "Borussia Dortmund", "Borussia Mönchengladbach", "Eintracht Frankfurt", "FC Augsburg",
    "FC Bayern München", "FC St. Pauli", "Holstein Kiel", "RB Leipzig", "SC Freiburg",
    "SV Werder Bremen", "TSG 1899 Hoffenheim", "VfB Stuttgart", "VfL Bochum 1848", "VfL Wolfsburg"
]

EQUIPOS_CHAMPIONSHIP = [
    "Blackburn Rovers", "Bristol City", "Burnley FC", "Cardiff City", "Coventry City",
    "Derby County", "Hull City", "Leeds United", "Luton Town", "Middlesbrough FC",
    "Millwall FC", "Norwich City", "Oxford United", "Plymouth Argyle", "Portsmouth FC",
    "Preston North End", "Queens Park Rangers", "Sheffield United", "Sheffield Wednesday",
    "Stoke City", "Sunderland AFC", "Swansea City", "Watford FC", "West Bromwich Albion"
]

# --- 4. GESTION DE DATOS ---
@st.cache_data
def cargar_datos(liga_file):
    ruta = f"Data/{liga_file}.csv"
    if os.path.exists(ruta):
        df = pd.read_csv(ruta)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return None

# --- 5. INTERFAZ DE USUARIO ---
st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    capital = st.number_input("Capital Total", min_value=0.0, value=1000.0, format="%g")
    liga_opciones = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026"}
    seleccion_liga = st.selectbox("Competicion:", list(liga_opciones.keys()))
    archivo_liga = liga_opciones[seleccion_liga]

df = cargar_datos(archivo_liga)

if df is not None:
    lista_activa = EQUIPOS_BUNDESLIGA if seleccion_liga == "Bundesliga" else EQUIPOS_CHAMPIONSHIP
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: e_h = st.selectbox("Equipo Local", lista_activa)
    with col_sel2: e_v = st.selectbox("Equipo Visitante", lista_activa, index=1)

    m_h = df[df['Home'] == e_h]['HG'].mean()
    m_v = df[df['Away'] == e_v]['AG'].mean()
    stats = AnalysisEngine.calcular_stats_completas(m_h, m_v)

    st.markdown("---")
    st.subheader("Probabilidades Calculadas")
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric(f"Gana {e_h}", f"{stats['Win_H']*100:.1f}%")
    p2.metric("Empate", f"{stats['Draw']*100:.1f}%")
    p3.metric(f"Gana {e_v}", f"{stats['Win_V']*100:.1f}%")
    p4.metric("+2.5 Goles", f"{stats['Over25']*100:.1f}%")
    p5.metric("Ambos Anotan", f"{stats['BTTS']*100:.1f}%")

    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales (+/-)")
    c_m1, c_m2, c_m3, c_m4, c_m5 = st.columns(5)
    
    # step=1 asegura que solo se ingresen números enteros
    with c_m1: m_h_raw = st.number_input(f"Momio {e_h}", value=None, step=1, placeholder="-110")
    with c_m2: m_d_raw = st.number_input("Momio Empate", value=None, step=1, placeholder="+300")
    with c_m3: m_v_raw = st.number_input(f"Momio {e_v}", value=None, step=1, placeholder="-110")
    with c_m4: m_o_raw = st.number_input("Momio +2.5 Goles", value=None, step=1, placeholder="-150")
    with c_m5: m_b_raw = st.number_input("Momio Ambos Anotan", value=None, step=1, placeholder="-120")

    m_l, m_e, m_vi = AnalysisEngine.american_to_decimal(m_h_raw), AnalysisEngine.american_to_decimal(m_d_raw), AnalysisEngine.american_to_decimal(m_v_raw)
    m_o, m_ba = AnalysisEngine.american_to_decimal(m_o_raw), AnalysisEngine.american_to_decimal(m_b_raw)

    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | 
                         ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    
    st.subheader("Enfrentamientos Directos")
    st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)

    if all([m_l, m_e, m_vi, m_o, m_ba]):
        st.markdown("---")
        st.subheader("Analisis de Pronostico y Apuesta")
        res1, res2 = st.columns(2)

        with res1:
            pick, prob, cuota = (f"Victoria {e_h}", stats['Win_H'], m_l) if stats['Win_H'] > stats['BTTS'] else ("Ambos Anotan", stats['BTTS'], m_ba)
            st.markdown(f"""<div class="bet-card safe-bet"><div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {prob*100}%; background-color: #10b981;"></div></div>
            <h3>Opcion Segura</h3><p><b>Pronostico:</b> {pick}</p><p><b>Probabilidad:</b> {prob*100:.1f}%</p>
            <div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold;">Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob, cuota, capital)))}</div></div>""", unsafe_allow_html=True)

        with res2:
            prob_c, cuota_c = stats['Win_H'] * stats['Over25'], m_l * m_o * 0.85 
            st.markdown(f"""<div class="bet-card risky-bet"><div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {prob_c*100}%; background-color: #f59e0b;"></div></div>
            <h3>Opcion Arriesgada</h3><p><b>Pronostico:</b> {e_h} y +2.5 Goles</p><p><b>Probabilidad:</b> {prob_c*100:.1f}%</p>
            <div style="background-color: #78350f; padding: 10px; border-radius: 8px; color: #f59e0b; font-weight: bold;">Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob_c, cuota_c, capital)))}</div></div>""", unsafe_allow_html=True)

        ev_l, ev_o = (stats['Win_H'] * m_l) - 1, (stats['Over25'] * m_o) - 1
        m_pick, m_prob, m_cuota = ("+2.5 Goles", stats['Over25'], m_o) if ev_o > ev_l else (f"Victoria: {e_h}", stats['Win_H'], m_l)
        st.markdown(f"""<div class="bet-card" style="border-top: 5px solid #3b82f6;"><div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {m_prob*100}%; background-color: #3b82f6;"></div></div>
        <h3>Seleccion Optima</h3><p style="color: #93c5fd;">Ventaja Detectada: <b>{m_pick}</b> con un {m_prob*100:.1f}%.</p>
        <div style="background-color: #1e3a8a; padding: 10px; border-radius: 8px; color: #93c5fd; font-weight: bold;">Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(m_prob, m_cuota, capital)))}</div></div>""", unsafe_allow_html=True)
else:
    st.error("Error: Archivos de datos no detectados.")