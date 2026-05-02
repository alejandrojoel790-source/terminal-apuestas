def actualizar_historial():
    for api_liga, archivo_csv in LIGAS.items():
        print(f"--- Procesando {archivo_csv} ---")
        path_csv = f"Data/{archivo_csv}.csv"
        
        if os.path.exists(path_csv):
            df_historial = pd.read_csv(path_csv)
            df_historial['Date'] = pd.to_datetime(df_historial['Date'])
        else:
            print(f"❌ Error: No se encontró {path_csv}")
            continue

        url = f'https://api.the-odds-api.com/v4/sports/{api_liga}/scores/?daysFrom={DIAS_ATRAS}&apiKey={API_KEY}'
        
        try:
            response = requests.get(url)
            partidos_api = response.json()
            
            # --- CORRECCIÓN: Verificar que la API mandó una LISTA ---
            if not isinstance(partidos_api, list):
                print(f"⚠️ Error de API para {api_liga}: {partidos_api}")
                continue

            nuevas_filas = []
            for partido in partidos_api:
                if partido.get('completed'):
                    fecha = pd.to_datetime(partido['commence_time']).strftime('%Y-%m-%d %H:%M:%S')
                    home = partido['home_team']
                    away = partido['away_team']
                    scores = partido.get('scores')
                    
                    if scores and len(scores) >= 2:
                        hg = next((s['score'] for s in scores if s['name'] == home), None)
                        ag = next((s['score'] for s in scores if s['name'] == away), None)
                        
                        if hg is not None and ag is not None:
                            # Evitar duplicados
                            existe = df_historial[
                                (df_historial['Home'] == home) & 
                                (df_historial['Away'] == away) & 
                                (df_historial['Date'].dt.strftime('%Y-%m-%d') == pd.to_datetime(fecha).strftime('%Y-%m-%d'))
                            ]
                            
                            if existe.empty:
                                nuevas_filas.append([fecha, home, away, int(hg), int(ag)])
                                print(f"➕ Añadido: {home} {hg}-{ag} {away}")

            if nuevas_filas:
                df_nuevos = pd.DataFrame(nuevas_filas, columns=['Date', 'Home', 'Away', 'HG', 'AG'])
                df_final = pd.concat([df_historial, df_nuevos]).sort_values(by='Date')
                df_final.to_csv(path_csv, index=False)
                print(f"✅ {len(nuevas_filas)} partidos nuevos guardados en {archivo_csv}.")
            else:
                print("ℹ️ Todo al día. No hay partidos nuevos.")

        except Exception as e:
            print(f"❌ Fallo crítico en {api_liga}: {e}")