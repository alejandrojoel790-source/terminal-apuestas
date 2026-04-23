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
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; min-height: 220px; }
    .optima-card { border-left: 8px solid #3b82f6; border-top: 2px solid #3b82f6; }
    .oportunidad-card { border-left: 8px solid #10b981; border-top: 2px solid #10b981; }
    .arriesgada-card { border-left: 8px solid #f59e0b; border-top: 2px solid #f59e0b; }
    .no-value { border-left: 8px solid #6b7280; opacity: 0.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR JARVIS ---
class JarvisEngine:
    @staticmethod
    def american_to_decimal(momio):
        if momio is None or momio == 0: return None
        return (momio/100)+1 if momio > 0 else (100/abs(momio))+1

    @staticmethod
    def calcular_stats_ponderadas(df_equipo, es_local):
        if df_equipo.empty: return 0.001
        col = 'HG' if es_local else 'AG'
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

# --- 4. PANEL DE CONTROL (ORDENADO) ---
st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    
    # 1. Ligas hasta arriba
    ligas = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026", "Liga MX": "LMX_2026"}
    liga_sel = st.selectbox("Ligas", list(ligas.keys()))
    
    st.markdown("---")
    
    # 2. Capital debajo de ligas
    capital = st.number_input("Capital Total", min_value=0.0, value=1000.0, format="%g")
    
    st.markdown("---")
    
    # 3. Modo de análisis y lo demás
    st.subheader("Modo de Analisis")
    modo = st.radio(
        "Nivel de Precision:",
        ["Sistema Normal", "Sistema Medio", "Sistema Muy Preciso"]
    )

    if modo == "Sistema Normal":
        fraccion_val, min_edge = 0.5, 0.05
    elif modo == "Sistema Medio":
        fraccion_val, min_edge = 0.25, 0.10
    else:
        fraccion_val, min_edge = 0.125, 0.18

    with st.expander("📚 Glosario Tecnico"):
        st.write("**Riesgo (Kelly):** Define la seguridad de tu bankroll.")
        st.write("**Edge (Ventaja):** Diferencia estadística a tu favor.")

    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 3px solid #3b82f6; margin-top: 10px;">
        <small>Configuracion Activa:</small><br>
        <b>Riesgo:</b> {int(1/fraccion_val)}x Kelly<br>
        <b>Filtro Edge:</b> {int(min_edge*100)}%
        </div>
    """, unsafe_allow_html=True)

# --- LOGICA DE EJECUCION ---
if liga_sel == "Liga MX":
    st.info("🚧 Estamos en proceso de añadir esta nueva liga. Los datos históricos estarán disponibles pronto.")
    st.stop()

df = load_data(ligas[liga_sel])

if isinstance(df, pd.DataFrame):
    equipos = sorted(df['Home'].unique())
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: e_h = st.selectbox("Equipo Local", equipos)
    with c_sel2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)
    
    # Calculos
    m_h = JarvisEngine.calcular_stats_ponderadas(df[df['Home'] == e_h], True)
    m_v = JarvisEngine.calcular_stats_ponderadas(df[df['Away'] == e_v], False)
    stats = JarvisEngine.poisson_probability(m_h, m_v)

    # UI: Probabilidades
    st.markdown("---")
    p_col = st.columns(5)
    p_col[0].metric(f"Gana {e_h}", f"{stats['Win_H']*100:.1f}%")
    p_col[1].metric("Empate", f"{stats['Draw']*100:.1f}%")
    p_col[2].metric(f"Gana {e_v}", f"{stats['Win_V']*100:.1f}%")
    p_col[3].metric("+2.5 Goles", f"{stats['Over25']*100:.1f}%")
    p_col[4].metric("Ambos Anotan", f"{stats['AmbosAn']*100:.1f}%")

    # UI: Momios
    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales (+/-)")
    m_col = st.columns(5)
    with m_col[0]: m_h_raw = st.number_input(f"Momio {e_h}", value=None, step=1)
    with m_col[1]: m_d_raw = st.number_input("Momio Empate", value=None, step=1)
    with m_col[2]: m_v_raw = st.number_input(f"Momio {e_v}", value=None, step=1)
    with m_col[3]: m_o_raw = st.number_input("Momio +2.5", value=None, step=1)
    with m_col[4]: m_b_raw = st.number_input("Momio Ambos Anotan", value=None, step=1)

    m_l = JarvisEngine.american_to_decimal(m_h_raw)
    m_e = JarvisEngine.american_to_decimal(m_d_raw)
    m_vi = JarvisEngine.american_to_decimal(m_v_raw)
    m_o = JarvisEngine.american_to_decimal(m_o_raw)
    m_b = JarvisEngine.american_to_decimal(m_b_raw)

    if m_l and m_e and m_vi and m_o and m_b:
        st.markdown("---")
        st.subheader(f"Estrategia sugerida - {modo}")
        
        mercados = [
            {"name": f"Victoria {e_h}", "prob": stats['Win_H'], "odd": m_l},
            {"name": "Empate", "prob": stats['Draw'], "odd": m_e},
            {"name": f"Victoria {e_v}", "prob": stats['Win_V'], "odd": m_vi},
            {"name": "Mas de 2.5 Goles", "prob": stats['Over25'], "odd": m_o},
            {"name": "Ambos Anotan", "prob": stats['AmbosAn'], "odd": m_b}
        ]
        
        validos = [m for m in mercados if (m['prob'] * m['odd']) - 1 >= min_edge]
        rec1, rec2, rec3 = st.columns(3)

        with rec1:
            if validos:
                optima = max(validos, key=lambda x: (x['prob'] * x['odd']) - 1)
                edge_opt = (optima['prob'] * optima['odd']) - 1
                imp = JarvisEngine.kelly_fraccional(optima['prob'], optima['odd'], capital, fraccion_val)
                st.markdown(f"""<div class="bet-card optima-card"><h3>🌟 Mas Optima</h3><p><b>{optima['name']}</b></p>
                <p>Edge: {edge_opt*100:+.1f}%</p>
                <div style="background-color: #1e3a8a; padding: 10px; border-radius: 8px; color: #93c5fd; font-weight: bold;">Monto sugerido: ${int(round(imp))}</div></div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>🌟 Mas Optima</h3><p>Sin valor bajo este umbral.</p></div>', unsafe_allow_html=True)

        with rec2:
            if validos:
                oportunidad = max(validos, key=lambda x: x['prob'])
                edge_op = (oportunidad['prob'] * oportunidad['odd']) - 1
                imp = JarvisEngine.kelly_fraccional(oportunidad['prob'], oportunidad['odd'], capital, fraccion_val)
                st.markdown(f"""<div class="bet-card oportunidad-card"><h3>✅ Oportunidad</h3><p><b>{oportunidad['name']}</b></p>
                <p>Confianza: {oportunidad['prob']*100:.1f}%</p>
                <div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold;">Monto sugerido: ${int(round(imp))}</div></div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>✅ Oportunidad</h3><p>Ninguna opcion cumple el filtro.</p></div>', unsafe_allow_html=True)

        with rec3:
            prob_comb = stats['Win_H'] * stats['Over25']
            cuota_comb = m_l * m_o * 0.85
            edge_arr = (prob_comb * cuota_comb) - 1
            if edge_arr >= min_edge:
                imp = JarvisEngine.kelly_fraccional(prob_comb, cuota_comb, capital, fraccion_val)
                st.markdown(f"""<div class="bet-card arriesgada-card"><h3>🔥 Arriesgada</h3><p><b>{e_h} y +2.5 Goles</b></p>
                <p>Monto sugerido: <b>${int(round(imp))}</b></p></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="bet-card no-value"><h3>🔥 Arriesgada</h3><p>No rentable en modo {modo}.</p></div>""", unsafe_allow_html=True)

    # Historial
    st.markdown("---")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    st.subheader("Historial Directo")
    st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
else:
    st.warning("Selecciona una liga para comenzar.")
