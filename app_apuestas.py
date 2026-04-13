import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime, timezone
import os

# CONFIGURACION DE PAGINA
st.set_page_config(page_title="Terminal de Analisis Predictivo", layout="wide", initial_sidebar_state="expanded")

# FUNCIONES DE PROCESAMIENTO
@st.cache_data
def cargar_datos(ruta_archivo):
    if not os.path.exists(ruta_archivo):
        return None
        
    df = pd.read_csv(ruta_archivo)
    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    
    def simplificar_nombre(nombre):
        n = nombre.lower()
        limpieza = ['fc ', 'vfl ', 'sv ', '1. ', 'rb ', 'tsg ', '04 ', '1899 ', '1910 ', 'vfb ', 'afc ', 'sc ', 'bayer 04 ']
        for basura in limpieza:
            n = n.replace(basura, "")
        
        # Diccionario de identidades fijas para evitar duplicados
        identidades = {
            "munchen": "bayern munich",
            "münchen": "bayern munich",
            "leverkusen": "leverkusen",
            "mönchengladbach": "gladbach",
            "st. pauli": "st. pauli"
        }
        for clave, valor in identidades.items():
            if clave in n: return valor
            
        return n.replace("ü", "u").strip()

    df['HomeClean'] = df['HomeTeam'].apply(simplificar_nombre)
    df['AwayClean'] = df['AwayTeam'].apply(simplificar_nombre)
    df['TotalGoals'] = df['FTHG'] + df['FTAG']
    return df

def to_dec(m):
    if m == 0: return 1.0
    return (m/100) + 1 if m > 0 else (100/abs(m)) + 1

def calcular_kelly(prob, momio_dec):
    if momio_dec <= 1: return 0
    b = momio_dec - 1
    f = (b * prob - (1 - prob)) / b
    return max(0, f * 100)

# PANEL LATERAL
with st.sidebar:
    st.header("Configuracion")
    ligas_disponibles = {"Bundesliga": "BL1", "Championship": "ELC"}
    liga_seleccionada = st.selectbox("Selecciona la Liga", list(ligas_disponibles.keys()))
    codigo_liga = ligas_disponibles[liga_seleccionada]
    
    df = cargar_datos(f"Data/{codigo_liga}_2026.csv")

    if df is not None:
        equipos = sorted(df['HomeClean'].unique())
        st.divider()
        st.subheader("Seleccion de Equipos")
        local = st.selectbox("Local", equipos, index=0)
        visita = st.selectbox("Visitante", equipos, index=1 if len(equipos) > 1 else 0)
        
        st.divider()
        st.subheader("Momios Actuales")
        col_m1, col_m2 = st.columns(2)
        m_l = col_m1.number_input(f"Momio {local[:10]}", value=-110)
        m_v = col_m2.number_input(f"Momio {visita[:10]}", value=150)
        m_o25 = st.number_input("Momio Over 2.5", value=-110)
        
        bankroll = st.number_input("Capital Total", value=1000)
        analizar = st.button("EJECUTAR ANALISIS COMPLETO", type="primary", use_container_width=True)
    else:
        st.error("Base de datos no encontrada. Ejecuta el script de actualizacion.")
        analizar = False

