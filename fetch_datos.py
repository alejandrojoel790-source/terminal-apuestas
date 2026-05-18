import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone

# ============================================================
# FETCH DATOS - iSports API
# Descarga calendario/resultados básicos de fútbol
#
# Genera:
# Data/BL1_2026.csv
# Data/ELC_2026.csv
# Data/LMX_2026.csv
#
# Endpoint usado:
# /sport/football/schedule/basic
# ============================================================

# API KEY DE iSPORTS
# Si esta key no funciona, reemplázala por la que aparece exactamente en tu panel.
API_KEY_ISPORTS = "Gv9HDzJfotLuAtFB"

BASE_URL = "http://api.isportsapi.com"

os.makedirs("Data", exist_ok=True)

# Fechas que quieres conservar en tus CSV
FECHA_INICIO = "2023-01-01"
FECHA_FIN = "2026-12-31"

# Filtros para evitar ligas femeniles
PALABRAS_FEMENIL = [
    "women",
    "woman",
    "female",
    "femenil",
    "femenina",
    "femenino",
    "ladies",
    "girls",
    "w league",
    "women's",
]

# Ligas objetivo.
# IMPORTANTE:
# Los league_id de iSports pueden ser distintos a API-Football.
# El código primero intenta encontrar los IDs automáticamente.
LIGAS_OBJETIVO = {
    "BL1_2026": {
        "nombre": "Bundesliga",
        "keywords": ["bundesliga", "germany"],
        "exclude": ["2.", "3.", "women", "u19", "u21"],
    },
    "ELC_2026": {
        "nombre": "Championship",
        "keywords": ["championship", "england"],
        "exclude": ["women", "u19", "u21"],
    },
    "LMX_2026": {
        "nombre": "Liga MX",
        "keywords": ["liga mx", "mexico", "primera"],
        "exclude": ["women", "femenil", "u19", "u21"],
    },
}


def api_get(path, params=None):
    """
    Petición GET base a iSports.
    """
    if params is None:
        params = {}

    params["api_key"] = API_KEY_ISPORTS

    url = f"{BASE_URL}{path}"

    try:
        response = requests.get(url, params=params, timeout=30)
    except Exception as e:
        print(f"ERROR conectando con iSports: {e}")
        return None

    try:
        data = response.json()
    except Exception:
        print("ERROR: iSports no devolvió JSON.")
        print("Status:", response.status_code)
        print(response.text[:1000])
        return None

    if response.status_code != 200:
        print(f"ERROR HTTP {response.status_code}")
        print(data)
        return None

    # iSports normalmente responde con:
    # {"code": 0, "message": "success", "data": [...]}
    code = data.get("code")

    if code not in [0, "0", None]:
        print("ERROR API iSports:")
        print(data)
        return None

    return data


def extraer_data(data):
    """
    Extrae la lista real desde la respuesta de iSports.
    """
    if data is None:
        return []

    contenido = data.get("data", [])

    if isinstance(contenido, list):
        return contenido

    if isinstance(contenido, dict):
        # Por si algún endpoint devuelve dict con listas internas
        for value in contenido.values():
            if isinstance(value, list):
                return value

    return []


def probar_api():
    """
    Prueba rápida de conexión con livescores.
    """
    print("=" * 60)
    print("PROBANDO iSPORTS API")
    print("=" * 60)

    data = api_get("/sport/football/livescores")

    if data is None:
        raise Exception("No se pudo conectar con iSports. Revisa tu API key.")

    print("iSports conectó correctamente.")
    print("Respuesta básica:")
    print({
        "code": data.get("code"),
        "message": data.get("message"),
        "items": len(extraer_data(data)),
    })
    print("")


def obtener_ligas():
    """
    Descarga catálogo básico de ligas/copas.
    """
    print("=" * 60)
    print("DESCARGANDO CATÁLOGO DE LIGAS")
    print("=" * 60)

    data = api_get("/sport/football/league/basic")
    ligas = extraer_data(data)

    print(f"Ligas encontradas: {len(ligas)}")
    print("")

    return ligas


