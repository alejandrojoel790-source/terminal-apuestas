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
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; min-height: 200px; }
    .safe-bet { border-left: 8px solid #10b981; }
    .no-value { border-left: 8px solid #6b7280; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR JARVIS (LOGICA DE INGENIERIA) ---
class JarvisEngine:
    @staticmethod
    def american_to_decimal(momio):
        if momio is None or momio == 0: return None
        return (momio/100)+1 if momio > 0 else (100/abs(momio))+1

    @staticmethod
    def calcular_stats_ponderadas(df_equipo, es_local):
        if df_equipo.empty: return 0.001
        col = 'HG' if es_local else 'AG'
        # Ponderacion: 2026(x3), 2025(x2), 2024(x1)
        df_equipo['weight'] = df_equipo['Date'].dt.year.map({2026: 3, 2025: 2, 2024: 1}).fillna(1)
        return (df_equipo[col] * df_equipo['weight']).sum() / df_equipo['weight'].sum()

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
        return {"Win_H": prob_h, "Draw": prob_e, "Win_V": prob_v, "Over25": over25, "AmbosAn": btts}

    @staticmethod
    def kelly_fraccional(prob, cuota, bankroll, fraccion):
        if not cuota or cuota <= 1: return 0
        edge = (prob * cuota) - 1
        if edge <= 0: return 0
        return (edge / (cuota - 1)) * bankroll * fraccion

# --- 3. GESTION DE DATOS ---
@st.cache_data
def load_data(file):
    path = f"Data/{file}.csv"
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if df.empty: return "EMPTY"
            df['Date'] = pd.to_datetime(df['Date'])
            df['Home'] = df['Home'].str.strip()
            df['Away'] = df['Away'].str.strip()
            return df
        except: return "EMPTY"
    return None

# --- 4. PANEL DE CONTROL ---
st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    capital = st.number_input("Capital Total", min_value=0.0, value=1000.0, format="%g")
    
    riesgo_map = {"Agresivo (1/2 Kelly)": 0.5, "Moderado (1/4 Kelly)": 0.25, "Conservador (1/8 Kelly)": 0.125}
    fraccion_sel = st.select_slider("Perfil de Riesgo", options=list(riesgo_map.keys()), value="Moderado (1/4 Kelly)")
    
    min_edge = st.slider("Umbral de Valor (Edge %)", 0, 20, 15) / 100
    
    ligas = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026", "Liga MX": "LMX_2026"}
    liga_sel = st.selectbox("Competicion", list(ligas.keys()))

if liga_sel == "Liga MX":
    st.info("🚧 Estamos en proceso de añadir esta nueva liga. Los datos históricos estarán disponibles pronto.")
    st.stop()

df = load_data(ligas[liga_sel])

if isinstance(df, pd.DataFrame):
    equipos = sorted(df['Home'].unique())
    c1, c2 = st.columns(2)
    with c1: e_h = st.selectbox("Equipo Local", equipos)
    with c2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)
    
    # Calculos de Probabilidad
    m_h = JarvisEngine.calcular_stats_ponderadas(df[df['Home'] == e_h], True)
    m_v = JarvisEngine.calcular_stats_ponderadas(df[df['Away'] == e_v], False)
    stats = JarvisEngine.poisson_probability(m_h, m_v)

    # UI: Probabilidades
    st.markdown("---")
    st.subheader(f"Probabilidades Calculadas: {e_h} vs {e_v}")
    p_col = st.columns(5)
    p_col[0].metric("Gana Local", f"{stats['Win_H']*100:.1f}%")
    p_col[1].metric("Empate", f"{stats['Draw']*100:.1f}%")
    p_col[2].metric("Gana Visita", f"{stats['Win_V']*100:.1f}%")
    p_col[3].metric("+2.5 Goles", f"{stats['Over25']*100:.1f}%")
    p_col[4].metric("Ambos Anotan", f"{stats['AmbosAn']*100:.1f}%")

    # UI: Momios (Enteros Americanos)
    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales (+/-)")
    m_col = st.columns(5)
    with m_col[0]: m_h_raw = st.number_input(f"Momio {e_h}", value=None, step=1)
    with m_col[1]: m_d_raw = st.number_input("Momio Empate", value=None, step=1)
    with m_col[2]: m_v_raw = st.number_input(f"Momio {e_v}", value=None, step=1)
    with m_col[3]: m_o_raw = st.number_input("Momio +2.5", value=None, step=1)
    with m_col[4]: m_b_raw = st.number_input("Momio Ambos Anotan", value=None, step=1)

    # Conversiones
    m_l = JarvisEngine.american_to_decimal(m_h_raw)
    m_e = JarvisEngine.american_to_decimal(m_d_raw)
    m_vi = JarvisEngine.american_to_decimal(m_v_raw)
    m_o = JarvisEngine.american_to_decimal(m_o_raw)
    m_b = JarvisEngine.american_to_decimal(m_b_raw)

    # --- ANALISIS DE VALOR (5 COLUMNAS) ---
    if m_l and m_e and m_vi and m_o and m_b:
        st.markdown("---")
        st.subheader("Analisis de Valor y Stake")
        res_cols = st.columns(5)
        
        # Diccionario de mercados para iterar
        mercados = [
            ("Victoria Local", stats['Win_H'], m_l),
            ("Empate", stats['Draw'], m_e),
            ("Victoria Visita", stats['Win_V'], m_vi),
            ("Mas de 2.5 Goles", stats['Over25'], m_o),
            ("Ambos Anotan", stats['AmbosAn'], m_b)
        ]

        for i, (nombre, prob, cuota) in enumerate(mercados):
            edge = (prob * cuota) - 1
            with res_cols[i]:
                if edge > min_edge:
                    imp = JarvisEngine.kelly_fraccional(prob, cuota, capital, riesgo_map[fraccion_sel])
                    st.markdown(f"""<div class="bet-card safe-bet"><h3>{nombre}</h3><p>Edge: {edge*100:+.1f}%</p><p><b>Sugerido: ${int(round(imp))}</b></p></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="bet-card no-value"><h3>{nombre}</h3><p>Sin valor suficiente.</p></div>', unsafe_allow_html=True)

    # Historial
    st.markdown("---")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    st.subheader("Historial Directo (Cronologico)")
    st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
else:
    st.warning("Selecciona una liga con datos para comenzar.")
