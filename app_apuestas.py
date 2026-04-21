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
        prob_h, prob_e, prob_v = 0, 0, 0
        over25 = 0
        btts = 0
        
        for g_h in range(9):
            for g_v in range(9):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                if g_h > g_v: prob_h += p
                elif g_h == g_v: prob_e += p
                else: prob_v += p
                if (g_h + g_v) > 2.5: over25 += p
                if g_h > 0 and g_v > 0: btts += p
                    
        return {
            "Win_H": prob_h, "Draw": prob_e, "Win_V": prob_v,
            "Over25": over25, "BTTS": btts
        }

    @staticmethod
    def kelly_criterion(prob, cuota, bankroll):
        if cuota <= 1: return 0
        # Formula de Kelly: f = (bp - q) / b
        b = cuota - 1
        q = 1 - prob
        f = (b * prob - q) / b
        # Kelly fraccional al 50% para gestion conservadora
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
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: e_h = st.selectbox("Equipo Local", equipos)
    with col_sel2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)

    # --- NUEVA SECCION: ENTRADA DE MOMIOS ---
    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales")
    c_m1, c_m2, c_m3, c_m4, c_m5 = st.columns(5)
    with c_m1: m_local = st.number_input(f"Momio {e_h}", min_value=1.0, value=2.0, step=0.1)
    with c_m2: m_empate = st.number_input("Momio Empate", min_value=1.0, value=3.4, step=0.1)
    with c_m3: m_visita = st.number_input(f"Momio {e_v}", min_value=1.0, value=3.0, step=0.1)
    with c_m4: m_over25 = st.number_input("Momio +2.5 Goles", min_value=1.0, value=1.8, step=0.1)
    with c_m5: m_btts = st.number_input("Momio Ambos Anotan", min_value=1.0, value=1.7, step=0.1)

    # Filtrado y Calculos
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values('Date', ascending=False)
    m_h = df[df['Home'] == e_h]['HG'].mean()
    m_v = df[df['Away'] == e_v]['AG'].mean()
    stats = AnalysisEngine.calcular_stats_completas(m_h, m_v)

    # --- 5. ANALISIS HISTORICO ---
    st.subheader("Enfrentamientos Directos")
    if not enfrentamientos.empty:
        st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']].head(5), use_container_width=True)
    else:
        st.info("No se registran enfrentamientos previos.")

    # --- 6. RESULTADOS DEL ANALISIS ---
    st.markdown("---")
    st.subheader("Analisis de Probabilidades y Apuesta")

    res1, res2 = st.columns(2)

    # Opcion Segura
    with res1:
        st.markdown('<div class="bet-card safe-bet">', unsafe_allow_html=True)
        st.markdown("### Opcion Segura")
        # Logica: Elegir entre victoria local o ambos anotan segun probabilidad
        if stats['Win_H'] > stats['BTTS']:
            pick, prob, cuota_usada = f"Victoria {e_h}", stats['Win_H'], m_local
        else:
            pick, prob, cuota_usada = "Ambos Anotan", stats['BTTS'], m_btts
        
        st.write(f"**Pronostico:** {pick}")
        st.write(f"**Probabilidad:** {prob*100:.1f}%")
        monto = AnalysisEngine.kelly_criterion(prob, cuota_usada, capital)
        st.success(f"**Importe Sugerido:** ${monto:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Opcion Arriesgada
    with res2:
        st.markdown('<div class="bet-card risky-bet">', unsafe_allow_html=True)
        st.markdown("### Opcion Arriesgada")
        # Combinada: Gana Local y +2.5 goles
        prob_comb = stats['Win_H'] * stats['Over25']
        cuota_comb = m_local * m_over25 * 0.8 # Ajuste estimado de cuota combinada
        st.write(f"**Pronostico:** {e_h} y Mas de 2.5 goles")
        st.write(f"**Probabilidad:** {prob_comb*100:.1f}%")
        monto_r = AnalysisEngine.kelly_criterion(prob_comb, cuota_comb, capital)
        st.warning(f"**Importe Sugerido:** ${monto_r:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Seleccion Optima
    st.markdown('<div class="bet-card" style="border-top: 5px solid #3b82f6;">', unsafe_allow_html=True)
    st.write("### Seleccion Optima")
    
    # Calculo de valor esperado (EV) para decidir la mejor opcion
    ev_local = (stats['Win_H'] * m_local) - 1
    ev_over = (stats['Over25'] * m_over25) - 1
    
    if ev_over > ev_local:
        mejor_pick, mejor_prob = "Mas de 2.5 goles", stats['Over25']
    else:
        mejor_pick, mejor_prob = f"Victoria: {e_h}", stats['Win_H']

    st.info(f"Tras analizar los momios ingresados, la opcion con mayor valor esperado es {mejor_pick} con una probabilidad del {mejor_prob*100:.1f}%.")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("Error: Los archivos de datos no estan disponibles.")