def texto_liga(liga):
    """
    Convierte una liga en texto para poder buscar por keywords.
    """
    campos = [
        "leagueId",
        "leagueName",
        "leagueShortName",
        "name",
        "shortName",
        "country",
        "countryName",
        "areaName",
    ]

    partes = []

    for campo in campos:
        valor = liga.get(campo)
        if valor is not None:
            partes.append(str(valor))

    return " ".join(partes).lower()


def es_femenil(texto):
    """
    Evita descargar ligas femeniles.
    """
    texto = texto.lower()
    return any(palabra in texto for palabra in PALABRAS_FEMENIL)


def buscar_liga_por_keywords(ligas, config):
    """
    Busca una liga objetivo dentro del catálogo de iSports.
    """
    keywords = [k.lower() for k in config["keywords"]]
    excludes = [e.lower() for e in config.get("exclude", [])]

    candidatos = []

    for liga in ligas:
        texto = texto_liga(liga)

        if es_femenil(texto):
            continue

        if any(ex in texto for ex in excludes):
            continue

        score = 0

        for kw in keywords:
            if kw in texto:
                score += 1

        if score > 0:
            candidatos.append((score, liga, texto))

    candidatos = sorted(candidatos, key=lambda x: x[0], reverse=True)

    return candidatos


def imprimir_candidatos(nombre_archivo, candidatos):
    print("=" * 60)
    print(f"CANDIDATOS PARA {nombre_archivo}")
    print("=" * 60)

    if not candidatos:
        print("No encontré candidatos automáticos.")
        print("")
        return

    for score, liga, texto in candidatos[:10]:
        league_id = liga.get("leagueId") or liga.get("id")
        league_name = liga.get("leagueName") or liga.get("name")
        short_name = liga.get("leagueShortName") or liga.get("shortName")
        country = liga.get("country") or liga.get("countryName") or liga.get("areaName")

        print(
            f"Score: {score} | "
            f"leagueId: {league_id} | "
            f"Nombre: {league_name} | "
            f"Short: {short_name} | "
            f"Country: {country}"
        )

    print("")


def obtener_league_id_automatico(ligas, nombre_archivo, config):
    """
    Elige automáticamente el mejor candidato.
    """
    candidatos = buscar_liga_por_keywords(ligas, config)
    imprimir_candidatos(nombre_archivo, candidatos)

    if not candidatos:
        return None

    mejor = candidatos[0][1]
    league_id = mejor.get("leagueId") or mejor.get("id")

    if league_id is None:
        return None

    return str(league_id)


