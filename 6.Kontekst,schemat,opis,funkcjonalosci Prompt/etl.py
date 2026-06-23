import pandas as pd
import numpy as np
import os

def process_tmdb_data(file_path):
    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    
    # 3. Bezpieczna konwersja typów (z usuwaniem przypadkowych błędów tekstowych)
    print("Cleaning and safely converting types...")
    numeric_cols = ['id', 'number_of_seasons', 'number_of_episodes', 'episode_run_time', 'vote_count', 'popularity', 'vote_average']
    for col in numeric_cols:
        # errors='coerce' zamienia wszelkie błędne wpisy tekstowe na NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Usunięcie wierszy z błędnym/pustym id (nasz klucz główny)
    df = df.dropna(subset=['id']).copy()
    df['id'] = df['id'].astype(int)
    
    # Rzutowanie zmiennej boolowskiej in_production
    df['in_production'] = df['in_production'].astype(str).str.lower().map({'true': True, 'false': False})
    
    # --- Dim_Title ---
    print("Building Dim_Title...")
    dim_title = df[['id', 'name', 'original_name', 'overview', 'tagline', 'status', 'type', 'original_language']].copy()
    dim_title.rename(columns={'id': 'title_id'}, inplace=True)
    dim_title = dim_title.drop_duplicates(subset=['title_id']).reset_index(drop=True)
    
    # --- Dim_Date (2. Czyszczenie dat i uniwersalny wymiar czasu) ---
    print("Building Dim_Date...")
    df['first_air_date'] = pd.to_datetime(df['first_air_date'], errors='coerce')
    df['last_air_date'] = pd.to_datetime(df['last_air_date'], errors='coerce')
    
    # Wyciągnięcie wszystkich unikalnych dat
    unique_dates = pd.concat([df['first_air_date'], df['last_air_date']]).dropna().unique()
    dim_date = pd.DataFrame({'full_date': unique_dates})
    dim_date = dim_date.sort_values('full_date').reset_index(drop=True)
    
    # Dodanie atrybutów wymiaru czasu
    dim_date['date_id'] = dim_date.index + 1
    dim_date['year'] = dim_date['full_date'].dt.year
    dim_date['month'] = dim_date['full_date'].dt.month
    dim_date['day'] = dim_date['full_date'].dt.day
    dim_date['quarter'] = dim_date['full_date'].dt.quarter
    
    # Zmiana kolejności kolumn (estetyka)
    dim_date = dim_date[['date_id', 'full_date', 'year', 'month', 'day', 'quarter']]
    
    # Mapowanie dat na klucze obce (date_id)
    date_map = dim_date.set_index('full_date')['date_id'].to_dict()
    df['first_air_date_id'] = df['first_air_date'].map(date_map).astype('Int64')
    df['last_air_date_id'] = df['last_air_date'].map(date_map).astype('Int64')
    
    # --- Dim_ShowAttributes ---
    print("Building Dim_ShowAttributes...")
    show_attrs_cols = ['number_of_seasons', 'number_of_episodes', 'episode_run_time', 'in_production']
    dim_show_attributes = df[show_attrs_cols].drop_duplicates().reset_index(drop=True)
    dim_show_attributes['show_attributes_id'] = dim_show_attributes.index + 1
    
    # Bezpieczny join aby zmapować show_attributes_id na głównego DataFrame'a 
    df_filled = df[show_attrs_cols].fillna(-99999)
    dim_filled = dim_show_attributes[show_attrs_cols].fillna(-99999)
    dim_filled['show_attributes_id'] = dim_show_attributes['show_attributes_id']
    
    merged_attrs = df_filled.merge(dim_filled, on=show_attrs_cols, how='left')
    df['show_attributes_id'] = merged_attrs['show_attributes_id'].values
    
    # --- 1. Obsługa wielowartościowych stringów (Splity i Explode dla tabel mostowych) ---
    def process_multivalued(df_source, col_name, dim_name_col, dim_id_col, bridge_col):
        s = df_source[['id', col_name]].copy()
        s = s.dropna(subset=[col_name])
        
        # Split stringów po przecinku
        s[col_name] = s[col_name].astype(str).str.split(',')
        # Explode - rozbicie list na oddzielne wiersze
        s = s.explode(col_name)
        # Czyszczenie białych znaków (np. spacji po przecinku)
        s[col_name] = s[col_name].str.strip()
        # Odfiltrowanie pustych stringów
        s = s[s[col_name] != '']
        
        # Wymiar
        dim_df = pd.DataFrame({dim_name_col: s[col_name].unique()})
        dim_df[dim_id_col] = dim_df.index + 1
        
        # Bridge
        bridge_df = s.merge(dim_df, left_on=col_name, right_on=dim_name_col)[['id', dim_id_col]]
        bridge_df.rename(columns={'id': bridge_col}, inplace=True)
        bridge_df = bridge_df.drop_duplicates().reset_index(drop=True)
        
        return dim_df, bridge_df

    print("Building Dim_Genre & Bridge_Show_Genre...")
    dim_genre, bridge_show_genre = process_multivalued(df, 'genres', 'genre_name', 'genre_id', 'show_id')

    print("Building Dim_Creator & Bridge_Show_Creator...")
    dim_creator, bridge_show_creator = process_multivalued(df, 'created_by', 'creator_name', 'creator_id', 'show_id')
    
    print("Building Dim_Network & Bridge_Show_Network...")
    dim_network, bridge_show_network = process_multivalued(df, 'networks', 'network_name', 'network_id', 'show_id')
    
    print("Building Dim_ProductionCompany & Bridge_Show_ProductionCompany...")
    dim_production_company, bridge_show_production_company = process_multivalued(df, 'production_companies', 'company_name', 'company_id', 'show_id')
    
    # --- Fact_TV_Show ---
    print("Building Fact_TV_Show...")
    fact_tv_show = df[['id', 'first_air_date_id', 'last_air_date_id', 'show_attributes_id', 'popularity', 'vote_average', 'vote_count']].copy()
    fact_tv_show = fact_tv_show.rename(columns={'id': 'show_id'})
    fact_tv_show.insert(1, 'title_id', fact_tv_show['show_id']) # w tej relacji title_id = show_id (zgodnie ze schematem relacja 1:1)
    
    print("ETL script finished successfully!")
    
    # Zwrócenie struktury w postaci słownika
    return {
        'Fact_TV_Show': fact_tv_show,
        'Dim_Title': dim_title,
        'Dim_Date': dim_date,
        'Dim_ShowAttributes': dim_show_attributes,
        'Dim_Genre': dim_genre,
        'Bridge_Show_Genre': bridge_show_genre,
        'Dim_Creator': dim_creator,
        'Bridge_Show_Creator': bridge_show_creator,
        'Dim_Network': dim_network,
        'Bridge_Show_Network': bridge_show_network,
        'Dim_ProductionCompany': dim_production_company,
        'Bridge_Show_ProductionCompany': bridge_show_production_company
    }

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "TMDB_tv_dataset_v3.csv")
    
    if os.path.exists(file_path):
        tables = process_tmdb_data(file_path)
        
        # Zapis wyników ETL do folderu 'etl_output'
        output_dir = os.path.join(script_dir, "etl_output")
        os.makedirs(output_dir, exist_ok=True)
        
        for table_name, df_table in tables.items():
            out_file = os.path.join(output_dir, f"{table_name}.csv")
            df_table.to_csv(out_file, index=False)
            print(f"Saved {table_name} to {out_file} (Rows: {len(df_table)})")
    else:
        print(f"Error: Dataset not found at {file_path}")
