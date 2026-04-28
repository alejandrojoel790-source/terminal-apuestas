import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import os
import requests

# --- CONFIGURACION DE API ---
API_KEY = '2a6d26bba847efc00183c6d06b7caf2c'
REGION = 'us' 
MARKETS = 'h2h,totals,btts'

# --- 1. CONFIGURACION DE LA INTERFAZ ---
st.set_page_config(page_title="Sistema de Apuestas", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; }
    .bet-card { background-color: #262730; padding: 20px; border-radius: 15px; border: 1px solid #4b5563; margin-bottom: 20px; min-height: 220px; }
    .segura-card { border-left: 8px solid #3b82f6; border-top: 2px solid #3b82f6; }
    .intermedia-card { border-left: 8px solid #10b981; border-top: 2px solid #10b981; }
    .oportunidad-card { border-left: 8px solid #f59e0b; border-top: 2px solid #f59e0b; }
    .arriesgada-card { border-left: 8px solid #ef4444; border-top: 2px solid #ef4444; }
    
    .resultado-final-horizontal { 
        background-color: #262730; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #4b5563; 
        border-left: 12px solid #8b5cf6; 
        margin-top: 20px;
    }
    .monto-destacado {
        background-color: #4c1d95; 
        padding: 12px; 
        border-radius: 8px; 
        color: #c4b5fd; 
        font-weight: bold; 
        font-size: 22px;
    }
    .config-box {
        background-color: #1e1e1e; padding: 12px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-top: 15px; font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CALCULO ---
class BettingEngine:
    @staticmethod
    def american_to_decimal(momio):
        if momio is None or momio == 0: return 1.0
        return (momio/100)+1 if momio > 0 else (100/abs(momio))+1

    @staticmethod
    def decimal_to_american(decimal_odd):
        if decimal_odd >= 2.0:
            return int((decimal_odd - 1) * 100)
        else:
            return int(-100 / (decimal_odd - 1))

    @staticmethod
    def obtener_momios_api(liga_sel):
        api_map = {
            "Bundesliga": "soccer_germany_bundesliga",
            "Championship": "soccer_efl_championship",
            "Liga MX": "soccer_mexico_ligamx"
        }
        sport = api_map.get(liga_sel)
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGION}&markets={MARKETS}'
        try:
            response = requests.get(url)
            data = response.json()
            # Si la API devuelve un error (como dict en vez de lista), lo manejamos
            return data if isinstance(data, list) else None
        except: return None

    @staticmethod
    def calcular_stats_ponderadas(df_equipo, es_local):
        if df_equipo.empty: return 0.001
        col = 'HG' if es_local else 'AG'
        df_equipo['weight'] = df_equipo['Date'].dt.year.map({2026: 3, 2025: 2, 2024: 1}).fillna(1)
        return (df_equipo[col] * df_equipo['weight']).sum() / df_equipo['weight'].sum()

    @staticmethod
    def poisson_probability(media_h, media_v):
        res = {"Win_H": 0, "Draw": 0, "Win_V": 0, "AmbosAn": 0, "O05": 0, "O15": 0, "O25": 0, "O35": 0, "U15": 0, "U25": 0}
        for g_h in range(10):
            for g_v in range(10):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                total = g_h + g_v
                if g_h > g_v: res["Win_H"] += p
                elif g_h == g_v: res["Draw"] += p
                else: res["Win_V"] += p
                if g_h > 0 and g_v > 0: res["AmbosAn"] += p
                if total > 0.5: res["O05"] += p
                if total > 1.5: res["O15"] += p
                if total > 2.5: res["O25"] += p
                else: res["U25"] += p
                if total > 3.5: res["O35"] += p
                if total < 1.5: res["U15"] += p
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
    modo = st.radio("Nivel de Precision:", ["Sistema Normal", "Sistema Medio", "Sistema Muy Preciso"])
    
    if modo == "Sistema Normal":
        fraccion_val, min_edge = 0.5, 0.05
        desc_riesgo, desc_edge = "1/2 (Equilibrado)", "5%"
    elif modo == "Sistema Medio":
        fraccion_val, min_edge = 0.25, 0.10
        desc_riesgo, desc_edge = "1/4 (Seguro)", "10%"
    else:
        fraccion_val, min_edge = 0.125, 0.18
        desc_riesgo, desc_edge = "1/8 (Muy Seguro)", "18%"

    st.markdown(f"""<div class="config-box"><b>Parametros Activos:</b><br>• Riesgo Kelly: {desc_riesgo}<br>• Edge Minimo: {desc_edge}</div>""", unsafe_allow_html=True)

if liga_sel == "Liga MX":
    st.info("🚧 Liga MX en desarrollo.")
    st.stop()

df = load_data(ligas_dict[liga_sel])

if isinstance(df, pd.DataFrame):
    equipos = sorted(df['Home'].unique())
    c1, c2 = st.columns(2)
    with c1: e_h = st.selectbox("Equipo Local", equipos)
    with c2: e_v = st.selectbox("Equipo Visitante", equipos, index=1)
    
    stats = BettingEngine.poisson_probability(
        BettingEngine.calcular_stats_ponderadas(df[df['Home'] == e_h], True),
        BettingEngine.calcular_stats_ponderadas(df[df['Away'] == e_v], False)
    )

    st.markdown("---")
    p_col = st.columns(5)
    p_col[0].metric(f"Gana {e_h}", f"{int(round(stats['Win_H']*100))}%")
    p_col[1].metric("Empate", f"{int(round(stats['Draw']*100))}%")
    p_col[2].metric(f"Gana {e_v}", f"{int(round(stats['Win_V']*100))}%")
    p_col[3].metric("+2.5 Goles", f"{int(round(stats['O25']*100))}%")
    p_col[4].metric("Ambos Anotan", f"{int(round(stats['AmbosAn']*100))}%")

    # --- SECCION DE MOMIOS ---
    st.markdown("---")
    st.subheader("Ingreso de Momios Actuales")

    if st.button("🔄 Cargar Momios en Tiempo Real"):
        with st.spinner("Escaneando mercados de Caliente..."):
            datos = BettingEngine.obtener_momios_api(liga_sel)
            if isinstance(datos, list): # <-- FIX: Validamos que sea una lista real
                found = False
                for partido in datos:
                    if e_h.lower() in partido.get('home_team', '').lower() or partido.get('home_team', '').lower() in e_h.lower():
                        bk = next((b for b in partido['bookmakers'] if b['key'] == 'caliente'), partido['bookmakers'][0])
                        for mkt in bk['markets']:
                            if mkt['key'] == 'h2h':
                                for res in mkt['outcomes']:
                                    am = BettingEngine.decimal_to_american(res['price'])
                                    if res['name'] == partido['home_team']: st.session_state.m_h = am
                                    elif res['name'] == partido['away_team']: st.session_state.m_v = am
                                    else: st.session_state.m_e = am
                            elif mkt['key'] == 'totals':
                                for res in mkt['outcomes']:
                                    if res['point'] == 2.5 and res['name'] == 'Over': st.session_state.m_o = BettingEngine.decimal_to_american(res['price'])
                            elif mkt['key'] == 'btts':
                                for res in mkt['outcomes']:
                                    if res['name'] == 'Yes': st.session_state.m_b = BettingEngine.decimal_to_american(res['price'])
                        st.success(f"¡Momios de {bk['title']} cargados!")
                        found = True
                        break
                if not found: st.warning("Partido no detectado en la API.")
            else:
                st.error("Error en la respuesta de la API. Revisa tu API Key o limites.")

    m_col = st.columns(5)
    with m_col[0]: m_h_raw = st.number_input(f"Momio {e_h}", value=st.session_state.get('m_h', 0), step=1, format="%d")
    with m_col[1]: m_d_raw = st.number_input("Momio Empate", value=st.session_state.get('m_e', 0), step=1, format="%d")
    with m_col[2]: m_v_raw = st.number_input(f"Momio {e_v}", value=st.session_state.get('m_v', 0), step=1, format="%d")
    with m_col[3]: m_o_raw = st.number_input("Momio +2.5", value=st.session_state.get('m_o', 0), step=1, format="%d")
    with m_col[4]: m_b_raw = st.number_input("Momio Ambos Anotan", value=st.session_state.get('m_b', 0), step=1, format="%d")

    # --- ESTRATEGIA ---
    if m_h_raw != 0:
        st.markdown("---")
        m_l, m_o_25, m_b_25 = BettingEngine.american_to_decimal(m_h_raw), BettingEngine.american_to_decimal(m_o_raw), BettingEngine.american_to_decimal(m_b_raw)
        mercados = [{"n": "Victoria Local", "p": stats['Win_H'], "m": m_l}, {"n": "Mas de 2.5 Goles", "p": stats['O25'], "m": m_o_25}, {"n": "Ambos Anotan", "p": stats['AmbosAn'], "m": m_b_25}]
        validos = [m for m in mercados if (m['p'] * m['m']) - 1 >= min_edge]

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            s = max(mercados, key=lambda x: x['p'])
            st.markdown(f'<div class="bet-card segura-card"><h4>🛡️ Mas Segura</h4><p><b>{s["n"]}</b></p><div class="monto-destacado">${int(round(capital * (0.08 if s["p"] > 0.8 else 0.05)))}</div></div>', unsafe_allow_html=True)
        with r2:
            st.markdown(f'<div class="bet-card intermedia-card"><h4>⚖️ Intermedia</h4><p><b>{mercados[0]["n"]}</b></p><div class="monto-destacado">${int(round(capital * 0.04))}</div></div>', unsafe_allow_html=True)
        with r3:
            if validos:
                op = max(validos, key=lambda x: (x['p'] * x['m']) - 1)
                st.markdown(f'<div class="bet-card oportunidad-card"><h4>💎 Oportunidad</h4><p><b>{op["n"]}</b></p><div class="monto-destacado">${int(round(BettingEngine.kelly_fraccional(op["p"], op["m"], capital, fraccion_val)))}</div></div>', unsafe_allow_html=True)
            else: st.markdown(f'<div class="bet-card no-value"><h4>💎 Oportunidad</h4><p>Sin valor hoy.</p></div>', unsafe_allow_html=True)
        with r4: st.markdown(f'<div class="bet-card arriesgada-card"><h4>🔥 Arriesgada</h4><p><b>{e_h} y Ambos Anotan</b></p><div class="monto-destacado">${int(round(capital * 0.02))}</div></div>', unsafe_allow_html=True)

        st.markdown(f"""<div class="resultado-final-horizontal"><h3 style="color: #c4b5fd; margin: 0;">📊 Mayor Probabilidad (Apuesta Normal)</h3><p style="font-size: 18px; margin: 10px 0;">La mejor opcion para este encuentro es: <b>{max(mercados, key=lambda x: x['p'])['n']}</b></p></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Historial Directo")
    st.dataframe(df[((df['Home'] == e_h) & (df['Away'] == e_v)) | ((df['Home'] == e_v) & (df['Away'] == e_h))].sort_values(by='Date', ascending=False)[['Date', 'Home', 'HG', 'AG', 'Away']], use_container_width=True, hide_index=True)
