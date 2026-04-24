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
    .optima-card { border-left: 8px solid #3b82f6; border-top: 2px solid #3b82f6; }
    .oportunidad-card { border-left: 8px solid #10b981; border-top: 2px solid #10b981; }
    .arriesgada-card { border-left: 8px solid #f59e0b; border-top: 2px solid #f59e0b; }
    
    /* Estilo para la tarjeta horizontal de resultado final */
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

# --- 4. PANEL DE CONTROL ---
st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")
    ligas_dict = {"Bundesliga": "BL1_2026", "Championship": "ELC_2026", "Liga MX": "LMX_2026"}
    liga_sel = st.selectbox("Ligas", list(ligas_dict.keys()))
    
    st.markdown("---")
    capital = st.number_input("Capital Total", min_value=0, value=1000, step=100)
    
    st.markdown("---")
    st.subheader("Modo de Analisis")
    modo = st.radio("Nivel de Precision:", ["Sistema Normal", "Sistema Medio", "Sistema Muy Preciso"])

    if modo == "Sistema Normal":
        fraccion_val, min_edge = 0.5, 0.05
    elif modo == "Sistema Medio":
        fraccion_val, min_edge = 0.25, 0.10
    else:
        fraccion_val, min_edge = 0.125, 0.18

    with st.expander("📚 Glosario Tecnico"):
        st.write("**Kelly:** Gestion de capital.")
        st.write("**Edge:** Tu ventaja real.")

    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 3px solid #3b82f6; margin-top: 10px;">
        <small>Configuracion Activa:</small><br>
        <b>Riesgo:</b> {int(1/fraccion_val)}x Kelly<br>
        <b>Filtro Edge:</b> {int(min_edge*100)}%
        </div>
    """, unsafe_allow_html=True)

df = load_data(ligas_dict[liga_sel])

if isinstance(df, pd.DataFrame):
    equipos = sorted(df['Home'].unique())
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: e_h = st.selectbox("Equipo Local", equipos)
    with c_sel2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)
    
    m_h = JarvisEngine.calcular_stats_ponderadas(df[df['Home'] == e_h], True)
    m_v = JarvisEngine.calcular_stats_ponderadas(df[df['Away'] == e_v], False)
    stats = JarvisEngine.poisson_probability(m_h, m_v)

    # UI: PROBABILIDADES SIN DECIMALES
    st.markdown("---")
    p_col = st.columns(5)
    p_col[0].metric(f"Gana {e_h}", f"{int(round(stats['Win_H']*100))}%")
    p_col[1].metric("Empate", f"{int(round(stats['Draw']*100))}%")
    p_col[2].metric(f"Gana {e_v}", f"{int(round(stats['Win_V']*100))}%")
    p_col[3].metric("+2.5 Goles", f"{int(round(stats['Over25']*100))}%")
    p_col[4].metric("Ambos Anotan", f"{int(round(stats['AmbosAn']*100))}%")

    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales (+/-)")
    m_col = st.columns(5)
    with m_col[0]: m_h_raw = st.number_input(f"Momio {e_h}", value=None)
    with m_col[1]: m_d_raw = st.number_input("Momio Empate", value=None)
    with m_col[2]: m_v_raw = st.number_input(f"Momio {e_v}", value=None)
    with m_col[3]: m_o_raw = st.number_input("Momio +2.5", value=None)
    with m_col[4]: m_b_raw = st.number_input("Momio Ambos Anotan", value=None)

    m_l = JarvisEngine.american_to_decimal(m_h_raw)
    m_e = JarvisEngine.american_to_decimal(m_d_raw)
    m_vi = JarvisEngine.american_to_decimal(m_v_raw)
    m_o = JarvisEngine.american_to_decimal(m_o_raw)
    m_b = JarvisEngine.american_to_decimal(m_b_raw)

    if m_l and m_e and m_vi and m_o and m_b:
        st.markdown("---")
        st.subheader(f"Estrategia sugerida - {modo}")
        
        # FILA SUPERIOR: 3 Tarjetas
        rec1, rec2, rec3 = st.columns(3)
        
        mercados = [
            {"name": f"Victoria {e_h}", "prob": stats['Win_H'], "odd": m_l},
            {"name": "Empate", "prob": stats['Draw'], "odd": m_e},
            {"name": f"Victoria {e_v}", "prob": stats['Win_V'], "odd": m_vi},
            {"name": "Mas de 2.5 Goles", "prob": stats['Over25'], "odd": m_o},
            {"name": "Ambos Anotan", "prob": stats['AmbosAn'], "odd": m_b}
        ]
        
        validos = [m for m in mercados if (m['prob'] * m['odd']) - 1 >= min_edge]

        with rec1:
            if validos:
                optima = max(validos, key=lambda x: (x['prob'] * x['odd']) - 1)
                monto = int(round(JarvisEngine.kelly_fraccional(optima['prob'], optima['odd'], capital, fraccion_val)))
                st.markdown(f'<div class="bet-card optima-card"><h3>🌟 Mas Optima</h3><p><b>{optima["name"]}</b></p><div style="background-color: #1e3a8a; padding: 10px; border-radius: 8px; color: #93c5fd; font-weight: bold; font-size: 20px;">Monto sugerido: ${monto}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>🌟 Mas Optima</h3><p>Sin valor suficiente.</p></div>', unsafe_allow_html=True)

        with rec2:
            if validos:
                oportunidad = max(validos, key=lambda x: x['prob'])
                monto = int(round(JarvisEngine.kelly_fraccional(oportunidad['prob'], oportunidad['odd'], capital, fraccion_val)))
                st.markdown(f'<div class="bet-card oportunidad-card"><h3>✅ Oportunidad</h3><p><b>{oportunidad["name"]}</b></p><div style="background-color: #064e3b; padding: 10px; border-radius: 8px; color: #10b981; font-weight: bold; font-size: 20px;">Monto sugerido: ${monto}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>✅ Oportunidad</h3><p>Sin apuestas probables.</p></div>', unsafe_allow_html=True)

        with rec3:
            prob_comb = stats['Win_H'] * stats['Over25']
            cuota_comb = m_l * m_o * 0.85
            if (prob_comb * cuota_comb) - 1 >= min_edge:
                monto = int(round(JarvisEngine.kelly_fraccional(prob_comb, cuota_comb, capital, fraccion_val)))
                st.markdown(f'<div class="bet-card arriesgada-card"><h3>🔥 Arriesgada</h3><p><b>{e_h} y +2.5 Goles</b></p><div style="background-color: #78350f; padding: 10px; border-radius: 8px; color: #f59e0b; font-weight: bold; font-size: 20px;">Monto sugerido: ${monto}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bet-card no-value"><h3>🔥 Arriesgada</h3><p>No rentable actualmente.</p></div>', unsafe_allow_html=True)

        # FILA INFERIOR: Resultado Final Horizontal
        st.markdown("---")
        
        todas_opciones = [
            {"n": f"Victoria {e_h}", "p": stats['Win_H'], "m": m_l},
            {"n": f"Victoria {e_v}", "p": stats['Win_V'], "m": m_vi},
            {"n": "Mas de 2.5 Goles", "p": stats['Over25'], "m": m_o},
            {"n": "Ambos Anotan", "p": stats['AmbosAn'], "m": m_b}
        ]
        mejor_segura = max(todas_opciones, key=lambda x: x['p'])
        monto_segura = int(round(JarvisEngine.kelly_fraccional(mejor_segura['p'], mejor_segura['m'], capital, fraccion_val)))
        if monto_segura <= 0: monto_segura = int(capital * 0.01) # Protección mínima

        st.markdown(f"""
            <div class="resultado-final-horizontal">
                <h2 style="color: #c4b5fd; margin: 0;">📊 Mayor Probabilidad (Resultado Final)</h2>
                <p style="font-size: 18px; margin: 0;">Basado en el analisis mas probable y seguro, la apuesta recomendada es:</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="font-size: 26px; color: white; margin: 5px 0;"><b>{mejor_segura['n']}</b></p>
                        <p style="font-size: 16px; color: #9ca3af; margin: 0;">Confianza estadistica: {int(round(mejor_segura['p']*100))}%</p>
                    </div>
                    <div class="monto-destacado">
                        Monto sugerido: ${monto_segura}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    enfrentamientos = df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)
    st.subheader("Historial Directo")
    st.dataframe(enfrentamientos[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
