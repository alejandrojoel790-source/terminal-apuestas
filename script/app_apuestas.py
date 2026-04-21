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

# --- 2. BASE DE DATOS DE EQUIPOS (NOMBRES OFICIALES) ---
EQUIPOS_BUNDESLIGA = [
    "Bayer 04 Leverkusen", "VfB Stuttgart", "FC Bayern München", "RB Leipzig", 
    "Borussia Dortmund", "Eintracht Frankfurt", "TSG 1899 Hoffenheim", 
    "1. FC Heidenheim 1846", "SV Werder Bremen", "SC Freiburg", "FC Augsburg", 
    "VfL Wolfsburg", "1. FSV Mainz 05", "Borussia Mönchengladbach", 
    "1. FC Union Berlin", "VfL Bochum 1848", "FC St. Pauli", "Holstein Kiel"
]

EQUIPOS_CHAMPIONSHIP = [
    "Burnley FC", "Luton Town", "Sheffield United", "Leeds United", 
    "West Bromwich Albion", "Norwich City", "Hull City", "Middlesbrough FC", 
    "Coventry City", "Preston North End", "Bristol City", "Cardiff City", 
    "Swansea City", "Watford FC", "Sunderland AFC", "Stoke City", 
    "Queens Park Rangers", "Blackburn Rovers", "Sheffield Wednesday", 
    "Plymouth Argyle", "Portsmouth FC", "Derby County", "Oxford United", "Millwall FC"
]

# --- 3. MOTOR DE CALCULO ANALITICO ---
class AnalysisEngine:
    @staticmethod
    def calcular_stats_completas(media_h, media_v):
        """Calculo mediante Distribucion de Poisson"""
        # Evitar division por cero o valores nulos
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
    def kelly_criterion(prob, cuota, bankroll):
        """Calculo de Stake mediante Criterio de Kelly al 50%"""
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
    # Seleccion de lista segun la liga
    lista_equipos = EQUIPOS_BUNDESLIGA if seleccion_liga == "Bundesliga" else EQUIPOS_CHAMPIONSHIP
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: e_h = st.selectbox("Equipo Local", lista_equipos)
    with col_sel2: e_v = st.selectbox("Equipo Visitante", lista_equipos, index=1)

    # --- CALCULO DE PROBABILIDADES ---
    m_h = df[df['Home'] == e_h]['HG'].mean()
    m_v = df[df['Away'] == e_v]['AG'].mean()
    stats = AnalysisEngine.calcular_stats_completas(m_h, m_v)

    # --- SECCION: PROBABILIDADES CALCULADAS ---
    st.markdown("---")
    st.subheader("Probabilidades Calculadas")
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric(f"Gana {e_h}", f"{stats['Win_H']*100:.1f}%")
    p2.metric("Empate", f"{stats['Draw']*100:.1f}%")
    p3.metric(f"Gana {e_v}", f"{stats['Win_V']*100:.1f}%")
    p4.metric("Mas de 2.5", f"{stats['Over25']*100:.1f}%")
    p5.metric("Ambos Anotan", f"{stats['BTTS']*100:.1f}%")

    # --- INGRESO DE MOMIOS ---
    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales")
    c_m1, c_m2, c_m3, c_m4, c_m5 = st.columns(5)
    with c_m1: m_local = st.number_input(f"Momio {e_h}", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m2: m_empate = st.number_input("Momio Empate", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m3: m_visita = st.number_input(f"Momio {e_v}", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m4: m_over25 = st.number_input("Momio +2.5 Goles", min_value=1.0, value=None, format="%g", placeholder="0")
    with c_m5: m_btts = st.number_input("Momio Ambos Anotan", min_value=1.0, value=None, format="%g", placeholder="0")

    # --- ENFRENTAMIENTOS DIRECTOS (ORDEN DESCENDENTE) ---
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | 
                         ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    
    st.subheader("Enfrentamientos Directos")
    if not enfrentamientos.empty:
        st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
    else:
        st.info("No se registran enfrentamientos previos en la base de datos.")

    # --- ANALISIS FINAL DE APUESTA ---
    st.markdown("---")
    if all([m_local, m_empate, m_visita, m_over25, m_btts]):
        st.subheader("Analisis de Pronostico y Apuesta")
        res1, res2 = st.columns(2)

        with res1:
            pick, prob, cuota = (f"Victoria {e_h}", stats['Win_H'], m_local) if stats['Win_H'] > stats['BTTS'] else ("Ambos Anotan", stats['BTTS'], m_btts)
            st.markdown(f"""
                <div class="bet-card safe-bet">
                    <div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {prob*100}%; background-color: #10b981;"></div></div>
                    <h3>Opcion Segura</h3>
                    <p><b>Pronostico:</b> {pick}</p>
                    <p><b>Probabilidad:</b> {prob*100:.1f}%</p>
                    <div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold;">
                        Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob, cuota, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with res2:
            prob_c, cuota_c = stats['Win_H'] * stats['Over25'], m_local * m_over25 * 0.85 
            st.markdown(f"""
                <div class="bet-card risky-bet">
                    <div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {prob_c*100}%; background-color: #f59e0b;"></div></div>
                    <h3>Opcion Arriesgada</h3>
                    <p><b>Pronostico:</b> {e_h} y Mas de 2.5 goles</p>
                    <p><b>Probabilidad:</b> {prob_c*100:.1f}%</p>
                    <div style="background-color: #78350f; padding: 10px; border-radius: 8px; color: #f59e0b; font-weight: bold;">
                        Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(prob_c, cuota_c, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        ev_l, ev_o = (stats['Win_H'] * m_local) - 1, (stats['Over25'] * m_over25) - 1
        m_pick, m_prob, m_cuota = ("Mas de 2.5 goles", stats['Over25'], m_over25) if ev_o > ev_l else (f"Victoria: {e_h}", stats['Win_H'], m_local)
        st.markdown(f"""
            <div class="bet-card" style="border-top: 5px solid #3b82f6;">
                <div class="custom-progress-bg"><div class="custom-progress-fill" style="width: {m_prob*100}%; background-color: #3b82f6;"></div></div>
                <h3>Seleccion Optima</h3>
                <p style="color: #93c5fd;">Mejor ventaja matematica: <b>{m_pick}</b> con {m_prob*100:.1f}%.</p>
                <div style="background-color: #1e3a8a; padding: 10px; border-radius: 8px; color: #93c5fd; font-weight: bold;">
                    Importe Sugerido: ${int(round(AnalysisEngine.kelly_criterion(m_prob, m_cuota, capital)))}
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Ingresa los momios actuales para generar las recomendaciones.")
else:
    st.error("Error: Archivos de datos no detectados.")