import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime, timezone
import os

# CONFIGURACION DE RUTA Y PARAMETROS
RUTA_DATA = "Data/BL1_2026.csv" # Cambiar a ELC_2026.csv segun sea el caso
FECHA_CORTE_TEMPORADA = pd.to_datetime("2025-08-01").tz_localize('UTC')
PESO_FORMA_RECIENTE = 0.60
PESO_TEMPORADA = 0.40

def to_dec(m):
    if m == 0: return 1.0
    return (m/100) + 1 if m > 0 else (100/abs(m)) + 1

def simplificar_nombre(nombre):
    n = nombre.lower()
    limpieza = ['fc ', 'vfl ', 'sv ', '1. ', 'rb ', 'tsg ', '04 ', '1899 ', '1910 ', 'vfb ', 'afc ', 'sc ', 'bayer 04 ']
    for basura in limpieza:
        n = n.replace(basura, "")
    if "munchen" in n or "münchen" in n: n = "bayern munich"
    if "leverkusen" in n: n = "leverkusen"
    if "gladbach" in n: n = "gladbach"
    return n.replace("ü", "u").strip()

def calcular_kelly(prob, momio_dec):
    if momio_dec <= 1: return 0
    b = momio_dec - 1
    f = (b * prob - (1 - prob)) / b
    return max(0, f)

# 1. CARGA Y PREPARACION DE DATOS
if not os.path.exists(RUTA_DATA):
    print(f"Error: No se encuentra el archivo {RUTA_DATA}")
    exit()

df = pd.read_csv(RUTA_DATA)
df['Date'] = pd.to_datetime(df['Date'], utc=True)
df['HomeClean'] = df['HomeTeam'].apply(simplificar_nombre)
df['AwayClean'] = df['AwayTeam'].apply(simplificar_nombre)
df['TotalGoals'] = df['FTHG'] + df['FTAG']

# 2. MOTOR DE CALCULO (ESTADISTICA AVANZADA)
def analizar_partido(local, visita, m_l, m_v, m_o25):
    df_actual = df[df['Date'] >= FECHA_CORTE_TEMPORADA].sort_values('Date', ascending=False)
    
    # Factor de Descanso (Factor X)
    def obtener_factor_x(equipo):
        partidos = df_actual[(df_actual['HomeClean'] == equipo) | (df_actual['AwayClean'] == equipo)]
        if partidos.empty: return 1.0
        ultima_fecha = partidos.iloc[0]['Date']
        dias_descanso = (datetime.now(timezone.utc) - ultima_fecha).days
        return 0.90 if dias_descanso < 4 else 1.05 # Penaliza si jugaron hace menos de 4 dias

    # Metricas de Temporada
    avg_h, avg_a = df_actual['FTHG'].mean(), df_actual['FTAG'].mean()
    
    # Metricas de Forma (Ultimos 5)
    def get_stats(equipo, modo):
        d = df_actual[(df_actual['HomeClean' if modo=='H' else 'AwayClean'] == equipo)]
        temp = d['FTHG' if modo=='H' else 'FTAG'].mean()
        def_temp = d['FTAG' if modo=='H' else 'FTHG'].mean()
        
        ultimos = df_actual[(df_actual['HomeClean'] == equipo) | (df_actual['AwayClean'] == equipo)].head(5)
        g_f = [r['FTHG'] if r['HomeClean']==equipo else r['FTAG'] for _,r in ultimos.iterrows()]
        g_c = [r['FTAG'] if r['HomeClean']==equipo else r['FTHG'] for _,r in ultimos.iterrows()]
        forma = np.mean(g_f) if g_f else temp
        def_forma = np.mean(g_c) if g_c else def_temp
        
        atq_final = ((temp/avg_h if modo=='H' else temp/avg_a) * PESO_TEMPORADA) + ((forma/avg_h if modo=='H' else forma/avg_a) * PESO_FORMA_RECIENTE)
        def_final = ((def_temp/avg_a if modo=='H' else def_temp/avg_h) * PESO_TEMPORADA) + ((def_forma/avg_a if modo=='H' else def_forma/avg_h) * PESO_FORMA_RECIENTE)
        return atq_final, def_final

    atq_l, def_l = get_stats(local, 'H')
    atq_v, def_v = get_stats(visita, 'A')
    
    # Aplicacion de Factor X
    mu_h = atq_l * def_v * avg_h * obtener_factor_x(local)
    mu_a = atq_v * def_l * avg_a * obtener_factor_x(visita)

    # Matriz de Probabilidades
    prob_matrix = np.outer(poisson.pmf(range(10), mu_h), poisson.pmf(range(10), mu_a))
    prob_matrix /= prob_matrix.sum()

    p_l = np.sum(np.tril(prob_matrix, -1))
    p_v = np.sum(np.triu(prob_matrix, 1))
    p_e = np.sum(np.diag(prob_matrix))
    p_o25 = sum(prob_matrix[i,j] for i in range(10) for j in range(10) if i+j > 2.5)
    p_btts = np.sum(prob_matrix[1:, 1:])

    # 3. SALIDA DE DATOS PROFESIONAL
    print("-" * 40)
    print(f"ANALISIS: {local.upper()} vs {visita.upper()}")
    print("-" * 40)
    print(f"Prob. Victoria {local.title()}: {p_l*100:.1f}% | Edge: {(p_l * to_dec(m_l)-1)*100:+.1f}%")
    print(f"Prob. Empate: {p_e*100:.1f}%")
    print(f"Prob. Victoria {visita.title()}: {p_v*100:.1f}% | Edge: {(p_v * to_dec(m_v)-1)*100:+.1f}%")
    print("-" * 40)
    print(f"Probabilidad Over 2.5: {p_o25*100:.1f}%")
    print(f"Probabilidad Ambos Anotan: {p_btts*100:.1f}%")
    
    k_o25 = calcular_kelly(p_o25, to_dec(m_o25))
    if k_o25 > 0:
        print(f"Sugerencia Kelly para Over 2.5: {k_o25*100:.1f}% del capital")
    
    # Historial H2H
    h2h = df[((df['HomeClean'] == local) & (df['AwayClean'] == visita)) | 
             ((df['HomeClean'] == visita) & (df['AwayClean'] == local))].head(5)
    print("-" * 40)
    print("Ultimos Enfrentamientos Directos:")
    print(h2h[['Date', 'HomeTeam', 'FTHG', 'FTAG', 'AwayTeam']].to_string(index=False))

# EJECUCION DE PRUEBA
if __name__ == "__main__":
    # Ejemplo: Augsburg vs Leverkusen
    analizar_partido("augsburg", "leverkusen", m_l=-110, m_v=150, m_o25=-120)