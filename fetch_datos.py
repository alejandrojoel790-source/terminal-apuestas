import requests
import pandas as pd
import time
import os

# === CONFIGURACIÓN ===
API_KEY = "09766cc50fa14c40827ea6a629e851ac"
BASE_URL = "https://api.football-data.org/v4/competitions"

# Ligas Europeas (Gratuitas en esta API)
LIGAS = {
    "BL1_2026": "BL1",   # Bundesliga
    "ELC_2026": "ELC"    # Championship
}

# Temporadas: 2023, 2024 y 2025 (La 2025 cubre hasta mayo de 2026)
SEASONS = [2023, 2024, 2025]

headers = {'X-Auth-Token': API_KEY}

if not os.path.exists('Data'):
    os.makedirs('Data')

def descargar_europa():
    print("--- INICIANDO VERIFICACIÓN DE EUROPA (Football-Data.org) ---")
    
    for archivo, code in LIGAS.items():
        print(f"\nProcesando: {archivo}...")
        dataset_liga = []
        
        for season in SEASONS:
            print(f"  > Descargando temporada {season}...", end=" ")
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
                    error_msg = data.get('message', 'Límite de API alcanzado o error de acceso')
                    print(f"Error: {error_msg}")
                
                # LA CLAVE: Esperar 6 segundos entre peticiones. 
                # Esta API es muy estricta con el plan gratuito (10 peticiones/minuto).
                time.sleep(6) 
                
            except Exception as e:
                print(f"Error técnico: {e}")

        if dataset_liga:
            df = pd.DataFrame(dataset_liga)
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d %H:%M')
            ruta = f"Data/{archivo}.csv"
            df.to_csv(ruta, index=False)
            print(f"--- ARCHIVO GENERADO: {ruta} con {len(df)} partidos totales ---")

if __name__ == "__main__":
    descargar_europa()