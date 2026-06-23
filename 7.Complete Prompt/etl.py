import sqlite3

import pandas as pd
import numpy as np
import os
import re

def run_etl(input_csv, output_dir):
    print("Rozpoczęcie procesu ETL...")
    
    # 5. Odporność i Idempotentność potoku
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        for file in os.listdir(output_dir):
            if file.endswith(".csv"):
                os.remove(os.path.join(output_dir, file))
                
    # Wczytanie danych wejściowych
    df = pd.read_csv(input_csv)
    
    # Usuwamy całkowite duplikaty wierszy dla zachowania spójności
    df = df.drop_duplicates().reset_index(drop=True)
    
    # 6. Klucze główne - ponumerowanie wszystkich wierszy od 1 do len(df) dla głównego faktu
    df['show_id'] = range(1, len(df) + 1)
    
    # ==========================================
    # CZYSZCZENIE I TRANSFORMACJA ZMIENNYCH
    # ==========================================
    
    # 3. Czyszczenie typów numerycznych: 'episode_run_time'
    # Wydzielamy tylko pierwszy Integer za pomocą regex, by uniknąć błędu 'ValueError'
    df['episode_run_time'] = df['episode_run_time'].astype(str).str.extract(r'(\d+)')[0]
    df['episode_run_time'] = pd.to_numeric(df['episode_run_time'], errors='coerce').astype('Int64')
    
    # 4. Baza Boolowska: 'in_production' z tekstowego True/False na czysty bool
    df['in_production'] = df['in_production'].astype(str).str.strip().str.lower().map({'true': True, 'false': False})
    df['in_production'] = df['in_production'].fillna(False).astype(bool)
    
    # Numeryczne do faktu
    df['popularity'] = pd.to_numeric(df['popularity'], errors='coerce').astype(float)
    df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce').astype(float)
    df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce').astype('Int64')
    df['number_of_seasons'] = pd.to_numeric(df['number_of_seasons'], errors='coerce').astype('Int64')
    df['number_of_episodes'] = pd.to_numeric(df['number_of_episodes'], errors='coerce').astype('Int64')
    
    # ==========================================
    # WYMIAR DATY (Dim_Date)
    # ==========================================
    print("Generowanie Dim_Date...")
    
    date_cols = ['first_air_date', 'last_air_date']
    all_dates_series = pd.concat([df[col] for col in date_cols]).dropna()
    all_dates = pd.to_datetime(all_dates_series, errors='coerce').dropna().drop_duplicates()
    
    dim_date = pd.DataFrame({'full_date': all_dates})
    dim_date['year'] = dim_date['full_date'].dt.year.astype('Int64')
    dim_date['month'] = dim_date['full_date'].dt.month.astype('Int64')
    dim_date['day'] = dim_date['full_date'].dt.day.astype('Int64')
    dim_date['quarter'] = dim_date['full_date'].dt.quarter.astype('Int64')
    
    # 2. Format daty do YYYYMMDD w int
    dim_date['date_id'] = dim_date['full_date'].dt.strftime('%Y%m%d').astype(int)
    
    # Obsługa braków - syntetyczna data '99991231'
    missing_date = pd.DataFrame({
        'date_id': [99991231],
        'full_date': [pd.NaT],
        'year': [pd.NA],
        'month': [pd.NA],
        'day': [pd.NA],
        'quarter': [pd.NA]
    })
    
    dim_date = pd.concat([dim_date, missing_date], ignore_index=True)
    dim_date = dim_date[['date_id', 'full_date', 'year', 'month', 'day', 'quarter']].drop_duplicates()
    
    # Mapowanie dat na identyfikatory
    for col in date_cols:
        col_dt = pd.to_datetime(df[col], errors='coerce')
        df[f'{col}_id'] = col_dt.dt.strftime('%Y%m%d').fillna(99991231).astype(int)
        
    # ==========================================
    # WYMIARY PROSTE (Dim_Title, Dim_ShowAttributes)
    # ==========================================
    print("Generowanie Dim_Title oraz Dim_ShowAttributes...")
    
    # Dim_Title
    title_cols = ['name', 'original_name', 'overview', 'tagline', 'status', 'type', 'original_language']
    dim_title = df[title_cols].drop_duplicates().reset_index(drop=True)
    dim_title['title_id'] = range(1, len(dim_title) + 1)
    
    # Dim_ShowAttributes
    attr_cols = ['number_of_seasons', 'number_of_episodes', 'episode_run_time', 'in_production']
    dim_attributes = df[attr_cols].drop_duplicates().reset_index(drop=True)
    dim_attributes['show_attributes_id'] = range(1, len(dim_attributes) + 1)
    
    # Dołączenie identyfikatorów z powrotem do df
    df = df.merge(dim_title, on=title_cols, how='left', suffixes=('', '_drop'))
    # Dla bezpiecznego merge z intami, musimy wyrównać typy
    df = df.merge(dim_attributes, on=attr_cols, how='left', suffixes=('', '_drop'))
    
    dim_title = dim_title[['title_id'] + title_cols]
    dim_attributes = dim_attributes[['show_attributes_id'] + attr_cols]
    
    # ==========================================
    # RELACJE WIELE-DO-WIELU Z UŻYCIEM EXPLODE (Dim i Bridge)
    # ==========================================
    def process_many_to_many(df, source_col, target_dim_name, id_col_name, val_col_name):
        print(f"Przetwarzanie relacji N:M dla {source_col}...")
        exploded = df[['show_id', source_col]].copy()
        
        # 1. Framework: Rozdzielenie separatorami i użycie pd.explode()
        exploded[source_col] = exploded[source_col].astype(str).str.split(r',\s*')
        exploded = exploded.explode(source_col)
        
        # Filtrowanie pustych / nan
        exploded[source_col] = exploded[source_col].str.strip()
        exploded = exploded[exploded[source_col].notna() & (exploded[source_col] != '') & (exploded[source_col] != 'nan')]
        
        # Tworzenie wymiaru
        dim = pd.DataFrame({val_col_name: exploded[source_col].unique()})
        dim[id_col_name] = range(1, len(dim) + 1)
        dim = dim[[id_col_name, val_col_name]]
        
        # Tworzenie tabeli mostka
        bridge = exploded.merge(dim, left_on=source_col, right_on=val_col_name, how='left')
        bridge = bridge[['show_id', id_col_name]].drop_duplicates()
        
        return dim, bridge

    dim_genre, bridge_genre = process_many_to_many(df, 'genres', 'Dim_Genre', 'genre_id', 'genre_name')
    dim_creator, bridge_creator = process_many_to_many(df, 'created_by', 'Dim_Creator', 'creator_id', 'creator_name')
    dim_network, bridge_network = process_many_to_many(df, 'networks', 'Dim_Network', 'network_id', 'network_name')
    dim_company, bridge_company = process_many_to_many(df, 'production_companies', 'Dim_ProductionCompany', 'company_id', 'company_name')

    # ==========================================
    # TABELA FAKTÓW (Fact_TV_Show)
    # ==========================================
    print("Generowanie Fact_TV_Show...")
    fact_cols = ['show_id', 'title_id', 'first_air_date_id', 'last_air_date_id', 'show_attributes_id', 
                 'popularity', 'vote_average', 'vote_count']
    fact_tv_show = df[fact_cols].drop_duplicates()
    
    # ==========================================
    # ZAPIS WYNIKÓW
    # ==========================================
    print("Zapis tabel do bazy SQLite...")
    exports = {
        'Dim_Title': dim_title,
        'Dim_ShowAttributes': dim_attributes,
        'Dim_Date': dim_date,
        'Dim_Genre': dim_genre,
        'Dim_Creator': dim_creator,
        'Dim_Network': dim_network,
        'Dim_ProductionCompany': dim_company,
        'Bridge_Show_Genre': bridge_genre,
        'Bridge_Show_Creator': bridge_creator,
        'Bridge_Show_Network': bridge_network,
        'Bridge_Show_ProductionCompany': bridge_company,
        'Fact_TV_Show': fact_tv_show
    }
    
    conn = sqlite3.connect('hurtownia.db')
    for table_name, dataframe in exports.items():
        dataframe.to_sql(table_name, conn, if_exists='replace', chunksize=10000, index=False)
        print(f"Zapisano tabelę {table_name} do bazy SQLite.")
    conn.close()
        
    print("Zakończono sukcesem!")

if __name__ == "__main__":
    # Parametry wejścia/wyjścia można dostosować.
    input_file_path = "TMDB_tv_dataset_v3.csv"
    output_directory = "dwh_output"
    
    # Ścieżka relatywna do folderu z danymi, zakładając że skrypt jest uruchamiany w tym samym miejscu.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_full_path = os.path.join(base_dir, input_file_path)
    output_full_path = os.path.join(base_dir, output_directory)
    
    run_etl(input_full_path, output_full_path)
