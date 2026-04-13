import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Prototipo de Apuestas", layout="wide")

class MotorAnalisis:
    @staticmethod
    def limpiar_texto(texto):
        t = str(texto).lower().strip()
        basura = ["fc ", "vfl ", "sv ", "1. ", "rb ", "tsg ", "04 ", "1899 ", "1910 ", "vfb ", "afc ", "sc ", "bayer 04 "]
        for b in basura:
            t = t.replace(b, "")
        return t.replace("ü", "u").replace("ö", "o").replace("ä", "a")

    @staticmethod
    def formatear_nombre(nombre):
        mapeo = {
            "bayern munchen": "Bayern Munich",
            "borussia dortmund": "Borussia Dortmund",
            "bayer leverkusen": "Bayer Leverkusen",
            "borussia monchengladbach": "Monchengladbach",
            "stuttgart": "Stuttgart",
            "leipzig": "RB Leipzig",
            "eintracht frankfurt": "Eintracht Frankfurt",
            "freiburg": "Friburgo",
            "hoffenheim": "Hoffenheim",
            "heidenheim": "Heidenheim",
            "werder bremen": "Werder Bremen",
            "augsburg": "Augsburgo",
            "wolfsburg": "Wolfsburgo",
            "mainz 05": "Mainz",
            "union berlin": "Union Berlin",
            "bochum 1848": "Bochum",
            "darmstadt 98": "Darmstadt",
            "koln": "Colonia",
            "leeds": "Leeds United",
            "leicester": "Leicester",
            "southampton": "Southampton",
            "ipswich": "Ipswich",
            "west brom": "West Bromwich",
            "norwich": "Norwich",
            "hull": "Hull City",
            "middlesbrough": "Middlesbrough",
            "coventry": "Coventry",
            "preston": "Preston",
            "bristol city": "Bristol City",
            "cardiff": "Cardiff",
            "swansea": "Swansea",
            "watford": "Watford",
            "sunderland": "Sunderland",
            "millwall": "Millwall",
            "blackburn": "Blackburn",
            "plymouth": "Plymouth",
            "qpr": "QPR",
            "stoke": "Stoke",
            "birmingham": "Birmingham",
            "huddersfield": "Huddersfield",
            "sheffield wed": "Sheffield Wednesday",
            "sheffield utd": "Sheffield United",
            "burnley": "Burnley",
            "luton": "Luton",
            "portsmouth": "Portsmouth",
            "derby": "Derby County",
            "oxford utd": "Oxford United"
        }
        return mapeo.get(nombre, nombre.title())

    @staticmethod
    def momio_a_decimal(momio):
        if momio is None or momio == 0: return 1.0
        return momio / 100 + 1 if momio > 0 else 100 / abs(momio) + 1

    @staticmethod
    def aplicar_dixon_coles(prob_matrix, lambda_h, lambda_a, rho):
        if rho == 0: return prob_matrix
        prob_matrix[0, 0] *= 1 - lambda_h * lambda_a * rho
        prob_matrix[0, 1] *= 1 + lambda_h * rho
        prob_matrix[1, 0] *= 1 + lambda_a * rho
        prob_matrix[1, 1] *= 1 - rho
        return prob_matrix / prob_matrix.sum()

    @staticmethod
    def calcular_probabilidades(media_h, media_a, rho=0.13):
        max_goles = 8
        prob_h = [poisson.pmf(i, media_h) for i in range(max_goles)]
        prob_a = [poisson.pmf(i, media_a) for i in range(max_goles)]
        matriz = np.outer(prob_h, prob_a)
        matriz = MotorAnalisis.aplicar_dixon_coles(matriz, media_h, media_a, rho)
        
        win = np.sum(np.tril(matriz, -1))
        draw = np.sum(np.diag(matriz))
        loss = np.sum(np.triu(matriz, 1))
        over25 = 1 - np.sum(matriz[:2, :2]) - matriz[0, 2] - matriz[2, 0]
        
        return win, draw, loss, over25

st.sidebar.header("CONFIGURACIÓN")
liga = st.sidebar.selectbox("Liga", ["Bundesliga", "Championship"])
archivo = f"Data/BL1_2026.csv" if liga == "Bundesliga" else "Data/ELC_2026.csv"

