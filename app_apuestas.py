import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from difflib import SequenceMatcher
import os
import requests
import re
import unicodedata

# ============================================================
# SISTEMA DE APUESTAS MOLINA - APP CORREGIDA
# Compatible con CSVs generados por iSports:
# Data/BL1_2026.csv
# Data/ELC_2026.csv
# Data/LMX_2026.csv
# ============================================================

# ------------------------------------------------------------
# 1. CONFIGURACION GENERAL
# ------------------------------------------------------------

st.set_page_config(page_title="Sistema de Apuestas", layout="wide")

# --- THE ODDS API KEY ---
# Esta API es para MOMIOS, no para descargar partidos.
API_KEY = "2a6d26bba847efc00183c6d06b7caf2c"

ODDS_REGIONS = "us,eu"
ODDS_MARKETS = "h2h"

LEAGUES = {
    "Bundesliga": {
        "csv": "Data/BL1_2026.csv",
        "odds_api_sport": "soccer_germany_bundesliga",
    },
    "Championship": {
        "csv": "Data/ELC_2026.csv",
        "odds_api_sport": "soccer_efl_championship",
    },
    "Liga MX": {
        "csv": "Data/LMX_2026.csv",
        "odds_api_sport": "soccer_mexico_ligamx",
    },
}

REQUIRED_COLUMNS = {"Date", "Home", "Away", "HG", "AG"}