# CUERPO PRINCIPAL
if analizar and df is not None:
    try:
        # 1. PARAMETROS DE TIEMPO
        fecha_corte = pd.to_datetime("2025-08-01").tz_localize('UTC')
        df_actual = df[df['Date'] >= fecha_corte].sort_values('Date', ascending=False)
        
        # 2. FUNCION DE CALCULO DE POTENCIA (FORMA + TEMPORADA + FACTOR X)
        def obtener_metricas(equipo, rol):
            # Estadistica de temporada (40% peso)
            avg_h_liga = df_actual['FTHG'].mean()
            avg_a_liga = df_actual['FTAG'].mean()
            
            temp_atq = df_actual.groupby('HomeClean' if rol == 'H' else 'AwayClean')['FTHG' if rol == 'H' else 'FTAG'].mean()[equipo]
            temp_def = df_actual.groupby('HomeClean' if rol == 'H' else 'AwayClean')['FTAG' if rol == 'H' else 'FTHG'].mean()[equipo]
            
            # Estadistica de forma reciente (60% peso)
            ultimos = df_actual[(df_actual['HomeClean'] == equipo) | (df_actual['AwayClean'] == equipo)].head(5)
            g_f = [r['FTHG'] if r['HomeClean']==equipo else r['FTAG'] for _,r in ultimos.iterrows()]
            g_c = [r['FTAG'] if r['HomeClean']==equipo else r['FTHG'] for _,r in ultimos.iterrows()]
            
            forma_atq = np.mean(g_f) if g_f else temp_atq
            forma_def = np.mean(g_c) if g_c else temp_def
            
            # Fusion Ponderada
            atq_final = ((temp_atq * 0.4) + (forma_atq * 0.6)) / (avg_h_liga if rol == 'H' else avg_a_liga)
            def_final = ((temp_def * 0.4) + (forma_def * 0.6)) / (avg_a_liga if rol == 'H' else avg_h_liga)
            
            # Factor X (Descanso)
            ultima_fecha = ultimos.iloc[0]['Date'] if not ultimos.empty else fecha_corte
            dias_descanso = (datetime.now(timezone.utc) - ultima_fecha).days
            factor_x = 0.90 if dias_descanso < 4 else 1.05
            
            return atq_final, def_final, factor_x

        # 3. GENERACION DE LAMBDAS
        atq_l, def_l, fx_l = obtener_metricas(local, 'H')
        atq_v, def_v, fx_v = obtener_metricas(visita, 'A')
        
        avg_h_total = df_actual['FTHG'].mean()
        avg_a_total = df_actual['FTAG'].mean()

        mu_h = atq_l * def_v * avg_h_total * fx_l
        mu_a = atq_v * def_l * avg_a_total * fx_v

        # 4. MATRIZ DE POISSON
        prob_matrix = np.outer(poisson.pmf(range(10), mu_h), poisson.pmf(range(10), mu_a))
        prob_matrix /= prob_matrix.sum()

        p_l = np.sum(np.tril(prob_matrix, -1))
        p_v = np.sum(np.triu(prob_matrix, 1))
        p_e = np.sum(np.diag(prob_matrix))
        p_o25_poisson = sum(prob_matrix[i, j] for i in range(10) for j in range(10) if i+j > 2.5)
        p_btts = np.sum(prob_matrix[1:, 1:])

        # 5. HISTORIAL H2H (ULTIMOS 10)
        h2h = df[((df['HomeClean'] == local) & (df['AwayClean'] == visita)) | 
                 ((df['HomeClean'] == visita) & (df['AwayClean'] == local))].sort_values('Date', ascending=False).head(10)
        p_h2h_o25 = (len(h2h[h2h['TotalGoals'] > 2.5]) / len(h2h)) if not h2h.empty else 0
        
        # PROBABILIDAD FINAL CONSENSO
        p_final_o25 = (p_o25_poisson + p_h2h_o25) / 2

        # --- INTERFAZ DE RESULTADOS ---
        st.title(f"Analisis: {local.title()} vs {visita.title()}")
        
        # BLOQUE 1: 1X2
        st.subheader("Probabilidades de Resultado (1X2)")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Victoria {local.title()}", f"{p_l*100:.1f}%", f"Edge: {(p_l * to_dec(m_l)-1)*100:+.1f}%")
        c2.metric("Empate", f"{p_e*100:.1f}%")
        c3.metric(f"Victoria {visita.title()}", f"{p_v*100:.1f}%", f"Edge: {(p_v * to_dec(m_v)-1)*100:+.1f}%")

        st.divider()

        # BLOQUE 2: OVER 2.5 Y KELLY
        st.subheader("Mercado Over 2.5 Goles")
        col1, col2, col3 = st.columns(3)
        
        kelly_val = calcular_kelly(p_final_o25, to_dec(m_o25))
        coherencia = 100 - abs((p_o25_poisson*100) - (p_h2h_o25*100))
        
        col1.metric("Probabilidad Consenso", f"{p_final_o25*100:.1f}%")
        col2.metric("Sugerencia Kelly", f"{kelly_val:.1f}%", f"Stake: ${bankroll * (kelly_val/100):.2f}")
        col3.metric("Indice de Coherencia", f"{coherencia:.0f}/100")

        st.divider()

        # BLOQUE 3: ALERTAS Y DATOS EXTRA
        ca, cb = st.columns(2)
        with ca:
            st.subheader("Alertas y Riesgos")
            if fx_l < 1.0 or fx_v < 1.0:
                st.warning("Alerta de Fatiga detectada por partidos recientes")
            st.write(f"Probabilidad Ambos Anotan: {p_btts*100:.1f}%")
            st.write(f"Probabilidad Porteria a Cero Local: {np.sum(prob_matrix[:, 0])*100:.1f}%")
            st.write(f"Probabilidad Porteria a Cero Visita: {np.sum(prob_matrix[0, :])*100:.1f}%")
            
        with cb:
            st.subheader("Historial Directo (Ultimos 10)")
            if not h2h.empty:
                st.dataframe(h2h[['Date', 'HomeTeam', 'FTHG', 'FTAG', 'AwayTeam']], use_container_width=True)
            else:
                st.info("No hay historial disponible entre estos equipos")

    except Exception as e:
        st.error(f"Error en el calculo: {e}")