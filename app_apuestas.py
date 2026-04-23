import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import os

# --- 1. CONFIGURACION ---
st.set_page_config(page_title="Sistema de Apuestas", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; }
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; }
    .safe-bet { border-left: 8px solid #10b981; }
    .no-value { border-left: 8px solid #6b7280; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR ANALITICO ---
class JarvisEngine:
    @staticmethod
    def american_to_decimal(momio):
        if momio is None or momio == 0: return None
        return (momio/100)+1 if momio > 0 else (100/abs(momio))+1

    @staticmethod
    def calcular_stats_ponderadas(df_equipo, es_local):
        if df_equipo.empty: return 0.001
        col_goles = 'HG' if es_local else 'AG'
        # Ponderacion temporal: 2026 tiene mas peso
        df_equipo['weight'] = df_equipo['Date'].dt.year.map({2026: 3, 2025: 2, 2024: 1}).fillna(1)
        promedio = (df_equipo[col_goles] * df_equipo['weight']).sum() / df_equipo['weight'].sum()
        return max(0.001, promedio)

    @staticmethod
    def poisson_probability(media_h, media_v):
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
    def kelly_fraccional(prob, cuota, bankroll, fraccion):
        if not cuota or cuota <= 1: return 0
        edge = (prob * cuota) - 1
        if edge <= 0: return 0
        return (edge / (cuota - 1)) * bankroll * fraccion

# --- 3. GESTION DE DATOS ---
@st.cache_data
def cargar_datos(liga_file):
    ruta = f"Data/{liga_file}.csv"
    if os.path.exists(ruta):
        df = pd.read_csv(ruta)
        df['Date'] = pd.to_datetime(df['Date'])
        # Limpieza: quitamos espacios extra por si acaso
        df['Home'] = df['Home'].str.strip()
        df['Away'] = df['Away'].str.strip()
        return df
    return None

# --- 4. PANEL DE CONTROL ---
st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    capital = st.number_input("Capital Total", min_value=0.0, value=1000.0, format="%g")
    
    riesgo_map = {"Agresivo (1/2 Kelly)": 0.5, "Moderado (1/4 Kelly)": 0.25, "Conservador (1/8 Kelly)": 0.125}
    fraccion_sel = st.select_slider("Perfil de Riesgo", options=list(riesgo_map.keys()), value="Moderado (1/4 Kelly)")
    fraccion_val = riesgo_map[fraccion_sel]
    
    min_edge = st.slider("Umbral de Valor (Edge %)", 0, 15, 5) / 100
    
    # Añadi tambien la LMX por si quieres usar el archivo que vi en tu GitHub
    ligas = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026", "Liga MX": "LMX_2026"}
    liga_sel = st.selectbox("Competicion", list(ligas.keys()))

df = cargar_datos(ligas[liga_sel])

if df is not None:
    # --- AUTOMATIZACION DE EQUIPOS ---
    # Extraemos los nombres reales que vienen en TU archivo CSV
    equipos_reales = sorted(df['Home'].unique())
    
    c1, c2 = st.columns(2)
    with c1: e_h = st.selectbox("Equipo Local", equipos_reales)
    with c2: e_v = st.selectbox("Equipo Visitante", equipos_reales, index=1)
    
    # Calculos
    media_h = JarvisEngine.calcular_stats_ponderadas(df[df['Home'] == e_h], True)
    media_v = JarvisEngine.calcular_stats_ponderadas(df[df['Away'] == e_v], False)
    stats = JarvisEngine.poisson_probability(media_h, media_v)

    # UI Probabilidades
    st.markdown("---")
    st.subheader(f"Probabilidades: {e_h} vs {e_v}")
    p_col = st.columns(5)
    p_col[0].metric("Gana Local", f"{stats['Win_H']*100:.1f}%")
    p_col[1].metric("Empate", f"{stats['Draw']*100:.1f}%")
    p_col[2].metric("Gana Visita", f"{stats['Win_V']*100:.1f}%")
    p_col[3].metric("+2.5 Goles", f"{stats['Over25']*100:.1f}%")
    p_col[4].metric("Ambos Anotan", f"{stats['BTTS']*100:.1f}%")

    # Entrada de Momios
    st.markdown("---")
    st.subheader("Entrada de Momios (+/-)")
    m_col = st.columns(5)
    with m_col[0]: m_h_raw = st.number_input(f"Momio {e_h}", value=None, step=1)
    with m_col[1]: m_d_raw = st.number_input("Momio Empate", value=None, step=1)
    with m_col[2]: m_v_raw = st.number_input(f"Momio {e_v}", value=None, step=1)
    with m_col[3]: m_o_raw = st.number_input("Momio +2.5", value=None, step=1)
    with m_col[4]: m_b_raw = st.number_input("Momio BTTS", value=None, step=1)

    # Conversiones
    m_l = JarvisEngine.american_to_decimal(m_h_raw)
    m_o = JarvisEngine.american_to_decimal(m_o_raw)

    # Analisis de Valor
    if m_l and m_o:
        st.markdown("---")
        st.subheader("Analisis de Valor")
        res1, res2 = st.columns(2)
        
        edge_local = (stats['Win_H'] * m_l) - 1
        edge_over = (stats['Over25'] * m_o) - 1

        with res1:
            if edge_local > min_edge:
                imp = JarvisEngine.kelly_fraccional(stats['Win_H'], m_l, capital, fraccion_val)
                st.markdown(f'<div class="bet-card safe-bet"><h3>Victoria Local</h3><p>Edge: {edge_local*100:+.1f}%</p><p><b>Sugerido: ${int(round(imp))}</b></p></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>Victoria Local</h3><p>Sin valor.</p></div>', unsafe_allow_html=True)

        with res2:
            if edge_over > min_edge:
                imp_o = JarvisEngine.kelly_fraccional(stats['Over25'], m_o, capital, fraccion_val)
                st.markdown(f'<div class="bet-card safe-bet"><h3>Mas de 2.5</h3><p>Edge: {edge_over*100:+.1f}%</p><p><b>Sugerido: ${int(round(imp_o))}</b></p></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>Mas de 2.5</h3><p>Sin valor.</p></div>', unsafe_allow_html=True)

    # Historial
    st.markdown("---")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    st.subheader("Historial Directo")
    if not enfrentamientos.empty:
        st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
    else:
        st.warning(f"No se encontraron enfrentamientos previos entre {e_h} y {e_v} en este archivo.")
else:
    st.error("Archivo no encontrado.")
