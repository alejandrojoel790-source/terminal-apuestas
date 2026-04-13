import requests
import pandas as pd
import time
import os

# CONFIGURACION
API_KEY = "09766cc50fa14c40827ea6a629e851ac"
LIGAS_A_ACTUALIZAR = ['BL1', 'ELC'] 
TEMPORADAS = [2022, 2023, 2024, 2025]

def actualizar_todo():
    headers = {"X-Auth-Token": API_KEY}
    
    if not os.path.exists('Data'):
        os.makedirs('Data')

    print("Iniciando actualizacion de historial multitemporada")
    print("-" * 30)

    for liga in LIGAS_A_ACTUALIZAR:
        lista_maestra = []
        print(f"Procesando liga: {liga}")
        
        for año in TEMPORADAS:
            url = f"https://api.football-data.org/v4/competitions/{liga}/matches?season={año}"
            print(f"Consultando temporada {año}")
            
            try:
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    matches = data.get('matches', [])
                    
                    for m in matches:
                        if m['status'] == 'FINISHED':
                            lista_maestra.append({
                                'Date': m['utcDate'],
                                'HomeTeam': m['homeTeam']['name'],
                                'AwayTeam': m['awayTeam']['name'],
                                'FTHG': m['score']['fullTime']['home'],
                                'FTAG': m['score']['fullTime']['away']
                            })
                    
                    print(f"Temporada {año} guardada")
                    time.sleep(6)
                    
                elif response.status_code == 429:
                    print("Limite de peticiones alcanzado. Esperando 60 segundos")
                    time.sleep(60)
                else:
                    print(f"Error en temporada {año}: Codigo {response.status_code}")
                    
            except Exception as e:
                print(f"Error en peticion: {e}")

        if lista_maestra:
            df = pd.DataFrame(lista_maestra)
            nombre_archivo = f"Data/{liga}_2026.csv"
            df.to_csv(nombre_archivo, index=False)
            print(f"Exito: {len(df)} partidos totales guardados en {nombre_archivo}")

    print("-" * 30)
    print("Actualizacion de base de datos terminada")

if __name__ == "__main__":
    actualizar_todo()