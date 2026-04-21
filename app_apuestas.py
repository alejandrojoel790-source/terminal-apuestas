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
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CALCULO ANALITICO ---
class AnalysisEngine:
    @staticmethod
    def calcular_stats_completas(media_h, media_v):
        """Calcula probabilidades del mercado usando Distribucion de Poisson"""
        prob_h, prob_e, prob_v = 0, 0, 0
        over25 = 0
        btts = 0
        
        # Matriz de goles (0 a 8)
        for g_h in range(9):
            for g_v in range(9):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                
                # Resultado 1X2
                if g_h > g_v: prob_h += p
                elif g_h == g_v: prob_e += p
                else: prob_v += p
                
                # Mas de 2.5 goles
                if (g_h + g_v) > 2.5: over25 += p
                # Ambos Anotan
                if g_h > 0 and g_v > 0: btts += p
                    
        return {
            "Win_H": prob_h, "Draw": prob_e, "Win_V": prob_v,
            "Over25": over25, "BTTS": btts
        }

    @staticmethod
    def kelly_criterion(prob, cuota, bankroll):
        """Calcula la apuesta optima basada en el criterio de Kelly fraccional al 50%"""
        if cuota <= 1: return 0
        b = cuota - 1
        q = 1 - prob
        f = (b * prob - q) / b
        apuesta = max(0, f * bankroll * 0.5)
        return apuesta

# --- 3. GESTION DE DATOS ---
@st.cache_data
def cargar_datos(liga_file):
    ruta = f"Data/{liga_file}.csv"
    if os.path.exists(ruta):
        df = pd.read_csv(ruta)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return None

# --- 4. PANEL DE CONTROL ---
st.title("Prototipo de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    capital = st.number_input("Capital Total (Opcional)", min_value=0.0, value=1000.0, step=100.0)
    
    liga_opciones = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026"}
    seleccion_liga = st.selectbox("Competicion:", list(liga_opciones.keys()))
    archivo_liga = liga_opciones[seleccion_liga]

df = cargar_datos(archivo_liga)

if df is not None:
    equipos = sorted(df['Home'].unique())
    col1, col2 = st.columns(2)
    with col1: e_h = st.selectbox("Equipo Local", equipos)
    with col2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)

    # Filtrado de enfrentamientos directos historicos
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values('Date', ascending=False)
    
    # Calculo de promedios ofensivos y defensivos
    m_h = df[df['Home'] == e_h]['HG'].mean()
    m_v = df[df['Away'] == e_v]['AG'].mean()
    
    stats = AnalysisEngine.calcular_stats_completas(m_h, m_v)

    # --- 5. ANALISIS HISTORICO ---
    st.subheader("Enfrentamientos Directos")
    if not enfrentamientos.empty:
        st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']].head(5), use_container_width=True)
    else:
        st.info("No se registran enfrentamientos previos en la base de datos.")

    # --- 6. SISTEMA DE RECOMENDACIONES ---
    st.markdown("---")
    st.subheader("Analisis de Probabilidades y Apuesta")

    c1, c2 = st.columns(2)

    # Opcion Segura
    with c1:
        st.markdown('<div class="bet-card safe-bet">', unsafe_allow_html=True)
        st.markdown("### Opcion Segura")
        if stats['Win_H'] > 0.50:
            pick, prob = f"Victoria {e_h}", stats['Win_H']
        elif stats['BTTS'] > 0.60:
            pick, prob = "Ambos Anotan", stats['BTTS']
        else:
            pick, prob = f"Doble Oportunidad {e_h}", (stats['Win_H'] + stats['Draw'])
        
        st.write(f"**Pronostico:** {pick}")
        st.write(f"**Probabilidad:** {prob*100:.1f}%")
        # Cuota estimada para mercado seguro: 1.50
        monto = AnalysisEngine.kelly_criterion(prob, 1.50, capital)
        st.success(f"**Importe Sugerido:** ${monto:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Opcion Arriesgada
    with c2:
        st.markdown('<div class="bet-card risky-bet">', unsafe_allow_html=True)
        st.markdown("### Opcion Arriesgada")
        # Combinada: Gana Local + Over 2.5
        prob_comb = stats['Win_H'] * stats['Over25']
        st.write(f"**Pronostico:** {e_h} y Mas de 2.5 goles")
        st.write(f"**Probabilidad:** {prob_comb*100:.1f}%")
        # Cuota estimada para combinada: 3.50
        monto_r = AnalysisEngine.kelly_criterion(prob_comb, 3.50, capital)
        st.warning(f"**Importe Sugerido:** ${monto_r:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Seleccion Optima General
    st.markdown('<div class="bet-card" style="border-top: 5px solid #3b82f6;">', unsafe_allow_html=True)
    st.write("### Seleccion Optima")
    
    if stats['Over25'] > 0.65:
        mejor_pick, mejor_prob = "Mas de 2.5 goles", stats['Over25']
    elif stats['Win_H'] > 0.60:
        mejor_pick, mejor_prob = f"Victoria: {e_h}", stats['Win_H']
    else:
        mejor_pick, mejor_prob = "Ambos Anotan", stats['BTTS']

    st.info(f"Tras analizar {len(df)} registros, la opcion con mejor balance riesgo/beneficio es {mejor_pick} con una probabilidad del {mejor_prob*100:.1f}%.")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("Error: Los archivos de datos no estan disponibles.")