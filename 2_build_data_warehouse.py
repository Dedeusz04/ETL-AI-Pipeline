import pandas as pd

print("\n=== FAZA 2: Budowa Hurtowni Danych (MODELOWANIE & L) ===")
# Wczytanie zaufanego zestawu danych
try:
    df = pd.read_csv('cleaned_netflix_temp.csv', parse_dates=['date_added_clean'])
    print(f"[1] Wczytano wyczyszczoną tabelę z Fazy 1 gotową do modelowania. (Wierszy: {len(df)})")
except Exception as e:
    print(f"Nie znaleziono pliku pośredniego. Uruchom najpierw kod 1_clean_and_transform.py: {e}")
    exit(1)

# MODELOWANIE  


print("[2] Modelowanie Wymiaru Czasu (DIM_TIME)...")
dim_time = df[['date_added_clean', 'date_id']].dropna().drop_duplicates().copy()
dim_time['year'] = dim_time['date_added_clean'].dt.year
dim_time['month'] = dim_time['date_added_clean'].dt.month
dim_time['day'] = dim_time['date_added_clean'].dt.day
dim_time = dim_time[['date_id', 'year', 'month', 'day']].drop_duplicates().reset_index(drop=True)

print("[3] Modelowanie Wymiaru Reżyserów (DIM_DIRECTOR)...")
directors = df[['show_id', 'director']].dropna()
directors['director'] = directors['director'].str.split(', ')
directors = directors.explode('director') # Każdy reżyser traktowany osobno
dim_director = pd.DataFrame({'director_name': directors['director'].unique()})
dim_director['director_id'] = range(1, len(dim_director) + 1)
dim_director = dim_director[['director_id', 'director_name']]

print("[4] Modelowanie relacyjnej Tabeli Asocjacyjnej (BRIDGE_SHOW_DIRECTOR)...")
bridge_show_director = directors.merge(dim_director, left_on='director', right_on='director_name')
bridge_show_director = bridge_show_director[['show_id', 'director_id']].drop_duplicates()

print("[5] Wyodrębnianie Centralnej Tabeli Faktów (FACT_SHOWS)...")
fact_shows = df[['show_id', 'type', 'title', 'release_year', 'duration_numeric', 'date_id']]


# LOAD               

fact_shows.to_csv('fact_shows.csv', index=False)
dim_time.to_csv('dim_time.csv', index=False)
dim_director.to_csv('dim_director.csv', index=False)
bridge_show_director.to_csv('bridge_show_director.csv', index=False)

print("[6] LOAD: Z powodzeniem zrzucono ostateczne 4 tabele na dysk w formacie CSV.")
print("=== KONIEC FAZY 2 - URUCHOMIENIE POMYŚLNE ===\n")
