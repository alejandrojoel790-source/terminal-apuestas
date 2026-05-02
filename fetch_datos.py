import requests
import pandas as pd
import time
import os

# === CONFIGURACIÓN ===
# Tu API Key de football-data.org
API_KEY = "09766cc50fa14c40827ea6a629e851ac"
BASE_URL = "https://api.football-data.org/v4/competitions"

# Ligas configuradas para tu sistema
LIGAS = {
    "BL1_2026": "BL1",   # Bundesliga
    "ELC_2026": "ELC"    # Championship
}

# SEASONS 2025 cubre hasta mayo de 2026
SEASONS = [2023, 2024, 2025]

headers = {'X-Auth-Token': API_KEY}

# Asegurar que la carpeta Data existe
if not os.path.exists('Data'):
    os.makedirs('Data')

def descargar_datos_ligas():
    print("--- INICIANDO DESCARGA DE DATOS HISTÓRICOS ---")
    
    for archivo, code in LIGAS.items():
        print(f"\nProcesando liga: {archivo}...")
        dataset_liga = []
        
        for season in SEASONS:
            print(f"  > Obteniendo temporada {season}...", end=" ", flush=True)
            url = f"{BASE_URL}/{code}/matches?season={season}"
            
            try:
                response = requests.get(url, headers=headers)
                data = response.json()

                if response.status_code == 200 and "matches" in data:
                    partidos = []
                    for m in data["matches"]:
                        if m["status"] == "FINISHED":
                            partidos.append({
                                "Date": m["utcDate"],
                                "Home": m["homeTeam"]["name"],
                                "Away": m["awayTeam"]["name"],
                                "HG": m["score"]["fullTime"]["home"],
                                "AG": m["score"]["fullTime"]["away"]
                            })
                    dataset_liga.extend(partidos)
                    print(f"Hecho ({len(partidos)} partidos)")
                else:
                    error_msg = data.get('message', 'Error de acceso o límite alcanzado')
                    print(f"Error: {error_msg}")
                
                # Respetar el Rate Limit de la API (10 peticiones por minuto)
                time.sleep(6) 
                
            except Exception as e:
                print(f"Error técnico: {e}")

        if dataset_liga:
            df = pd.DataFrame(dataset_liga)
            # Limpieza de fechas para el formato de tu sistema
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d %H:%M')
            ruta = f"Data/{archivo}.csv"
            df.to_csv(ruta, index=False)
            print(f"✅ ARCHIVO ACTUALIZADO: {ruta} con {len(df)} partidos.")

if __name__ == "__main__":
    descargar_datos_ligas()