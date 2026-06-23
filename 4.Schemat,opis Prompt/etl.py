import sqlite3
import pandas as pd
import numpy as np
import os

def generate_dim_date(dates_series):
    dates_series = pd.to_datetime(dates_series, errors='coerce').dropna().unique()
    dim_date = pd.DataFrame({'full_date': dates_series})
    dim_date = dim_date.sort_values('full_date').reset_index(drop=True)
    dim_date['date_id'] = range(1, len(dim_date) + 1)
    dim_date['year'] = dim_date['full_date'].dt.year
    dim_date['month'] = dim_date['full_date'].dt.month
    dim_date['day'] = dim_date['full_date'].dt.day
    dim_date['quarter'] = dim_date['full_date'].dt.quarter
    dim_date['full_date'] = dim_date['full_date'].dt.date
    
    # Zwracamy układ kolumn dokładnie jak na diagramie
    return dim_date[['date_id', 'full_date', 'year', 'month', 'day', 'quarter']]

def build_dim_bridge(df, col_name, id_col_name, entity_name):
    # Rozdzielenie wartości po przecinku
    s = df[['id', col_name]].copy()
    s[col_name] = s[col_name].fillna('').astype(str).str.split(',')
    s = s.explode(col_name)
    s[col_name] = s[col_name].str.strip()
    s = s[s[col_name] != '']
    
    # Wymiar (Dim)
    dim = pd.DataFrame({entity_name: s[col_name].unique()})
    dim[id_col_name] = range(1, len(dim) + 1)
    
    # Tabela asocjacyjna (Bridge)
    bridge = s.merge(dim, left_on=col_name, right_on=entity_name, how='left')
    bridge = bridge[['id', id_col_name]].rename(columns={'id': 'show_id'})
    
    # Układ kolumn zgodny z diagramem
    dim = dim[[id_col_name, entity_name]]
    return dim, bridge

def process_data(input_file, output_dir='.'):
    print(f"Wczytywanie danych z {input_file}...")
    df = pd.read_csv(input_file)
    
    # ==========================
    # 1. Dim_Date
    # ==========================
    all_dates = pd.concat([df['first_air_date'], df['last_air_date']])
    dim_date = generate_dim_date(all_dates)
    
    date_map = dim_date.set_index('full_date')['date_id'].to_dict()
    df['first_air_date_date'] = pd.to_datetime(df['first_air_date'], errors='coerce').dt.date
    df['last_air_date_date'] = pd.to_datetime(df['last_air_date'], errors='coerce').dt.date
    df['first_air_date_id'] = df['first_air_date_date'].map(date_map).astype('Int64')
    df['last_air_date_id'] = df['last_air_date_date'].map(date_map).astype('Int64')
    
    # ==========================
    # 2. Dim_Title
    # ==========================
    title_cols = ['name', 'original_name', 'overview', 'tagline', 'status', 'type', 'original_language']
    dim_title = df[title_cols].copy().drop_duplicates().reset_index(drop=True)
    dim_title['title_id'] = range(1, len(dim_title) + 1)
    
    df = df.merge(dim_title, on=title_cols, how='left')
    dim_title = dim_title[['title_id'] + title_cols]
    
    # ==========================
    # 3. Dim_ShowAttributes
    # ==========================
    attr_cols = ['number_of_seasons', 'number_of_episodes', 'episode_run_time', 'in_production']
    dim_attributes = df[attr_cols].copy().drop_duplicates().reset_index(drop=True)
    dim_attributes['show_attributes_id'] = range(1, len(dim_attributes) + 1)
    
    df = df.merge(dim_attributes, on=attr_cols, how='left')
    dim_attributes = dim_attributes[['show_attributes_id'] + attr_cols]

    # ==========================
    # 4. Wymiary i tabele asocjacyjne (Bridge) dla cech wielowartościowych
    # ==========================
    dim_genre, bridge_genre = build_dim_bridge(df, 'genres', 'genre_id', 'genre_name')
    dim_creator, bridge_creator = build_dim_bridge(df, 'created_by', 'creator_id', 'creator_name')
    dim_network, bridge_network = build_dim_bridge(df, 'networks', 'network_id', 'network_name')
    dim_company, bridge_company = build_dim_bridge(df, 'production_companies', 'company_id', 'company_name')

    # ==========================
    # 5. Fact_TV_Show
    # ==========================
    fact_cols = ['id', 'title_id', 'first_air_date_id', 'last_air_date_id', 'show_attributes_id', 'popularity', 'vote_average', 'vote_count']
    fact_tv_show = df[fact_cols].copy().rename(columns={'id': 'show_id'})
    
    # Rzutowanie kluczy obcych na typ całkowitoliczbowy z obsługą wartości pustych (Int64)
    for col in ['title_id', 'first_air_date_id', 'last_air_date_id', 'show_attributes_id', 'vote_count']:
        fact_tv_show[col] = fact_tv_show[col].astype('Int64')

    # ==========================
    # Zapis tabel do formatu CSV
    # ==========================
    tables = {
        'Dim_Title': dim_title,
        'Dim_Date': dim_date,
        'Dim_ShowAttributes': dim_attributes,
        'Dim_Genre': dim_genre,
        'Bridge_Show_Genre': bridge_genre,
        'Dim_Creator': dim_creator,
        'Bridge_Show_Creator': bridge_creator,
        'Dim_Network': dim_network,
        'Bridge_Show_Network': bridge_network,
        'Dim_ProductionCompany': dim_company,
        'Bridge_Show_ProductionCompany': bridge_company,
        'Fact_TV_Show': fact_tv_show
    }
    
    conn = sqlite3.connect('hurtownia.db')
    for table_name, dataframe in tables.items():
        dataframe.to_sql(table_name, conn, if_exists='replace', chunksize=10000, index=False)
        print(f"Zapisano: {table_name} do SQLite")
    conn.close()
        
    print("\nProces ETL zakończony. Pliki struktury hurtowni danych zostały wygenerowane.")

if __name__ == '__main__':
    # Generowanie tabel z pliku TMDB_tv_dataset_v3.csv w bieżącym katalogu
    process_data('TMDB_tv_dataset_v3.csv')

    try:
        conn.close()
    except:
        pass
