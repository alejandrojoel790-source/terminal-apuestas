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
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; min-height: 180px; }
    .oportunidad-card { border-left: 8px solid #10b981; border-top: 2px solid #10b981; }
    .arriesgada-card { border-left: 8px solid #f59e0b; border-top: 2px solid #f59e0b; }
    
    .resultado-final-horizontal { 
        background-color: #262730; 
        padding: 30px; 
        border-radius: 15px; 
        border: 1px solid #4b5563; 
        border-left: 12px solid #8b5cf6; 
        margin-top: 20px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .monto-destacado {
        background-color: #4c1d95; 
        padding: 15px; 
        border-radius: 10px; 
        color: #c4b5fd; 
        font-weight: bold; 
        font-size: 24px;
        display: inline-block;
        margin-top: 10px;
    }
    .no-value { border-left: 8px solid #6b7280; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CALCULO ---
class BettingEngine:
    @staticmethod
    def american_to_decimal(momio):
        if momio is None or momio == 0: return 1.0
        return (momio/100)+1 if momio > 0 else (100/abs(momio))+1

    @staticmethod
    def calcular_stats_ponderadas(df_equipo, es_local):
        if df_equipo.empty: return 0.001
        col = 'HG' if es_local else 'AG'
        # Prioridad a datos recientes (2026)
        df_equipo['weight'] = df_equipo['Date'].dt.year.map({2026: 3, 2025: 2, 2024: 1}).fillna(1)
        return (df_equipo[col] * df_equipo['weight']).sum() / df_equipo['weight'].sum()

    @staticmethod
    def poisson_probability(media_h, media_v):
        res = {
            "Win_H": 0, "Draw": 0, "Win_V": 0, "AmbosAn": 0,
            "O05": 0, "O15": 0, "O25": 0, "O35": 0,
            "U05": 0, "U15": 0, "U25": 0, "U35": 0
        }
        for g_h in range(10):
            for g_v in range(10):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                total = g_h + g_v
                if g_h > g_v: res["Win_H"] += p
                elif g_h == g_v: res["Draw"] += p
                else: res["Win_V"] += p
                if g_h > 0 and g_v > 0: res["AmbosAn"] += p
                if total > 0.5: res["O05"] += p
                else: res["U05"] += p
                if total > 1.5: res["O15"] += p
                else: res["U15"] += p
                if total > 2.5: res["O25"] += p
                else: res["U25"] += p
                if total > 3.5: res["O35"] += p
                else: res["U35"] += p
        return res

    @staticmethod
    def kelly_fraccional(prob, cuota, bankroll, fraccion):
        if cuota <= 1: return 0
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
            df['Date'] = pd.to_datetime(df['Date'])
            df['Home'] = df['Home'].str.strip()
            df['Away'] = df['Away'].str.strip()
            return df
        except: return None
    return None

# --- 4. PANEL DE CONTROL ---
st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    ligas_dict = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026", "Liga MX": "LMX_2026"}
    liga_sel = st.selectbox("Ligas", list(ligas_dict.keys()))
    st.markdown("---")
    capital = st.number_input("Capital Total", min_value=0, value=1000, step=1, format="%d")
    st.markdown("---")
    st.subheader("Modo de Analisis")
    modo = st.radio(
        "Nivel de Precision:", 
        ["Sistema Normal", "Sistema Medio", "Sistema Muy Preciso"],
        help="Normal: Mayor volumen.\nPreciso: Filtro estricto de ventaja."
    )

    if modo == "Sistema Normal":
        fraccion_val, min_edge = 0.5, 0.05
    elif modo == "Sistema Medio":
        fraccion_val, min_edge = 0.25, 0.10
    else:
        fraccion_val, min_edge = 0.125, 0.18

    with st.expander("📚 Glosario Tecnico"):
        st.write("**Riesgo (Kelly):**")
        st.latex(r"f = \frac{Edge}{Cuota-1} \times \frac{1}{N}")
        st.write("Gestiona la seguridad del bankroll. Un riesgo de **8x** reduce la apuesta para proteger el capital.")
        st.write("**Edge (Ventaja):**")
        st.latex(r"Edge = (Prob \times Cuota) - 1")
        st.write("Representa la ventaja matematica real detectada sobre el casino.")

    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 3px solid #3b82f6; margin-top: 10px;">
        <small>Configuracion Activa:</small><br>
        <b>Riesgo:</b> {int(1/fraccion_val)}x Kelly (Seguridad)<br>
        <b>Filtro Edge:</b> {int(min_edge*100)}% (Calidad)
        </div>
    """, unsafe_allow_html=True)

if liga_sel == "Liga MX":
    st.info("🚧 Estamos en proceso de añadir esta nueva liga. Los datos históricos estarán disponibles pronto.")
    st.stop()

df = load_data(ligas_dict[liga_sel])

if isinstance(df, pd.DataFrame):
    equipos = sorted(df['Home'].unique())
    c1, c2 = st.columns(2)
    with c1: e_h = st.selectbox("Equipo Local", equipos)
    with c2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)
    
    m_h = BettingEngine.calcular_stats_ponderadas(df[df['Home'] == e_h], True)
    m_v = BettingEngine.calcular_stats_ponderadas(df[df['Away'] == e_v], False)
    stats = BettingEngine.poisson_probability(m_h, m_v)

    st.markdown("---")
    p_col = st.columns(5)
    p_col[0].metric(f"Gana {e_h}", f"{int(round(stats['Win_H']*100))}%")
    p_col[1].metric("Empate", f"{int(round(stats['Draw']*100))}%")
    p_col[2].metric(f"Gana {e_v}", f"{int(round(stats['Win_V']*100))}%")
    p_col[3].metric("+2.5 Goles", f"{int(round(stats['O25']*100))}%")
    p_col[4].metric("Ambos Anotan", f"{int(round(stats['AmbosAn']*100))}%")

    with st.expander("📊 Analisis Detallado de Goles (Over/Under)"):
        g1, g2, g3 = st.columns(3)
        g1.write(f"**Over 0.5:** {int(round(stats['O05']*100))}% | **Under 0.5:** {int(round(stats['U05']*100))}%")
        g2.write(f"**Over 1.5:** {int(round(stats['O15']*100))}% | **Under 1.5:** {int(round(stats['U15']*100))}%")
        g3.write(f"**Over 3.5:** {int(round(stats['O35']*100))}% | **Under 3.5:** {int(round(stats['U35']*100))}%")

    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales (+/-)")
    m_col = st.columns(5)
    with m_col[0]: m_h_raw = st.number_input(f"Momio {e_h}", value=0, step=1, format="%d")
    with m_col[1]: m_d_raw = st.number_input("Momio Empate", value=0, step=1, format="%d")
    with m_col[2]: m_v_raw = st.number_input(f"Momio {e_v}", value=0, step=1, format="%d")
    with m_col[3]: m_o_raw = st.number_input("Momio +2.5", value=0, step=1, format="%d")
    with m_col[4]: m_b_raw = st.number_input("Momio Ambos Anotan", value=0, step=1, format="%d")

    m_l = BettingEngine.american_to_decimal(m_h_raw)
    m_o_25 = BettingEngine.american_to_decimal(m_o_raw)

    if m_h_raw != 0:
        st.markdown("---")
        st.subheader(f"Estrategia sugerida - {modo}")
        rec1, rec2 = st.columns(2)
        
        with rec1:
            edge_l = (stats['Win_H'] * m_l) - 1
            if edge_l >= min_edge:
                monto = int(round(BettingEngine.kelly_fraccional(stats['Win_H'], m_l, capital, fraccion_val)))
                st.markdown(f'<div class="bet-card oportunidad-card"><h3>✅ Oportunidad</h3><p><b>Victoria {e_h}</b></p><div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold; font-size: 20px;">Monto sugerido: ${monto}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>✅ Oportunidad</h3><p>Sin ventaja clara actualmente.</p></div>', unsafe_allow_html=True)

        with rec2:
            prob_comb = stats['Win_H'] * stats['O25']
            cuota_comb = m_l * m_o_25 * 0.85
            if (prob_comb * cuota_comb) - 1 >= min_edge:
                monto = int(round(BettingEngine.kelly_fraccional(prob_comb, cuota_comb, capital, fraccion_val)))
                st.markdown(f'<div class="bet-card arriesgada-card"><h3>🔥 Arriesgada</h3><p><b>{e_h} y +2.5 Goles</b></p><div style="background-color: #78350f; padding: 10px; border-radius: 8px; color: #f59e0b; font-weight: bold; font-size: 20px;">Monto sugerido: ${monto}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>🔥 Arriesgada</h3><p>Combinada no rentable.</p></div>', unsafe_allow_html=True)

        st.markdown("---")
        
        todas = [
            {"n": f"Victoria {e_h}", "p": stats['Win_H']},
            {"n": f"Victoria {e_v}", "p": stats['Win_V']},
            {"n": "Mas de 0.5 Goles", "p": stats['O05']},
            {"n": "Mas de 1.5 Goles", "p": stats['O15']},
            {"n": "Mas de 2.5 Goles", "p": stats['O25']},
            {"n": "Mas de 3.5 Goles", "p": stats['O35']},
            {"n": "Menos de 1.5 Goles", "p": stats['U15']},
            {"n": "Menos de 2.5 Goles", "p": stats['U25']},
            {"n": "Menos de 3.5 Goles", "p": stats['U35']},
            {"n": "Ambos Anotan", "p": stats['AmbosAn']}
        ]
        
        segura = max(todas, key=lambda x: x['p'])
        monto_final = int(capital * 0.05) if segura['p'] > 0.7 else int(capital * 0.02)

        st.markdown(f"""
            <div class="resultado-final-horizontal">
                <h2 style="color: #c4b5fd; margin: 0;">📊 Mayor Probabilidad (Resultado Final)</h2>
                <p style="font-size: 18px; margin: 0;">Analisis completo de mercados Over/Under y Ganador:</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="font-size: 26px; color: white; margin: 5px 0;"><b>{segura['n']}</b></p>
                        <p style="font-size: 16px; color: #9ca3af; margin: 0;">Confianza estadistica: {int(round(segura['p']*100))}%</p>
                    </div>
                    <div class="monto-destacado">
                        Inversion sugerida: ${monto_final}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    st.subheader("Historial Directo")
    st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
