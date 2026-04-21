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
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; }
    .safe-bet { border-left: 8px solid #10b981; }
    .risky-bet { border-left: 8px solid #f59e0b; }
    .draw-bet { border-left: 8px solid #6366f1; }
    
    .custom-progress-bg {
        background-color: #374151;
        border-radius: 10px;
        height: 12px;
        width: 100%;
        margin-bottom: 15px;
        overflow: hidden;
    }
    .custom-progress-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LISTAS OFICIALES DE EQUIPOS ---
EQUIPOS_POR_LIGA = {
    "Bundesliga": [
        "1. FC Heidenheim 1846", "1. FC Köln", "1. FC Union Berlin", "1. FSV Mainz 05",
        "Bayer 04 Leverkusen", "Borussia Dortmund", "Borussia Mönchengladbach",
        "Eintracht Frankfurt", "FC Augsburg", "FC Bayern München", "FC St. Pauli",
        "Hamburger SV", "RB Leipzig", "SC Freiburg", "SV Werder Bremen",
        "TSG 1899 Hoffenheim", "VfB Stuttgart", "VfL Wolfsburg"
    ],
    "Championship": [
        "Blackburn Rovers", "Bristol City", "Burnley FC", "Cardiff City", "Coventry City",
        "Derby County", "Hull City", "Leeds United", "Luton Town", "Middlesbrough",
        "Millwall FC", "Norwich City", "Oxford United", "Plymouth Argyle", "Portsmouth FC",
        "Preston North End", "Queens Park Rangers", "Sheffield United", "Sheffield Wednesday",
        "Stoke City", "Sunderland AFC", "Swansea City", "Watford FC", "West Bromwich Albion"
    ]
}

# --- 3. MOTOR DE CALCULO ANALITICO ---
class AnalysisEngine:
    @staticmethod
    def calcular_stats_completas(media_h, media_v):
        prob_h, prob_e, prob_v = 0, 0, 0
        over25 = 0
        btts = 0
        for g_h in range(12):
            for g_v in range(12):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                if g_h > g_v: prob_h += p
                elif g_h == g_v: prob_e += p
                else: prob_v += p
                if (g_h + g_v) > 2.5: over25 += p
                if g_h > 0 and g_v > 0: btts += p
        return {"Win_H": prob_h, "Draw": prob_e, "Win_V": prob_v, "Over25": over25, "BTTS": btts}

    @staticmethod
    def kelly_criterion(prob, cuota, bankroll):
        if cuota is None or cuota <= 1: return 0
        b = cuota - 1
        q = 1 - prob
        f = (b * prob - q) / b
        return max(0, f * bankroll * 0.5)

# --- 4. GESTION DE DATOS ---
@st.cache_data
def cargar_datos(liga_file):
    ruta = f"Data/{liga_file}.csv"
    if os.path.exists(ruta):
        df = pd.read_csv(ruta)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return None

# --- 5. PANEL DE CONTROL ---
st.title("Prototipo de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    capital = st.number_input("Capital Total", min_value=0.0, value=1000.0, format="%g")
    liga_opciones = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026"}
    seleccion_liga = st.selectbox("Competicion:", list(liga_opciones.keys()))
    archivo_liga = liga_opciones[seleccion_liga]

df = cargar_datos(archivo_liga)

if df is not None:
    lista_equipos = EQUIPOS_POR_LIGA[seleccion_liga]
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: 
        e_h = st.selectbox("Equipo Local", lista_equipos)
    with col_sel2: 
        e_v = st.selectbox("Equipo Visitante", lista_equipos, index=1)

    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales")
    c_m1, c_m2, c_m3, c_m4, c_m5 = st.columns(5)
    with c_m1: m_local = st.number_input(f"Momio {e_h}", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m2: m_empate = st.number_input("Momio Empate", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m3: m_visita = st.number_input(f"Momio {e_v}", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m4: m_over25 = st.number_input("Momio +2.5 Goles", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m5: m_btts = st.number_input("Momio Ambos Anotan", min_value=1.0, value=None, format="%g", placeholder="0")

    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | 
                         ((df['Home'] == e_v) & (df['Away'] == e_h))]
    
    enfrentamientos = enfrentamientos.sort_values(by='Date', ascending=False)
    
    m_h = df[df['Home'] == e_h]['HG'].mean() if not df[df['Home'] == e_h].empty else 0
    m_v = df[df['Away'] == e_v]['AG'].mean() if not df[df['Away'] == e_v].empty else 0
    stats = AnalysisEngine.calcular_stats_completas(m_h, m_v)

    st.subheader("Enfrentamientos Directos")
    if not enfrentamientos.empty:
        st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
    else:
        st.info(f"No se registran enfrentamientos previos entre {e_h} y {e_v}.")

    st.markdown("---")
    
    if all([m_local, m_empate, m_visita, m_over25, m_btts]):
        st.subheader("Analisis de Probabilidades y Apuesta")
        res1, res2, res3 = st.columns(3)

        # Opcion Local / BTTS
        with res1:
            if stats['Win_H'] > stats['BTTS']:
                pick, prob, cuota_usada = f"Victoria {e_h}", stats['Win_H'], m_local
            else:
                pick, prob, cuota_usada = "Ambos Anotan", stats['BTTS'], m_btts
            
            st.markdown(f"""
                <div class="bet-card safe-bet">
                    <div class="custom-progress-bg">
                        <div class="custom-progress-fill" style="width: {prob*100}%; background-color: #10b981;"></div>
                    </div>
                    <h3>Opcion Principal</h3>
                    <p><b>Pronostico:</b> {pick}</p>
                    <p><b>Probabilidad:</b> {prob*100:.1f}%</p>
                    <div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold;">
                        Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob, cuota_usada, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Opcion Empate (Nueva)
        with res2:
            prob_e = stats['Draw']
            st.markdown(f"""
                <div class="bet-card draw-bet">
                    <div class="custom-progress-bg">
                        <div class="custom-progress-fill" style="width: {prob_e*100}%; background-color: #6366f1;"></div>
                    </div>
                    <h3>Opcion Empate</h3>
                    <p><b>Pronostico:</b> Empate</p>
                    <p><b>Probabilidad:</b> {prob_e*100:.1f}%</p>
                    <div style="background-color: #1e1b4b; padding: 10px; border-radius: 8px; color: #a5b4fc; font-weight: bold;">
                        Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob_e, m_empate, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Opcion Arriesgada
        with res3:
            prob_comb = stats['Win_H'] * stats['Over25']
            cuota_comb = m_local * m_over25 * 0.85 
            
            st.markdown(f"""
                <div class="bet-card risky-bet">
                    <div class="custom-progress-bg">
                        <div class="custom-progress-fill" style="width: {prob_comb*100}%; background-color: #f59e0b;"></div>
                    </div>
                    <h3>Opcion Arriesgada</h3>
                    <p><b>Pronostico:</b> {e_h} y Mas de 2.5 goles</p>
                    <p><b>Probabilidad:</b> {prob_comb*100:.1f}%</p>
                    <div style="background-color: #78350f; padding: 10px; border-radius: 8px; color: #f59e0b; font-weight: bold;">
                        Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob_comb, cuota_comb, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Seleccion Optima (Cálculo comparativo de EV)
        ev_local = (stats['Win_H'] * m_local) - 1
        ev_empate = (stats['Draw'] * m_empate) - 1
        ev_over = (stats['Over25'] * m_over25) - 1
        
        # Diccionario para encontrar el EV mas alto
        opciones_ev = {
            f"Victoria: {e_h}": (ev_local, stats['Win_H'], m_local),
            "Empate": (ev_empate, stats['Draw'], m_empate),
            "Mas de 2.5 goles": (ev_over, stats['Over25'], m_over25)
        }
        
        mejor_pick = max(opciones_ev, key=lambda k: opciones_ev[k][0])
        mejor_ev, mejor_prob, mejor_cuota = opciones_ev[mejor_pick]

        monto_optimo = AnalysisEngine.kelly_criterion(mejor_prob, mejor_cuota, capital)

        st.markdown(f"""
            <div class="bet-card" style="border-top: 5px solid #3b82f6;">
                <div class="custom-progress-bg">
                    <div class="custom-progress-fill" style="width: {mejor_prob*100}%; background-color: #3b82f6;"></div>
                </div>
                <h3>Seleccion Optima</h3>
                <p style="color: #93c5fd;">Analisis completado: la opcion con mejor balance riesgo/beneficio es <b>{mejor_pick}</b> con una probabilidad del {mejor_prob*100:.1f}%.</p>
                <div style="background-color: #1e3a8a; padding: 10px; border-radius: 8px; color: #93c5fd; font-weight: bold;">
                    Importe Sugerido: ${int(round(monto_optimo))}
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Ingresa los momios actuales para generar las recomendaciones.")
else:
    st.error(f"Error: No se encontro el archivo 'Data/{archivo_liga}.csv'.")