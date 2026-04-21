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
    .stMetric { 
        background-color: #1f2937; 
        padding: 20px; 
        border-radius: 10px; 
        border-top: 4px solid #3b82f6;
        text-align: center;
    }
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
        "Birmingham City FC", "Blackburn Rovers FC", "Bristol City", "Burnley FC", "Cardiff City", 
        "Coventry City", "Derby County", "Hull City", "Leeds United", "Luton Town", 
        "Middlesbrough", "Millwall FC", "Norwich City", "Oxford United", "Plymouth Argyle", 
        "Portsmouth FC", "Preston North End", "Queens Park Rangers", "Sheffield United", 
        "Sheffield Wednesday", "Stoke City", "Sunderland AFC", "Swansea City", "Watford FC", 
        "West Bromwich Albion"
    ]
}

# --- 3. MOTOR DE CALCULO ANALITICO ---
class AnalysisEngine:
    @staticmethod
    def calcular_stats_completas(media_h, media_v):
        prob_h, prob_e, prob_v = 0, 0, 0
        over25 = 0
        btts = 0
        # Rango de 0 a 11 goles para cubrir todas las posibilidades reales
        for g_h in range(12):
            for g_v in range(12):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                if g_h > g_v: prob_h += p
                elif g_h == g_v: prob_e += p
                else: prob_v += p
                if (g_h + g_v) > 2.5: over25 += p
                if g_h > 0 and g_v > 0: btts += p
        return {
            "Win_H": prob_h, 
            "Draw": prob_e, 
            "Win_V": prob_v, 
            "Over25": over25, 
            "BTTS": btts
        }

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

# --- 5. INTERFAZ PRINCIPAL ---
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

    # --- CALCULO INMEDIATO DE PROBABILIDADES ---
    # Filtrar datos para obtener las medias de goles
    data_h = df[df['Home'] == e_h]
    data_v = df[df['Away'] == e_v]
    
    m_h = data_h['HG'].mean() if not data_h.empty else 0.0
    m_v = data_v['AG'].mean() if not data_v.empty else 0.0
    
    # Ejecutar motor de Poisson
    stats = AnalysisEngine.calcular_stats_completas(m_h, m_v)

    # --- SECCION VISIBLE DE PROBABILIDADES ---
    st.markdown("---")
    st.header("Dashboard de Probabilidades Calculadas")
    
    # Fila 1: Resultados del Partido
    st.subheader("Resultado Final (1X2)")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Victoria {e_h}", f"{stats['Win_H']*100:.2f}%")
    c2.metric("Empate", f"{stats['Draw']*100:.2f}%")
    c3.metric(f"Victoria {e_v}", f"{stats['Win_V']*100:.2f}%")
    
    # Fila 2: Mercados Adicionales
    st.subheader("Mercados de Goles")
    c4, c5 = st.columns(2)
    c4.metric("Mas de 2.5 Goles", f"{stats['Over25']*100:.2f}%")
    c5.metric("Ambos Anotan (BTTS)", f"{stats['BTTS']*100:.2f}%")

    st.markdown("---")
    
    # --- ENTRADA DE MOMIOS ---
    st.subheader("Ingreso de Momios Actuales")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1: m_local = st.number_input(f"Momio {e_h}", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col2: m_empate = st.number_input("Momio Empate", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col3: m_visita = st.number_input(f"Momio {e_v}", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col4: m_over25 = st.number_input("Momio +2.5 Goles", min_value=1.0, value=None, format="%g", placeholder="0")
    with m_col5: m_btts = st.number_input("Momio Ambos Anotan", min_value=1.0, value=None, format="%g", placeholder="0")

    # --- HISTORIAL H2H ---
    st.subheader("Enfrentamientos Directos")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | 
                         ((df['Home'] == e_v) & (df['Away'] == e_h))]
    enfrentamientos = enfrentamientos.sort_values(by='Date', ascending=False)

    if not enfrentamientos.empty:
        st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay historial registrado entre {e_h} y {e_v}.")

    # --- RECOMENDACIONES FINALES ---
    st.markdown("---")
    if all([m_local, m_empate, m_visita, m_over25, m_btts]):
        st.header("Analisis de Apuesta Sugerida")
        res_col1, res_col2, res_col3 = st.columns(3)

        with res_col1:
            pick_s = f"Victoria {e_h}" if stats['Win_H'] > stats['BTTS'] else "Ambos Anotan"
            prob_s = stats['Win_H'] if stats['Win_H'] > stats['BTTS'] else stats['BTTS']
            cuota_s = m_local if stats['Win_H'] > stats['BTTS'] else m_btts
            
            st.markdown(f"""
                <div class="bet-card safe-bet">
                    <h3>Opcion Principal</h3>
                    <p><b>Pronostico:</b> {pick_s}</p>
                    <p><b>Confianza:</b> {prob_s*100:.1f}%</p>
                    <div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold;">
                        Stake Kelly: ${int(round(AnalysisEngine.kelly_criterion(prob_s, cuota_s, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with res_col2:
            st.markdown(f"""
                <div class="bet-card draw-bet">
                    <h3>Opcion Empate</h3>
                    <p><b>Pronostico:</b> Empate</p>
                    <p><b>Confianza:</b> {stats['Draw']*100:.1f}%</p>
                    <div style="background-color: #1e1b4b; padding: 10px; border-radius: 8px; color: #a5b4fc; font-weight: bold;">
                        Stake Kelly: ${int(round(AnalysisEngine.kelly_criterion(stats['Draw'], m_empate, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with res_col3:
            prob_c = stats['Win_H'] * stats['Over25']
            st.markdown(f"""
                <div class="bet-card risky-bet">
                    <h3>Opcion Arriesgada</h3>
                    <p><b>Pronostico:</b> {e_h} + Over 2.5</p>
                    <p><b>Confianza:</b> {prob_c*100:.1f}%</p>
                    <div style="background-color: #78350f; padding: 10px; border-radius: 8px; color: #f59e0b; font-weight: bold;">
                        Stake Kelly: ${int(round(AnalysisEngine.kelly_criterion(prob_c, m_local*m_over25*0.8, capital)))}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Completa todos los momios para ver las sugerencias de importe.")
else:
    st.error("Error critico: No se pudieron cargar los archivos de datos en la carpeta Data.")