def timestamp_a_fecha(match_time):
    """
    Convierte timestamp UNIX a fecha YYYY-MM-DD.
    """
    if match_time is None:
        return None

    try:
        match_time = int(match_time)
    except Exception:
        return None

    # Si viene en milisegundos
    if match_time > 10_000_000_000:
        match_time = match_time // 1000

    try:
        dt = datetime.fromtimestamp(match_time, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def calcular_season(fecha):
    """
    Season aproximada:
    - Si el partido es julio-diciembre, season = año.
    - Si es enero-junio, season = año - 1.
    Esto ayuda para ligas europeas y también sirve como referencia.
    """
    try:
        dt = pd.to_datetime(fecha)
    except Exception:
        return None

    if dt.month >= 7:
        return dt.year

    return dt.year - 1


def descargar_schedule_liga(league_id):
    """
    Descarga schedule/results básico por leagueId.
    """
    params = {
        "leagueId": league_id
    }

    data = api_get("/sport/football/schedule/basic", params=params)
    partidos = extraer_data(data)

    return partidos


def partido_terminado(item):
    """
    En iSports, el ejemplo de schedule/results muestra status = -1 para partidos terminados.
    También aceptamos status textual por si cambia.
    """
    status = item.get("status")

    if status in [-1, "-1"]:
        return True

    if isinstance(status, str):
        status_lower = status.lower()
        if status_lower in ["ft", "finished", "finish", "ended", "complete", "completed"]:
            return True

    return False


def convertir_partidos_a_df(partidos, nombre_liga):
    filas = []

    fecha_inicio = pd.to_datetime(FECHA_INICIO)
    fecha_fin = pd.to_datetime(FECHA_FIN)

    for item in partidos:
        if not partido_terminado(item):
            continue

        fecha = timestamp_a_fecha(item.get("matchTime"))

        if not fecha:
            continue

        fecha_dt = pd.to_datetime(fecha)

        if fecha_dt < fecha_inicio or fecha_dt > fecha_fin:
            continue

        home = item.get("homeName")
        away = item.get("awayName")

        hg = item.get("homeScore")
        ag = item.get("awayScore")

        if home is None or away is None:
            continue

        if hg is None or ag is None:
            continue

        try:
            hg = int(hg)
            ag = int(ag)
        except Exception:
            continue

        league_name_api = item.get("leagueName") or nombre_liga
        league_id = item.get("leagueId", "")

        # Doble filtro para evitar femenil por si el endpoint trae algo raro.
        texto = f"{league_name_api} {home} {away}".lower()
        if es_femenil(texto):
            continue

        filas.append({
            "Date": fecha,
            "Home": str(home).strip(),
            "Away": str(away).strip(),
            "HG": hg,
            "AG": ag,
            "League": nombre_liga,
            "Season": calcular_season(fecha),
            "Country": "",
            "Round": "",
            "Status": "FT",
            "SourceLeagueName": league_name_api,
            "SourceLeagueId": league_id,
        })

    df = pd.DataFrame(filas)

    if df.empty:
        return df

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date", ascending=False)

    df = df.drop_duplicates(
        subset=["Date", "Home", "Away", "HG", "AG"],
        keep="first"
    )

    return df


def guardar_liga(nombre_archivo, nombre_liga, df):
    ruta = f"Data/{nombre_archivo}.csv"

    if df.empty:
        print(f"No se guardó {ruta}: no hubo partidos terminados dentro del rango.")
        return False

    df.to_csv(ruta, index=False, encoding="utf-8-sig")

    print("")
    print(f"LISTO: {ruta}")
    print(f"Total partidos guardados: {len(df)}")
    print(df.head())
    print("")

    return True


def descargar_liga(nombre_archivo, config, ligas_catalogo):
    print("=" * 60)
    print(f"PROCESANDO {config['nombre']}")
    print("=" * 60)

    league_id = obtener_league_id_automatico(ligas_catalogo, nombre_archivo, config)

    if not league_id:
        print(f"No pude detectar leagueId para {config['nombre']}.")
        print("Abre la documentación o el catálogo de ligas y pon el ID manualmente.")
        print("")
        return False

    print(f"Usando leagueId: {league_id}")

    partidos = descargar_schedule_liga(league_id)

    print(f"Partidos crudos recibidos: {len(partidos)}")

    if not partidos:
        print(f"No hubo partidos para {config['nombre']}.")
        print("")
        return False

    df = convertir_partidos_a_df(partidos, config["nombre"])

    print(f"Partidos terminados dentro del rango {FECHA_INICIO} a {FECHA_FIN}: {len(df)}")

    return guardar_liga(nombre_archivo, config["nombre"], df)


def main():
    probar_api()

    ligas_catalogo = obtener_ligas()

    if not ligas_catalogo:
        print("No se pudo obtener catálogo de ligas.")
        return

    archivos_guardados = []

    for nombre_archivo, config in LIGAS_OBJETIVO.items():
        ok = descargar_liga(nombre_archivo, config, ligas_catalogo)

        if ok:
            archivos_guardados.append(f"Data/{nombre_archivo}.csv")

        # Para cuidar el límite de 200 llamadas por día
        time.sleep(1.5)

    print("=" * 60)
    print("DESCARGA TERMINADA")
    print("=" * 60)

    if archivos_guardados:
        print("Archivos generados correctamente:")
        for archivo in archivos_guardados:
            print(archivo)
    else:
        print("No se generó ningún archivo.")
        print("")
        print("Posibles causas:")
        print("1. iSports no encontró automáticamente los leagueId.")
        print("2. El endpoint schedule/basic no devuelve histórico completo en tu plan.")
        print("3. La liga existe con otro nombre en iSports.")
        print("4. Tu API key no tiene acceso activo a Football.")


if __name__ == "__main__":
    main()