# ------------------------------------------------------------
# 2. ESTILOS
# ------------------------------------------------------------

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }

    .stMetric {
        background-color: #1f2937;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #3b82f6;
    }

    .bet-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #4b5563;
        margin-bottom: 20px;
        min-height: 230px;
    }

    .segura-card {
        border-left: 8px solid #3b82f6;
        border-top: 2px solid #3b82f6;
    }

    .intermedia-card {
        border-left: 8px solid #10b981;
        border-top: 2px solid #10b981;
    }

    .oportunidad-card {
        border-left: 8px solid #f59e0b;
        border-top: 2px solid #f59e0b;
    }

    .arriesgada-card {
        border-left: 8px solid #ef4444;
        border-top: 2px solid #ef4444;
    }

    .no-value {
        border-left: 8px solid #6b7280;
        border-top: 2px solid #6b7280;
    }

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
        text-align: center;
    }

    .config-box {
        background-color: #1e1e1e;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin-top: 15px;
        font-size: 14px;
    }

    .small-muted {
        color: #9ca3af;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 3. MOTOR DE CALCULO
# ------------------------------------------------------------

class BettingEngine:
    @staticmethod
    def quitar_acentos(texto):
        texto = str(texto)
        texto = unicodedata.normalize("NFD", texto)
        texto = texto.encode("ascii", "ignore").decode("utf-8")
        return texto

    @staticmethod
    def normalizar_equipo(nombre):
        """
        Normaliza nombres de equipos para comparar:
        iSports vs The Odds API vs CSV.
        """
        nombre = str(nombre).lower().strip()
        nombre = BettingEngine.quitar_acentos(nombre)
        nombre = nombre.replace(".", " ")
        nombre = nombre.replace("-", " ")
        nombre = nombre.replace("_", " ")
        nombre = re.sub(r"\s+", " ", nombre).strip()

        reemplazos = {
            # Liga MX
            "cdsyc cruz azul": "cruz azul",
            "cruz azul": "cruz azul",
            "pumas u n a m": "pumas unam",
            "pumas unam": "pumas unam",
            "club universidad nacional": "pumas unam",
            "u n a m": "pumas unam",
            "club america": "america",
            "america": "america",
            "cf america": "america",
            "chivas guadalajara": "guadalajara",
            "guadalajara chivas": "guadalajara",
            "guadalajara": "guadalajara",
            "tigres uanl": "tigres",
            "tigres u a n l": "tigres",
            "tigres": "tigres",
            "monterrey": "monterrey",
            "rayados monterrey": "monterrey",
            "cf monterrey": "monterrey",
            "pachuca": "pachuca",
            "toluca": "toluca",
            "club toluca": "toluca",
            "necaxa": "necaxa",
            "atlas": "atlas",
            "leon": "leon",
            "club leon": "leon",
            "santos laguna": "santos laguna",
            "santos": "santos laguna",
            "club tijuana": "tijuana",
            "tijuana": "tijuana",
            "xolos": "tijuana",
            "fc juarez": "juarez",
            "juarez": "juarez",
            "atletico san luis": "san luis",
            "san luis": "san luis",
            "puebla": "puebla",
            "club puebla": "puebla",
            "queretaro": "queretaro",
            "mazatlan": "mazatlan",
            "mazatlan fc": "mazatlan",

            # Bundesliga comunes
            "bayern munich": "bayern munich",
            "fc bayern munchen": "bayern munich",
            "bayern munchen": "bayern munich",
            "borussia dortmund": "dortmund",
            "dortmund": "dortmund",
            "bayer leverkusen": "leverkusen",
            "leverkusen": "leverkusen",
            "rb leipzig": "leipzig",
            "rasenballsport leipzig": "leipzig",
            "eintracht frankfurt": "frankfurt",
            "frankfurt": "frankfurt",
            "vfb stuttgart": "stuttgart",
            "stuttgart": "stuttgart",
            "werder bremen": "werder bremen",
            "borussia monchengladbach": "monchengladbach",
            "monchengladbach": "monchengladbach",
            "wolfsburg": "wolfsburg",
            "vfl wolfsburg": "wolfsburg",
            "mainz": "mainz",
            "fc mainz": "mainz",
            "augsburg": "augsburg",
            "fc augsburg": "augsburg",
            "union berlin": "union berlin",
            "1 fc union berlin": "union berlin",
            "freiburg": "freiburg",
            "sc freiburg": "freiburg",
            "hoffenheim": "hoffenheim",
            "tsg hoffenheim": "hoffenheim",
            "heidenheim": "heidenheim",
            "1 fc heidenheim 1846": "heidenheim",
            "koln": "koln",
            "1 fc koln": "koln",

            # Championship comunes
            "leicester city": "leicester",
            "leicester": "leicester",
            "leeds united": "leeds",
            "leeds": "leeds",
            "southampton": "southampton",
            "ipswich town": "ipswich",
            "ipswich": "ipswich",
            "west bromwich albion": "west brom",
            "west brom": "west brom",
            "norwich city": "norwich",
            "norwich": "norwich",
            "coventry city": "coventry",
            "coventry": "coventry",
            "hull city": "hull",
            "hull": "hull",
            "middlesbrough": "middlesbrough",
            "sunderland": "sunderland",
            "blackburn rovers": "blackburn",
            "blackburn": "blackburn",
            "cardiff city": "cardiff",
            "cardiff": "cardiff",
            "swansea city": "swansea",
            "swansea": "swansea",
            "watford": "watford",
            "millwall": "millwall",
            "stoke city": "stoke",
            "stoke": "stoke",
            "bristol city": "bristol city",
            "preston north end": "preston",
            "preston": "preston",
            "qpr": "qpr",
            "queens park rangers": "qpr",
            "birmingham city": "birmingham",
            "birmingham": "birmingham",
            "huddersfield town": "huddersfield",
            "huddersfield": "huddersfield",
            "rotherham united": "rotherham",
            "rotherham": "rotherham",
            "plymouth argyle": "plymouth",
            "plymouth": "plymouth",
            "sheffield wednesday": "sheffield wednesday",
        }

        return reemplazos.get(nombre, nombre)

    @staticmethod
    def team_similarity(a, b):
        a_norm = BettingEngine.normalizar_equipo(a)
        b_norm = BettingEngine.normalizar_equipo(b)

        if not a_norm or not b_norm:
            return 0

        if a_norm == b_norm:
            return 1

        if a_norm in b_norm or b_norm in a_norm:
            return 0.95

        return SequenceMatcher(None, a_norm, b_norm).ratio()

    @staticmethod
    def american_to_decimal(momio):
        try:
            momio = float(momio)
        except (TypeError, ValueError):
            return None

        if momio == 0:
            return None

        if momio > 0:
            return (momio / 100) + 1

        return (100 / abs(momio)) + 1

    @staticmethod
    def decimal_to_american(decimal_odd):
        try:
            decimal_odd = float(decimal_odd)
        except (TypeError, ValueError):
            return 0

        if decimal_odd <= 1:
            return 0

        if decimal_odd >= 2:
            return int(round((decimal_odd - 1) * 100))

        return int(round(-100 / (decimal_odd - 1)))

    @staticmethod
    def implied_prob(decimal_odd):
        if decimal_odd is None or decimal_odd <= 1:
            return None
        return 1 / decimal_odd

    @staticmethod
    def edge(prob, decimal_odd):
        if decimal_odd is None or decimal_odd <= 1:
            return None
        return (prob * decimal_odd) - 1

    @staticmethod
    def kelly_fraccional(prob, cuota, bankroll, fraccion):
        if cuota is None or cuota <= 1 or bankroll <= 0:
            return 0

        edge = (prob * cuota) - 1
        if edge <= 0:
            return 0

        kelly_full = edge / (cuota - 1)
        stake = kelly_full * bankroll * fraccion

        return max(0, stake)

    @staticmethod
    def poisson_probability(media_h, media_v, max_goals=10):
        res = {
            "Win_H": 0,
            "Draw": 0,
            "Win_V": 0,
            "AmbosAn": 0,
            "O05": 0,
            "O15": 0,
            "O25": 0,
            "O35": 0,
            "U05": 0,
            "U15": 0,
            "U25": 0,
            "U35": 0,
        }

        for g_h in range(max_goals + 1):
            for g_v in range(max_goals + 1):
                p = poisson.pmf(g_h, media_h) * poisson.pmf(g_v, media_v)
                total = g_h + g_v

                if g_h > g_v:
                    res["Win_H"] += p
                elif g_h == g_v:
                    res["Draw"] += p
                else:
                    res["Win_V"] += p

                if g_h > 0 and g_v > 0:
                    res["AmbosAn"] += p

                if total > 0.5:
                    res["O05"] += p
                else:
                    res["U05"] += p

                if total > 1.5:
                    res["O15"] += p
                else:
                    res["U15"] += p

                if total > 2.5:
                    res["O25"] += p
                else:
                    res["U25"] += p

                if total > 3.5:
                    res["O35"] += p
                else:
                    res["U35"] += p

        return res

    @staticmethod
    def normalize_market_1x2(home_odd, draw_odd, away_odd):
        odds = [home_odd, draw_odd, away_odd]

        if any(o is None or o <= 1 for o in odds):
            return None

        raw = np.array([1 / o for o in odds], dtype=float)
        total = raw.sum()

        if total <= 0:
            return None

        fair = raw / total

        return {
            "Home": fair[0],
            "Draw": fair[1],
            "Away": fair[2],
            "Overround": total - 1,
        }

    @staticmethod
    def obtener_momios_api(liga_sel, home_team, away_team):
        """
        Carga momios H2H desde The Odds API y busca el partido por similitud.
        """
        if not API_KEY:
            return {"ok": False, "error": "No hay API key configurada."}

        sport = LEAGUES.get(liga_sel, {}).get("odds_api_sport")

        if not sport:
            return {"ok": False, "error": "Liga no configurada para The Odds API."}

        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"

        params = {
            "apiKey": API_KEY,
            "regions": ODDS_REGIONS,
            "markets": ODDS_MARKETS,
            "oddsFormat": "decimal",
        }

        try:
            response = requests.get(url, params=params, timeout=20)
            data = response.json()
        except Exception as e:
            return {"ok": False, "error": f"Error conectando con The Odds API: {e}"}

        if not response.ok:
            return {"ok": False, "error": f"API error {response.status_code}: {data}"}

        if not isinstance(data, list):
            return {"ok": False, "error": "Respuesta inesperada de The Odds API."}

        best_match = None
        best_score = 0

        for partido in data:
            api_home = partido.get("home_team", "")
            api_away = partido.get("away_team", "")

            score_direct = (
                BettingEngine.team_similarity(home_team, api_home)
                + BettingEngine.team_similarity(away_team, api_away)
            ) / 2

            score_reverse = (
                BettingEngine.team_similarity(home_team, api_away)
                + BettingEngine.team_similarity(away_team, api_home)
            ) / 2

            score = max(score_direct, score_reverse)

            if score > best_score:
                best_score = score
                best_match = partido

        if not best_match or best_score < 0.55:
            return {
                "ok": False,
                "error": (
                    "No se encontró el partido en The Odds API. "
                    "Puede ser por nombres distintos, partido no disponible o liga sin momios activos."
                ),
            }

        bookmakers = best_match.get("bookmakers", [])

        if not bookmakers:
            return {"ok": False, "error": "El partido existe, pero no trae bookmakers."}

        bk = bookmakers[0]
        markets = bk.get("markets", [])

        if not markets:
            return {"ok": False, "error": "El bookmaker no trae mercados."}

        outcomes = markets[0].get("outcomes", [])

        api_home = best_match.get("home_team", "")
        api_away = best_match.get("away_team", "")

        result = {
            "ok": True,
            "bookmaker": bk.get("title", "Bookmaker"),
            "api_home": api_home,
            "api_away": api_away,
            "score": best_score,
            "home_american": 0,
            "draw_american": 0,
            "away_american": 0,
        }

        for outcome in outcomes:
            name = outcome.get("name", "")
            price = outcome.get("price")
            american = BettingEngine.decimal_to_american(price)

            sim_home = BettingEngine.team_similarity(name, api_home)
            sim_away = BettingEngine.team_similarity(name, api_away)

            if sim_home >= 0.80 and sim_home >= sim_away:
                result["home_american"] = american
            elif sim_away >= 0.80 and sim_away > sim_home:
                result["away_american"] = american
            else:
                result["draw_american"] = american

        return result


class TeamModel:
    @staticmethod
    def _weighted_average(values, weights):
        values = pd.Series(values, dtype=float)
        weights = pd.Series(weights, dtype=float)

        mask = values.notna() & weights.notna() & (weights > 0)

        if mask.sum() == 0:
            return np.nan

        return float((values[mask] * weights[mask]).sum() / weights[mask].sum())

    @staticmethod
    def add_recency_weights(df):
        df = df.copy()
        max_date = df["Date"].max()
        days_old = (max_date - df["Date"]).dt.days.clip(lower=0)

        # Partidos recientes pesan más.
        df["weight"] = np.exp(-days_old / 240)

        return df

    @staticmethod
    def expected_goals(df, home_team, away_team):
        df = TeamModel.add_recency_weights(df)

        league_home_avg = TeamModel._weighted_average(df["HG"], df["weight"])
        league_away_avg = TeamModel._weighted_average(df["AG"], df["weight"])

        if not np.isfinite(league_home_avg) or league_home_avg <= 0:
            league_home_avg = 1.35

        if not np.isfinite(league_away_avg) or league_away_avg <= 0:
            league_away_avg = 1.10

        home_matches = df[df["Home"] == home_team]
        away_matches = df[df["Away"] == away_team]

        home_all = df[(df["Home"] == home_team) | (df["Away"] == home_team)]
        away_all = df[(df["Home"] == away_team) | (df["Away"] == away_team)]

        home_scored = TeamModel._weighted_average(home_matches["HG"], home_matches["weight"])
        home_conceded = TeamModel._weighted_average(home_matches["AG"], home_matches["weight"])

        away_scored = TeamModel._weighted_average(away_matches["AG"], away_matches["weight"])
        away_conceded = TeamModel._weighted_average(away_matches["HG"], away_matches["weight"])

        if not np.isfinite(home_scored):
            goals_for = np.where(home_all["Home"] == home_team, home_all["HG"], home_all["AG"])
            home_scored = TeamModel._weighted_average(goals_for, home_all["weight"])

        if not np.isfinite(home_conceded):
            goals_against = np.where(home_all["Home"] == home_team, home_all["AG"], home_all["HG"])
            home_conceded = TeamModel._weighted_average(goals_against, home_all["weight"])

        if not np.isfinite(away_scored):
            goals_for = np.where(away_all["Home"] == away_team, away_all["HG"], away_all["AG"])
            away_scored = TeamModel._weighted_average(goals_for, away_all["weight"])

        if not np.isfinite(away_conceded):
            goals_against = np.where(away_all["Home"] == away_team, away_all["AG"], away_all["HG"])
            away_conceded = TeamModel._weighted_average(goals_against, away_all["weight"])

        home_scored = home_scored if np.isfinite(home_scored) else league_home_avg
        home_conceded = home_conceded if np.isfinite(home_conceded) else league_away_avg
        away_scored = away_scored if np.isfinite(away_scored) else league_away_avg
        away_conceded = away_conceded if np.isfinite(away_conceded) else league_home_avg

        home_attack = home_scored / league_home_avg
        away_defense = away_conceded / league_home_avg

        away_attack = away_scored / league_away_avg
        home_defense = home_conceded / league_away_avg

        lambda_home = league_home_avg * home_attack * away_defense
        lambda_away = league_away_avg * away_attack * home_defense

        lambda_home = float(np.clip(lambda_home, 0.15, 4.50))
        lambda_away = float(np.clip(lambda_away, 0.15, 4.50))

        return lambda_home, lambda_away


# ------------------------------------------------------------
# 4. GESTION DE DATOS
# ------------------------------------------------------------

@st.cache_data
def load_data(path):
    if not os.path.exists(path):
        return None, f"No encontré el archivo: {path}"

    try:
        df = pd.read_csv(path)
    except Exception as e:
        return None, f"No pude leer el CSV: {e}"

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        return None, f"Al CSV le faltan columnas: {sorted(missing)}"

    try:
        df = df.copy()

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Home"] = df["Home"].astype(str).str.strip()
        df["Away"] = df["Away"].astype(str).str.strip()
        df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
        df["AG"] = pd.to_numeric(df["AG"], errors="coerce")

        df = df.dropna(subset=["Date", "Home", "Away", "HG", "AG"])
        df = df[df["Home"].ne("") & df["Away"].ne("")]

        # Evita partidos femeniles si entraron por error.
        filtro_femenil = (
            df["Home"].str.lower().str.contains("women|femenil|femenina|female", regex=True, na=False)
            | df["Away"].str.lower().str.contains("women|femenil|femenina|female", regex=True, na=False)
        )
        df = df[~filtro_femenil]

        df = df.sort_values("Date", ascending=False)

        if df.empty:
            return None, "El CSV cargó, pero no tiene partidos válidos."

        return df, None

    except Exception as e:
        return None, f"Error limpiando datos: {e}"


def money_fmt(value):
    try:
        return f"${int(round(value)):,}"
    except Exception:
        return "$0"


def pct(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def render_bet_card(title, mercado, capital, fraccion_val, extra_class, fixed_pct=None):
    prob = mercado.get("p")
    odd = mercado.get("m")
    edge = BettingEngine.edge(prob, odd)

    if fixed_pct is not None:
        stake = capital * fixed_pct
    else:
        stake = BettingEngine.kelly_fraccional(prob, odd, capital, fraccion_val)

    odd_txt = f"{odd:.2f}" if odd else "Sin momio"
    edge_txt = pct(edge) if edge is not None else "Sin edge"

    st.markdown(
        f"""
        <div class="bet-card {extra_class}">
            <h4>{title}</h4>
            <p><b>{mercado["n"]}</b></p>
            <p>Probabilidad modelo: <b>{pct(prob)}</b></p>
            <p>Cuota decimal: <b>{odd_txt}</b></p>
            <p>Edge: <b>{edge_txt}</b></p>
            <div class="monto-destacado">{money_fmt(stake)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# 5. PANEL DE CONTROL
# ------------------------------------------------------------

st.title("Sistema de Apuestas")

with st.sidebar:
    st.header("Configuracion")

    liga_sel = st.selectbox("Ligas", list(LEAGUES.keys()))

    st.markdown("---")

    capital = st.number_input(
        "Capital total",
        min_value=0,
        value=1000,
        step=1,
        format="%d",
    )

    st.markdown("---")

    modo = st.radio(
        "Nivel de precision:",
        ["Sistema Normal", "Sistema Medio", "Sistema Muy Preciso"],
    )

    if modo == "Sistema Normal":
        fraccion_val, min_edge = 0.50, 0.05
        desc_riesgo, desc_edge = "1/2 Kelly", "5%"
    elif modo == "Sistema Medio":
        fraccion_val, min_edge = 0.25, 0.10
        desc_riesgo, desc_edge = "1/4 Kelly", "10%"
    else:
        fraccion_val, min_edge = 0.125, 0.18
        desc_riesgo, desc_edge = "1/8 Kelly", "18%"

    st.markdown(
        f"""
        <div class="config-box">
            <b>Parametros activos:</b><br>
            • Riesgo: {desc_riesgo}<br>
            • Edge minimo: {desc_edge}<br>
            • Region momios: {ODDS_REGIONS}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    with st.expander("Glosario"):
        st.write("**Probabilidad modelo:** lo que estima tu sistema.")
        st.write("**Probabilidad implicita:** lo que el momio exige para quedar tablas.")
        st.write("**Edge:** ventaja estimada del modelo contra el momio.")
        st.write("**Kelly fraccional:** stake basado en edge, reducido por seguridad.")


# ------------------------------------------------------------
# 6. CARGA DE LIGA
# ------------------------------------------------------------

csv_path = LEAGUES[liga_sel]["csv"]
df, error = load_data(csv_path)

if error:
    st.error(error)
    st.info(
        "Revisa que el archivo exista dentro de la carpeta Data y que tenga columnas: "
        "Date, Home, Away, HG, AG."
    )
    st.stop()

st.caption(f"Datos cargados desde: `{csv_path}` | Partidos válidos: {len(df)}")

equipos = sorted(set(df["Home"].unique()).union(set(df["Away"].unique())))

if len(equipos) < 2:
    st.error("No hay suficientes equipos para comparar.")
    st.stop()

c1, c2 = st.columns(2)

with c1:
    e_h = st.selectbox("Equipo Local", equipos, index=0)

with c2:
    default_away_index = 1 if len(equipos) > 1 else 0
    e_v = st.selectbox("Equipo Visitante", equipos, index=default_away_index)

if e_h == e_v:
    st.warning("El equipo local y visitante no pueden ser el mismo.")
    st.stop()


# ------------------------------------------------------------
# 7. MODELO DE PROBABILIDADES
# ------------------------------------------------------------

media_h, media_v = TeamModel.expected_goals(df, e_h, e_v)
stats = BettingEngine.poisson_probability(media_h, media_v)

st.markdown("---")

p_col = st.columns(5)

p_col[0].metric(f"Gana {e_h}", f"{stats['Win_H'] * 100:.1f}%")
p_col[1].metric("Empate", f"{stats['Draw'] * 100:.1f}%")
p_col[2].metric(f"Gana {e_v}", f"{stats['Win_V'] * 100:.1f}%")
p_col[3].metric("+2.5 Goles", f"{stats['O25'] * 100:.1f}%")
p_col[4].metric("Ambos Anotan", f"{stats['AmbosAn'] * 100:.1f}%")

with st.expander("Analisis detallado del modelo"):
    m1, m2, m3 = st.columns(3)

    m1.write(f"**Goles esperados local:** {media_h:.2f}")
    m2.write(f"**Goles esperados visitante:** {media_v:.2f}")
    m3.write(f"**Goles esperados totales:** {media_h + media_v:.2f}")

    g_c1, g_c2, g_c3, g_c4 = st.columns(4)

    g_c1.write(f"**Over 0.5:** {pct(stats['O05'])} | **Under 0.5:** {pct(stats['U05'])}")
    g_c2.write(f"**Over 1.5:** {pct(stats['O15'])} | **Under 1.5:** {pct(stats['U15'])}")
    g_c3.write(f"**Over 2.5:** {pct(stats['O25'])} | **Under 2.5:** {pct(stats['U25'])}")
    g_c4.write(f"**Over 3.5:** {pct(stats['O35'])} | **Under 3.5:** {pct(stats['U35'])}")


# ------------------------------------------------------------
# 8. MOMIOS
# ------------------------------------------------------------

st.markdown("---")
st.subheader("Ingreso de momios actuales")

api_col1, api_col2 = st.columns([1, 3])

with api_col1:
    cargar_api = st.button("Cargar momios H2H")

with api_col2:
    st.caption(
        "The Odds API normalmente cubre H2H. "
        "Over/Under y Ambos Anotan pueden requerir otros mercados o plan."
    )

if cargar_api:
    with st.spinner("Conectando con The Odds API..."):
        datos = BettingEngine.obtener_momios_api(liga_sel, e_h, e_v)

    if datos.get("ok"):
        st.session_state.m_h = datos.get("home_american", 0)
        st.session_state.m_e = datos.get("draw_american", 0)
        st.session_state.m_v = datos.get("away_american", 0)

        st.success(
            f"Momios cargados desde {datos.get('bookmaker')} | "
            f"{datos.get('api_home')} vs {datos.get('api_away')} | "
            f"Coincidencia: {datos.get('score'):.2f}"
        )
    else:
        st.warning(datos.get("error", "No se pudieron cargar momios."))

m_col = st.columns(5)

with m_col[0]:
    m_h_raw = st.number_input(
        f"Momio {e_h}",
        value=st.session_state.get("m_h", 0),
        step=1,
        format="%d",
    )

with m_col[1]:
    m_d_raw = st.number_input(
        "Momio empate",
        value=st.session_state.get("m_e", 0),
        step=1,
        format="%d",
    )

with m_col[2]:
    m_v_raw = st.number_input(
        f"Momio {e_v}",
        value=st.session_state.get("m_v", 0),
        step=1,
        format="%d",
    )

with m_col[3]:
    m_o_raw = st.number_input(
        "Momio +2.5",
        value=0,
        step=1,
        format="%d",
    )

with m_col[4]:
    m_b_raw = st.number_input(
        "Momio ambos anotan",
        value=0,
        step=1,
        format="%d",
    )

m_h_dec = BettingEngine.american_to_decimal(m_h_raw)
m_d_dec = BettingEngine.american_to_decimal(m_d_raw)
m_v_dec = BettingEngine.american_to_decimal(m_v_raw)
m_o25_dec = BettingEngine.american_to_decimal(m_o_raw)
m_btts_dec = BettingEngine.american_to_decimal(m_b_raw)

fair_1x2 = BettingEngine.normalize_market_1x2(m_h_dec, m_d_dec, m_v_dec)

with st.expander("Lectura de mercado"):
    if fair_1x2:
        st.write(f"**Overround casa:** {fair_1x2['Overround'] * 100:.2f}%")
        st.write(
            f"**Probabilidades fair aproximadas:** "
            f"{e_h}: {pct(fair_1x2['Home'])} | "
            f"Empate: {pct(fair_1x2['Draw'])} | "
            f"{e_v}: {pct(fair_1x2['Away'])}"
        )
    else:
        st.write("Ingresa los 3 momios 1X2 para calcular overround y probabilidades fair.")


# ------------------------------------------------------------
# 9. ESTRATEGIA MULTINIVEL
# ------------------------------------------------------------

mercados = [
    {"n": f"Victoria {e_h}", "p": stats["Win_H"], "m": m_h_dec, "tipo": "1X2"},
    {"n": "Empate", "p": stats["Draw"], "m": m_d_dec, "tipo": "1X2"},
    {"n": f"Victoria {e_v}", "p": stats["Win_V"], "m": m_v_dec, "tipo": "1X2"},
    {"n": "Mas de 2.5 goles", "p": stats["O25"], "m": m_o25_dec, "tipo": "Goles"},
    {"n": "Ambos anotan", "p": stats["AmbosAn"], "m": m_btts_dec, "tipo": "BTTS"},
]

mercados_con_momio = [
    m for m in mercados
    if m["m"] is not None and m["m"] > 1
]

validos = [
    m for m in mercados_con_momio
    if BettingEngine.edge(m["p"], m["m"]) is not None
    and BettingEngine.edge(m["p"], m["m"]) >= min_edge
]

if mercados_con_momio:
    st.markdown("---")
    st.subheader(f"Estrategia multinivel - {modo}")

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        segura = max(mercados, key=lambda x: x["p"])

        render_bet_card(
            "Mas probable",
            segura,
            capital,
            fraccion_val,
            "segura-card",
            fixed_pct=0 if segura["m"] is None else 0.02,
        )

    with r2:
        candidatos = [m for m in mercados_con_momio if m["p"] >= 0.40]
        intermedia = max(candidatos or mercados_con_momio, key=lambda x: x["p"])

        render_bet_card(
            "Balance",
            intermedia,
            capital,
            fraccion_val,
            "intermedia-card",
        )

    with r3:
        if validos:
            op = max(validos, key=lambda x: BettingEngine.edge(x["p"], x["m"]))

            render_bet_card(
                "Oportunidad",
                op,
                capital,
                fraccion_val,
                "oportunidad-card",
            )
        else:
            st.markdown(
                f"""
                <div class="bet-card no-value">
                    <h4>Oportunidad</h4>
                    <p>No hay edge suficiente con los momios ingresados.</p>
                    <p>Filtro actual: <b>{desc_edge}</b></p>
                    <div class="monto-destacado">$0</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with r4:
        st.markdown(
            f"""
            <div class="bet-card arriesgada-card">
                <h4>Arriesgada</h4>
                <p><b>{e_h} y ambos anotan</b></p>
                <p>Requiere cuota combinada real para calcular stake.</p>
                <div class="monto-destacado">$0</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    mejor_prob = max(mercados, key=lambda x: x["p"])
    mejor_valor = max(validos, key=lambda x: BettingEngine.edge(x["p"], x["m"])) if validos else None

    if mejor_valor:
        final_text = (
            f"La mejor oportunidad por edge es: <b>{mejor_valor['n']}</b> "
            f"con edge estimado de <b>{pct(BettingEngine.edge(mejor_valor['p'], mejor_valor['m']))}</b>."
        )
    else:
        final_text = (
            f"La mejor opcion estadistica es: <b>{mejor_prob['n']}</b>, "
            f"pero con los momios actuales no hay valor suficiente."
        )

    st.markdown(
        f"""
        <div class="resultado-final-horizontal">
            <h3 style="color: #c4b5fd; margin: 0;">Resultado final</h3>
            <p style="font-size: 18px; margin: 10px 0;">{final_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Tabla completa de mercados"):
        rows = []

        for m in mercados:
            edge_value = BettingEngine.edge(m["p"], m["m"])

            rows.append({
                "Mercado": m["n"],
                "Tipo": m["tipo"],
                "Prob Modelo": pct(m["p"]),
                "Cuota Decimal": f"{m['m']:.2f}" if m["m"] else "N/A",
                "Prob Implicita": pct(BettingEngine.implied_prob(m["m"])) if m["m"] else "N/A",
                "Edge": pct(edge_value) if edge_value is not None else "N/A",
                "Stake Kelly": money_fmt(BettingEngine.kelly_fraccional(m["p"], m["m"], capital, fraccion_val)),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info("Ingresa al menos un momio valido para activar la estrategia multinivel.")


# ------------------------------------------------------------
# 10. HISTORIAL
# ------------------------------------------------------------

st.markdown("---")

tab1, tab2, tab3 = st.tabs(
    ["Historial directo", "Forma local", "Forma visitante"]
)

with tab1:
    enfrentamientos = df[
        ((df["Home"] == e_h) & (df["Away"] == e_v))
        | ((df["Home"] == e_v) & (df["Away"] == e_h))
    ].sort_values(by="Date", ascending=False)

    st.subheader("Historial directo")

    if enfrentamientos.empty:
        st.write("No hay enfrentamientos directos en el CSV.")
    else:
        st.dataframe(
            enfrentamientos[["Date", "Home", "HG", "AG", "Away"]],
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    st.subheader(f"Ultimos partidos de {e_h}")

    forma_h = df[
        (df["Home"] == e_h) | (df["Away"] == e_h)
    ].sort_values("Date", ascending=False).head(10)

    st.dataframe(
        forma_h[["Date", "Home", "HG", "AG", "Away"]],
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.subheader(f"Ultimos partidos de {e_v}")

    forma_v = df[
        (df["Home"] == e_v) | (df["Away"] == e_v)
    ].sort_values("Date", ascending=False).head(10)

    st.dataframe(
        forma_v[["Date", "Home", "HG", "AG", "Away"]],
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")