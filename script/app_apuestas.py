import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import os

# --- 1. CONFIGURACION DE LA INTERFAZ ---
st.set_page_config(page_title="Prototipo de Apuestas", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; }
    .edge-badge { padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; margin-top: 5px; display: inline-block; }
    .edge-pos { background-color: #064e3b; color: #10b981; }
    .edge-neg { background-color: #451a1a; color: #f87171; }
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; }
    .trend-box { background-color: #064e3b; color: #10b981; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CALCULO ---
class AnalysisEngine:
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
    def calcular_edge(prob, momio):
        if not momio or momio <= 1: return 0
        # Edge = (Probabilidad * Momio) - 1
        return (prob * momio) - 1

# --- 3. DATOS Y EQUIPOS ---
EQUIPOS_BUNDESLIGA = ["Bayer 04 Leverkusen", "FC Bayern München", "Borussia Dortmund", "RB Leipzig", "VfB Stuttgart", "Eintracht Frankfurt", "TSG 1899 Hoffenheim", "1. FC Heidenheim 1846", "SV Werder Bremen", "SC Freiburg", "FC Augsburg", "VfL Wolfsburg", "1. FSV Mainz 05", "Borussia Mönchengladbach", "1. FC Union Berlin", "VfL Bochum 1848", "FC St. Pauli", "Holstein Kiel"]
EQUIPOS_CHAMPIONSHIP = ["Burnley FC", "Luton Town", "Sheffield United", "Leeds United", "West Bromwich Albion", "Norwich City", "Hull City", "Sunderland AFC", "Stoke City", "Watford FC"] # Lista resumida para ejemplo

@st.cache_data
def cargar_datos(liga_file):
    ruta = f"Data/{liga_file}.csv"
    if os.path.exists(ruta):
        df = pd.read_csv(ruta)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return None

# --- 4. APP ---
st.title("Prototipo de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    capital = st.number_input("Capital Total", min_value=0.0, value=1000.0, format="%g")
    liga_opciones = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026"}
    seleccion_liga = st.selectbox("Competicion:", list(liga_opciones.keys()))
    archivo_liga = liga_opciones[seleccion_liga]

df = cargar_datos(archivo_liga)

if df is not None:
    lista_equipos = EQUIPOS_BUNDESLIGA if seleccion_liga == "Bundesliga" else EQUIPOS_CHAMPIONSHIP
    c1, c2 = st.columns(2)
    with c1: e_h = st.selectbox("Equipo Local", lista_equipos)
    with c2: e_v = st.selectbox("Equipo Visitante", lista_equipos, index=1)

    # --- ENTRADA DE MOMIOS ---
    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: momio_h = st.number_input(f"Momio {e_h}", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col2: momio_v = st.number_input(f"Momio {e_v}", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col3: momio_o25 = st.number_input("Momio Over 2.5", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col4: momio_btts = st.number_input("Momio Ambos Anotan", min_value=1.0, value=None, format="%g", placeholder="0")

    # --- RESULTADOS Y EDGE ---
    m_h_avg = df[df['Home'] == e_h]['HG'].mean()
    m_v_avg = df[df['Away'] == e_v]['AG'].mean()
    stats = AnalysisEngine.calcular_stats_completas(m_h_avg, m_v_avg)

    st.markdown(f"### Datos de la: {seleccion_liga}")
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

    markets = [
        (f"Victoria {e_h}", stats['Win_H'], momio_h),
        (f"Victoria {e_v}", stats['Win_V'], momio_v),
        ("Probabilidad Over 2.5", stats['Over25'], momio_o25),
        ("Probabilidad Ambos Anotan", stats['BTTS'], momio_btts)
    ]

    cols = [p_col1, p_col2, p_col3, p_col4]
    for i, (name, prob, momio) in enumerate(markets):
        with cols[i]:
            st.markdown(f"**{name}**")
            st.markdown(f"## {prob*100:.1f}%")
            if momio:
                edge = AnalysisEngine.calcular_edge(prob, momio)
                color = "edge-pos" if edge > 0 else "edge-neg"
                st.markdown(f'<div class="edge-badge {color}">Edge: {edge*100:+.1f}%</div>', unsafe_allow_html=True)

    # --- VALIDACION DE TENDENCIA (ULTIMOS 3) ---
    st.markdown("---")
    st.subheader("Validacion de Tendencia: Ultimos 3 partidos")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    
    if len(enfrentamientos) >= 3:
        ultimos_3 = enfrentamientos.head(3)
        over_25_count = ((ultimos_3['HG'] + ultimos_3['AG']) > 2.5).sum()
        pct_hist = (over_25_count / 3) * 100
        
        t_col1, t_col2 = st.columns([2, 1])
        with t_col1:
            st.write(f"Muestra analizada: 3 enfrentamientos")
            st.progress(pct_hist / 100)
            st.write(f"Porcentaje Historico Over 2.5: {pct_hist:.1f}%")
        with t_col2:
            if pct_hist >= 66:
                st.markdown('<div class="trend-box">Confirmacion estadistica alta</div>', unsafe_allow_html=True)
            else:
                st.info("Tendencia neutral o baja")
    else:
        st.info("No hay suficientes enfrentamientos recientes para validar tendencia.")

    # --- TABLA DE HISTORIAL ---
    st.subheader("Historial Directo")
    st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)

else:
    st.error("Error: Los archivos de datos no estan disponibles.")