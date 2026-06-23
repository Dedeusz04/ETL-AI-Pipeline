import pandas as pd
import numpy as np
import ast
import os

def parse_multivalue_col(val):
    """
    Parses a multi-valued column that could be a comma-separated string,
    or a stringified list of dictionaries (like JSON).
    """
    if pd.isna(val) or str(val).strip() == '':
        return []
    val_str = str(val).strip()
    
    # Check if it looks like a list of dictionaries/strings
    if val_str.startswith('[') and val_str.endswith(']'):
        try:
            parsed = ast.literal_eval(val_str)
            if isinstance(parsed, list):
                if len(parsed) > 0 and isinstance(parsed[0], dict):
                    # TMDB format often has [{'id': 1, 'name': 'Drama'}, ...]
                    return [item.get('name', str(item)) for item in parsed if item.get('name')]
                else:
                    return [str(i) for i in parsed]
        except (ValueError, SyntaxError):
            pass
            
    # Fallback to comma-separated
    return [x.strip() for x in val_str.split(',') if x.strip()]

def main():
    input_file = 'TMDB_tv_dataset_v3.csv'
    
    print(f"Loading data from {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        print("Please ensure the dataset is in the same directory as the script.")
        return

    print("Data loaded successfully. Starting transformation...")

    # Ensure necessary columns are present (adding empty if missing to prevent KeyError)
    expected_columns = [
        'id', 'name', 'original_name', 'overview', 'in_production', 'status', 'type', 
        'original_language', 'origin_country', 'first_air_date', 'last_air_date',
        'genres', 'created_by', 'networks', 'production_companies',
        'number_of_episodes', 'number_of_seasons', 'popularity', 'vote_average', 'vote_count'
    ]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = None

    # --- 1. Dim_Title ---
    print("Building Dim_Title...")
    dim_title = df[['id', 'name', 'original_name', 'overview']].copy()
    dim_title.rename(columns={'id': 'title_id'}, inplace=True)
    dim_title.drop_duplicates(subset=['title_id'], inplace=True)
    
    # --- 2. Dim_ShowAttributes ---
    print("Building Dim_ShowAttributes...")
    attr_cols = ['in_production', 'status', 'type', 'original_language', 'origin_country']
    dim_show_attr = df[attr_cols].copy()
    dim_show_attr.drop_duplicates(inplace=True)
    dim_show_attr.reset_index(drop=True, inplace=True)
    dim_show_attr['show_attributes_id'] = dim_show_attr.index + 1
    
    # Merge back to df to assign show_attributes_id to the fact table
    df = df.merge(dim_show_attr, on=attr_cols, how='left')
    
    # --- 3. Dim_Date ---
    print("Building Dim_Date...")
    dates = pd.concat([df['first_air_date'], df['last_air_date']]).dropna().unique()
    dim_date = pd.DataFrame({'date': dates})
    dim_date['date'] = pd.to_datetime(dim_date['date'], errors='coerce')
    dim_date.dropna(subset=['date'], inplace=True)
    dim_date.drop_duplicates(subset=['date'], inplace=True)
    dim_date.reset_index(drop=True, inplace=True)
    
    dim_date['date_id'] = dim_date.index + 1
    dim_date['year'] = dim_date['date'].dt.year
    dim_date['month'] = dim_date['date'].dt.month
    dim_date['day'] = dim_date['date'].dt.day
    
    # Map dates to IDs
    date_map = dim_date.set_index(dim_date['date'].dt.strftime('%Y-%m-%d'))['date_id'].to_dict()
    def map_date(val):
        if pd.isna(val):
            return None
        try:
            return date_map.get(pd.to_datetime(val).strftime('%Y-%m-%d'))
        except:
            return None

    df['first_air_date_id'] = df['first_air_date'].apply(map_date)
    df['last_air_date_id'] = df['last_air_date'].apply(map_date)

    # --- Helper function for N:M relationships (Bridge and Dimension Tables) ---
    def build_dim_and_bridge(df_source, col_name, dim_id_col, dim_name_col):
        records = []
        for _, row in df_source.iterrows():
            show_id = row['id']
            items = parse_multivalue_col(row[col_name])
            for item in items:
                records.append({'show_id': show_id, dim_name_col: item})
                
        bridge_raw = pd.DataFrame(records)
        if bridge_raw.empty:
             return pd.DataFrame(columns=[dim_id_col, dim_name_col]), pd.DataFrame(columns=['show_id', dim_id_col])
             
        dim = pd.DataFrame({dim_name_col: bridge_raw[dim_name_col].unique()})
        dim.reset_index(drop=True, inplace=True)
        dim[dim_id_col] = dim.index + 1
        
        bridge = bridge_raw.merge(dim, on=dim_name_col, how='left')
        bridge = bridge[['show_id', dim_id_col]].drop_duplicates()
        
        return dim, bridge

    # --- 4. Dim_Genre & Bridge_Show_Genre ---
    print("Building Dim_Genre & Bridge_Show_Genre...")
    dim_genre, bridge_genre = build_dim_and_bridge(df, 'genres', 'genre_id', 'genre_name')
    
    # --- 5. Dim_Creator & Bridge_Show_Creator ---
    print("Building Dim_Creator & Bridge_Show_Creator...")
    dim_creator, bridge_creator = build_dim_and_bridge(df, 'created_by', 'creator_id', 'creator_name')
    
    # --- 6. Dim_Network & Bridge_Show_Network ---
    print("Building Dim_Network & Bridge_Show_Network...")
    dim_network, bridge_network = build_dim_and_bridge(df, 'networks', 'network_id', 'network_name')
    
    # --- 7. Dim_ProductionCompany & Bridge_Show_ProductionCompany ---
    print("Building Dim_ProductionCompany & Bridge_Show_ProductionCompany...")
    dim_prod_company, bridge_prod_company = build_dim_and_bridge(df, 'production_companies', 'production_company_id', 'company_name')

    # --- 8. Fact_TV_Show ---
    print("Building Fact_TV_Show...")
    fact_tv_show = df.copy()
    fact_tv_show.rename(columns={'id': 'show_id'}, inplace=True)
    fact_tv_show['title_id'] = fact_tv_show['show_id']
    
    fact_tv_show = fact_tv_show[[
        'show_id', 'title_id', 'show_attributes_id', 'first_air_date_id', 'last_air_date_id', 
        'number_of_episodes', 'number_of_seasons', 'popularity', 'vote_average', 'vote_count'
    ]]
    
    # Convert IDs to pandas nullable integer type (Int64) to handle NaNs gracefully
    for col in ['show_attributes_id', 'first_air_date_id', 'last_air_date_id']:
        fact_tv_show[col] = fact_tv_show[col].astype('Int64')

    # --- 9. Export to CSV ---
    print("Exporting tables to CSV files...")
    
    dim_title.to_csv('Dim_Title.csv', index=False)
    dim_show_attr.to_csv('Dim_ShowAttributes.csv', index=False)
    dim_date.to_csv('Dim_Date.csv', index=False)
    dim_genre.to_csv('Dim_Genre.csv', index=False)
    dim_creator.to_csv('Dim_Creator.csv', index=False)
    dim_network.to_csv('Dim_Network.csv', index=False)
    dim_prod_company.to_csv('Dim_ProductionCompany.csv', index=False)
    
    bridge_genre.to_csv('Bridge_Show_Genre.csv', index=False)
    bridge_creator.to_csv('Bridge_Show_Creator.csv', index=False)
    bridge_network.to_csv('Bridge_Show_Network.csv', index=False)
    bridge_prod_company.to_csv('Bridge_Show_ProductionCompany.csv', index=False)
    
    fact_tv_show.to_csv('Fact_TV_Show.csv', index=False)
    
    print("ETL Process completed successfully! All files generated in the current directory.")

if __name__ == '__main__':
    main()
