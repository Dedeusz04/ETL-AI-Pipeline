import pandas as pd
import ast

def parse_list_col(val, key_id, key_name):
    """
    Parses complex list/JSON columns from TMDB datasets into a list of dicts.
    Handles stringified list of dicts, or comma-separated strings.
    """
    if pd.isna(val) or val == '' or val == '[]':
        return []
    try:
        # Check if it's a JSON-like string of dicts
        parsed = ast.literal_eval(val)
        if isinstance(parsed, list):
            if len(parsed) > 0 and isinstance(parsed[0], dict):
                # Extract id and name if they exist
                return [{'id': item.get('id'), 'name': item.get('name')} for item in parsed]
            else:
                return [{'name': str(item)} for item in parsed]
    except (ValueError, SyntaxError):
        pass
    
    # Fallback for comma-separated strings
    items = [x.strip() for x in str(val).split(',')]
    return [{'name': item} for item in items if item]

def process_etl():
    print("Loading data...")
    try:
        df = pd.read_csv('TMDB_tv_dataset_v3.csv')
    except FileNotFoundError:
        print("Error: TMDB_tv_dataset_v3.csv not found in the current directory.")
        return

    # Assuming the main identifier column in dataset is 'id'
    if 'id' in df.columns:
        df = df.rename(columns={'id': 'show_id'})
    elif 'show_id' not in df.columns:
        # If no id column, create one
        df['show_id'] = range(1, len(df) + 1)
    
    # ---------------------------------------------------------
    # 1. Dim_Title
    # ---------------------------------------------------------
    print("Building Dim_Title...")
    title_cols = ['name', 'original_name', 'overview', 'tagline', 'status', 'type', 'original_language']
    for col in title_cols:
        if col not in df.columns:
            df[col] = None
            
    dim_title = df[['show_id'] + title_cols].copy()
    dim_title = dim_title.rename(columns={'show_id': 'title_id'})
    # Dim_Title is 1:1 with show, so we use show_id as title_id
    
    # ---------------------------------------------------------
    # 2. Dim_Date
    # ---------------------------------------------------------
    print("Building Dim_Date...")
    if 'first_air_date' not in df.columns: df['first_air_date'] = None
    if 'last_air_date' not in df.columns: df['last_air_date'] = None
    
    dates = pd.concat([df['first_air_date'], df['last_air_date']]).dropna().unique()
    dim_date = pd.DataFrame({'full_date': dates})
    dim_date['full_date'] = pd.to_datetime(dim_date['full_date'], errors='coerce')
    dim_date = dim_date.dropna(subset=['full_date']).drop_duplicates().sort_values('full_date')
    
    # Create date_id as YYYYMMDD
    dim_date['date_id'] = dim_date['full_date'].dt.strftime('%Y%m%d').astype(int)
    dim_date['year'] = dim_date['full_date'].dt.year
    dim_date['month'] = dim_date['full_date'].dt.month
    dim_date['day'] = dim_date['full_date'].dt.day
    dim_date['quarter'] = dim_date['full_date'].dt.quarter
    dim_date['full_date'] = dim_date['full_date'].dt.strftime('%Y-%m-%d')
    dim_date = dim_date[['date_id', 'full_date', 'year', 'month', 'day', 'quarter']]
    
    # Helpers to map dates to IDs
    date_map = dict(zip(dim_date['full_date'], dim_date['date_id']))
    def get_date_id(date_val):
        if pd.isna(date_val): return None
        try:
            d = pd.to_datetime(date_val).strftime('%Y-%m-%d')
            return date_map.get(d, None)
        except:
            return None
            
    # ---------------------------------------------------------
    # 3. Dim_ShowAttributes
    # ---------------------------------------------------------
    print("Building Dim_ShowAttributes...")
    attr_cols = ['number_of_seasons', 'number_of_episodes', 'episode_run_time', 'in_production']
    for col in attr_cols:
        if col not in df.columns:
            df[col] = None
            
    dim_show_attr = df[attr_cols].drop_duplicates().reset_index(drop=True)
    dim_show_attr.insert(0, 'show_attributes_id', dim_show_attr.index + 1)
    
    # Merge back to get show_attributes_id for the fact table
    df_attr_mapped = df[['show_id'] + attr_cols].merge(dim_show_attr, on=attr_cols, how='left')
    
    # ---------------------------------------------------------
    # 4. Multi-valued dimensions
    # ---------------------------------------------------------
    def build_dim_and_bridge(col_name, dim_id_col, dim_name_col, show_id_col='show_id'):
        print(f"Building {col_name} dimension and bridge...")
        if col_name not in df.columns:
            return pd.DataFrame(columns=[dim_id_col, dim_name_col]), pd.DataFrame(columns=[show_id_col, dim_id_col])
            
        dim_data = []
        bridge_data = []
        
        for idx, row in df.iterrows():
            show_id = row['show_id']
            val = row[col_name]
            parsed = parse_list_col(val, dim_id_col, dim_name_col)
            
            for item in parsed:
                dim_data.append(item)
                bridge_item = {show_id_col: show_id}
                if item.get('id') is not None:
                    bridge_item[dim_id_col] = item['id']
                else:
                    bridge_item['_temp_name'] = item['name']
                bridge_data.append(bridge_item)
                
        # Create dimension DataFrame
        dim_df = pd.DataFrame(dim_data).drop_duplicates(subset=['name']).dropna(subset=['name']).reset_index(drop=True)
        
        if dim_df.empty:
            return pd.DataFrame(columns=[dim_id_col, dim_name_col]), pd.DataFrame(columns=[show_id_col, dim_id_col])

        if 'id' not in dim_df.columns:
            dim_df['id'] = dim_df.index + 1
        else:
            # Fill missing IDs safely
            missing_mask = dim_df['id'].isna()
            dim_df.loc[missing_mask, 'id'] = dim_df.index[missing_mask] + 100000
            dim_df['id'] = dim_df['id'].astype(int)
            
        dim_df = dim_df.rename(columns={'id': dim_id_col, 'name': dim_name_col})
        dim_df = dim_df[[dim_id_col, dim_name_col]]
        
        # Create bridge DataFrame
        bridge_df = pd.DataFrame(bridge_data)
        if not bridge_df.empty:
            if '_temp_name' in bridge_df.columns:
                name_to_id = dict(zip(dim_df[dim_name_col], dim_df[dim_id_col]))
                mask = bridge_df.get(dim_id_col, pd.Series(dtype=object)).isna() & bridge_df['_temp_name'].notna()
                bridge_df.loc[mask, dim_id_col] = bridge_df.loc[mask, '_temp_name'].map(name_to_id)
                bridge_df = bridge_df.drop(columns=['_temp_name'])
                
            bridge_df = bridge_df.dropna(subset=[dim_id_col]).drop_duplicates()
            bridge_df[dim_id_col] = bridge_df[dim_id_col].astype(int)
            
        return dim_df, bridge_df

    dim_genre, bridge_genre = build_dim_and_bridge('genres', 'genre_id', 'genre_name')
    dim_creator, bridge_creator = build_dim_and_bridge('created_by', 'creator_id', 'creator_name')
    dim_network, bridge_network = build_dim_and_bridge('networks', 'network_id', 'network_name')
    dim_company, bridge_company = build_dim_and_bridge('production_companies', 'company_id', 'company_name')
    
    # ---------------------------------------------------------
    # 5. Fact_TV_Show
    # ---------------------------------------------------------
    print("Building Fact_TV_Show...")
    fact_cols = ['popularity', 'vote_average', 'vote_count']
    for col in fact_cols:
        if col not in df.columns:
            df[col] = None
            
    fact_show = pd.DataFrame({
        'show_id': df['show_id'],
        'title_id': dim_title['title_id'],
        'first_air_date_id': df['first_air_date'].apply(get_date_id),
        'last_air_date_id': df['last_air_date'].apply(get_date_id),
        'show_attributes_id': df_attr_mapped['show_attributes_id'],
        'popularity': df['popularity'],
        'vote_average': df['vote_average'],
        'vote_count': df['vote_count']
    })
    
    # Convert IDs to nullable integers
    for col in ['first_air_date_id', 'last_air_date_id', 'show_attributes_id']:
        fact_show[col] = fact_show[col].astype('Int64')

    # ---------------------------------------------------------
    # 6. Save to CSV
    # ---------------------------------------------------------
    print("Saving to CSV files...")
    fact_show.to_csv('Fact_TV_Show.csv', index=False)
    dim_title.to_csv('Dim_Title.csv', index=False)
    dim_date.to_csv('Dim_Date.csv', index=False)
    dim_show_attr.to_csv('Dim_ShowAttributes.csv', index=False)
    dim_genre.to_csv('Dim_Genre.csv', index=False)
    bridge_genre.to_csv('Bridge_Show_Genre.csv', index=False)
    dim_creator.to_csv('Dim_Creator.csv', index=False)
    bridge_creator.to_csv('Bridge_Show_Creator.csv', index=False)
    dim_network.to_csv('Dim_Network.csv', index=False)
    bridge_network.to_csv('Bridge_Show_Network.csv', index=False)
    dim_company.to_csv('Dim_ProductionCompany.csv', index=False)
    bridge_company.to_csv('Bridge_Show_ProductionCompany.csv', index=False)
    
    print("ETL Process completed successfully!")

if __name__ == "__main__":
    process_etl()