try:
    df = pd.read_csv(archivo)
    c_home, c_away = ("Home", "Away") if "Home" in df.columns else ("HomeTeam", "AwayTeam")
    c_hg, c_ag = ("HG", "AG") if "HG" in df.columns else ("FTHG", "FTAG")
    c_date = "Date" if "Date" in df.columns else None

    df[c_home] = df[c_home].apply(MotorAnalisis.limpiar_texto)
    df[c_away] = df[c_away].apply(MotorAnalisis.limpiar_texto)

    if c_date:
        df[c_date] = pd.to_datetime(df[c_date])
        max_date = df[c_date].max()
        df["weight"] = np.exp(-0.005 * (max_date - df[c_date]).dt.days)
    else:
        df["weight"] = 1.0

    equipos_raw = sorted(df[c_home].unique())
    equipos_display = {MotorAnalisis.formatear_nombre(e): e for e in equipos_raw}
    
    label_local = st.sidebar.selectbox("Equipo Local", list(equipos_display.keys()))
    local = equipos_display[label_local]
    label_visitante = st.sidebar.selectbox("Equipo Visitante", list(equipos_display.keys()), index=1)
    visitante = equipos_display[label_visitante]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("GESTIÓN DE CAPITAL")
    capital_total = st.sidebar.number_input("Capital Total", value=None, step=1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("MOMIOS")
    m_local = st.sidebar.number_input(f"Momio {label_local}", value=None, step=1)
    m_empate = st.sidebar.number_input("Momio Empate", value=None, step=1)
    m_visita = st.sidebar.number_input(f"Momio {label_visitante}", value=None, step=1)
    m_over = st.sidebar.number_input("Momio Over 2.5", value=None, step=1)

    ejecutar = st.sidebar.button("ANALIZAR PARTIDO")

    st.title("Prototipo de Apuestas")

    if ejecutar:
        entradas = [capital_total, m_local, m_empate, m_visita, m_over]
        if any(v is None for v in entradas):
            st.warning("Por favor rellena todos los campos de capital y momios antes de analizar")
        else:
            p_goles_h = (df[c_hg] * df["weight"]).sum() / df["weight"].sum()
            p_goles_a = (df[c_ag] * df["weight"]).sum() / df["weight"].sum()

            def get_rating(team, col_team, col_goals):
                mask = df[col_team] == team
                return (df[mask][col_goals] * df[mask]["weight"]).sum() / df[mask]["weight"].sum()

            att_h = get_rating(local, c_home, c_hg) / p_goles_h
            def_v = get_rating(visitante, c_away, c_hg) / p_goles_h
            esp_h = att_h * def_v * p_goles_h

            att_v = get_rating(visitante, c_away, c_ag) / p_goles_a
            def_h = get_rating(local, c_home, c_ag) / p_goles_a
            esp_v = att_v * def_h * p_goles_a

            p_w, p_d, p_l, p_o25 = MotorAnalisis.calcular_probabilidades(esp_h, esp_v)

            st.markdown("### RESULTADOS DEL ANÁLISIS")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(label_local.upper(), f"{p_w:.2%}")
            c2.metric("EMPATE", f"{p_d:.2%}")
            c3.metric(label_visitante.upper(), f"{p_l:.2%}")
            c4.metric("OVER 2.5", f"{p_o25:.2%}")

            st.markdown("---")
            st.markdown("### HISTORIAL DIRECTO")
            h2h = df[((df[c_home] == local) & (df[c_away] == visitante)) | 
                     ((df[c_home] == visitante) & (df[c_away] == local))].copy()
            
            if not h2h.empty:
                h2h = h2h.sort_values(by=c_date, ascending=False).head(5)
                h2h_display = h2h[[c_date, c_home, c_hg, c_ag, c_away]].copy()
                h2h_display[c_home] = h2h_display[c_home].apply(MotorAnalisis.formatear_nombre)
                h2h_display[c_away] = h2h_display[c_away].apply(MotorAnalisis.formatear_nombre)
                h2h_display.columns = ["FECHA", "LOCAL", "GL", "GV", "VISITANTE"]
                st.table(h2h_display)

            st.markdown("---")
            st.markdown("### RECOMENDACIONES DE INVERSIÓN")
            
            def procesar(prob, momio, mercado):
                dec = MotorAnalisis.momio_a_decimal(momio)
                ventaja = prob - 1 / dec
                col_a, col_b = st.columns([1, 2])
                with col_a: st.write(f"**{mercado.upper()}**")
                with col_b:
                    if ventaja > 0:
                        f_kelly = (dec * prob - 1) / (dec - 1) * 0.25
                        st.success(f"VENTAJA: {ventaja:.2%} | APUESTA SUGERIDA: ${capital_total * f_kelly:.2f}")
                    else:
                        st.write("Sin valor matemático")

            procesar(p_w, m_local, label_local)
            procesar(p_d, m_empate, "Empate")
            procesar(p_l, m_visita, label_visitante)
            procesar(p_o25, m_over, "Over 2.5")
    else:
        st.info("Configura los datos en el panel izquierdo y presiona ANALIZAR PARTIDO")

except Exception as e:
    st.error(f"Fallo en la ejecución: {e}")