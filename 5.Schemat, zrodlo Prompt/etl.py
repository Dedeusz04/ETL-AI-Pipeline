import sqlite3
import pandas as pd
import os

def main():
    source_file = 'TMDB_tv_dataset_v3.csv'
    output_dir = 'output_data'
    
    print(f"Loading data from {source_file}...")
    df = pd.read_csv(source_file)
    
    # Drop completely duplicated show IDs just in case
    df = df.drop_duplicates(subset=['id']).copy()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Processing Dim_Date...")
    df['first_air_date_dt'] = pd.to_datetime(df['first_air_date'], errors='coerce')
    df['last_air_date_dt'] = pd.to_datetime(df['last_air_date'], errors='coerce')

    all_dates = pd.concat([df['first_air_date_dt'], df['last_air_date_dt']]).dropna().unique()
    dim_date = pd.DataFrame({'full_date_dt': all_dates})
    dim_date['date_id'] = dim_date.index + 1
    dim_date['full_date'] = dim_date['full_date_dt'].dt.strftime('%Y-%m-%d')
    dim_date['year'] = dim_date['full_date_dt'].dt.year
    dim_date['month'] = dim_date['full_date_dt'].dt.month
    dim_date['day'] = dim_date['full_date_dt'].dt.day
    dim_date['quarter'] = dim_date['full_date_dt'].dt.quarter
    dim_date_out = dim_date[['date_id', 'full_date', 'year', 'month', 'day', 'quarter']]

    # Mapping dates back to df
    df = df.merge(dim_date[['full_date_dt', 'date_id']], left_on='first_air_date_dt', right_on='full_date_dt', how='left').rename(columns={'date_id': 'first_air_date_id'}).drop(columns=['full_date_dt'])
    df = df.merge(dim_date[['full_date_dt', 'date_id']], left_on='last_air_date_dt', right_on='full_date_dt', how='left').rename(columns={'date_id': 'last_air_date_id'}).drop(columns=['full_date_dt'])

    print("Processing Dim_Title...")
    title_cols = ['name', 'original_name', 'overview', 'tagline', 'status', 'type', 'original_language']
    dim_title = df[title_cols].drop_duplicates().reset_index(drop=True)
    dim_title['title_id'] = dim_title.index + 1
    df = df.merge(dim_title, on=title_cols, how='left')
    dim_title_out = dim_title[['title_id'] + title_cols]

    print("Processing Dim_ShowAttributes...")
    attr_cols = ['number_of_seasons', 'number_of_episodes', 'episode_run_time', 'in_production']
    dim_show_attributes = df[attr_cols].drop_duplicates().reset_index(drop=True)
    dim_show_attributes['show_attributes_id'] = dim_show_attributes.index + 1
    df = df.merge(dim_show_attributes, on=attr_cols, how='left')
    dim_show_attributes_out = dim_show_attributes[['show_attributes_id'] + attr_cols]

    def create_dim_and_bridge(df, column_name, dim_id_col, dim_name_col):
        s = df.set_index('id')[column_name].dropna()
        s_exploded = s.str.split(',').explode().str.strip()
        s_exploded = s_exploded[s_exploded != '']
        bridge_temp = s_exploded.reset_index()
        bridge_temp.columns = ['show_id', dim_name_col]
        
        dim_df = pd.DataFrame({dim_name_col: bridge_temp[dim_name_col].unique()})
        dim_df[dim_id_col] = dim_df.index + 1
        
        bridge_df = bridge_temp.merge(dim_df, on=dim_name_col, how='left')[['show_id', dim_id_col]].drop_duplicates()
        return dim_df[[dim_id_col, dim_name_col]], bridge_df

    print("Processing Bridges and Many-to-Many Dimensions...")
    dim_genre_out, bridge_show_genre_out = create_dim_and_bridge(df, 'genres', 'genre_id', 'genre_name')
    dim_creator_out, bridge_show_creator_out = create_dim_and_bridge(df, 'created_by', 'creator_id', 'creator_name')
    dim_network_out, bridge_show_network_out = create_dim_and_bridge(df, 'networks', 'network_id', 'network_name')
    dim_production_company_out, bridge_show_production_company_out = create_dim_and_bridge(df, 'production_companies', 'company_id', 'company_name')

    print("Processing Fact_TV_Show...")
    fact_tv_show_out = df[['id', 'title_id', 'first_air_date_id', 'last_air_date_id', 'show_attributes_id', 'popularity', 'vote_average', 'vote_count']].copy()
    fact_tv_show_out.rename(columns={'id': 'show_id'}, inplace=True)
    fact_tv_show_out['first_air_date_id'] = fact_tv_show_out['first_air_date_id'].astype('Int64')
    fact_tv_show_out['last_air_date_id'] = fact_tv_show_out['last_air_date_id'].astype('Int64')

    print("Exporting data to SQLite database...")
    print('Connecting to SQLite database hurtownia.db...')
    conn = sqlite3.connect('hurtownia.db')
    dim_date_out.to_sql('Dim_Date', conn, if_exists='replace', chunksize=10000, index=False)
    dim_title_out.to_sql('Dim_Title', conn, if_exists='replace', chunksize=10000, index=False)
    dim_show_attributes_out.to_sql('Dim_ShowAttributes', conn, if_exists='replace', chunksize=10000, index=False)
    
    dim_genre_out.to_sql('Dim_Genre', conn, if_exists='replace', chunksize=10000, index=False)
    bridge_show_genre_out.to_sql('Bridge_Show_Genre', conn, if_exists='replace', chunksize=10000, index=False)
    
    dim_creator_out.to_sql('Dim_Creator', conn, if_exists='replace', chunksize=10000, index=False)
    bridge_show_creator_out.to_sql('Bridge_Show_Creator', conn, if_exists='replace', chunksize=10000, index=False)
    
    dim_network_out.to_sql('Dim_Network', conn, if_exists='replace', chunksize=10000, index=False)
    bridge_show_network_out.to_sql('Bridge_Show_Network', conn, if_exists='replace', chunksize=10000, index=False)
    
    dim_production_company_out.to_sql('Dim_ProductionCompany', conn, if_exists='replace', chunksize=10000, index=False)
    bridge_show_production_company_out.to_sql('Bridge_Show_ProductionCompany', conn, if_exists='replace', chunksize=10000, index=False)
    
    fact_tv_show_out.to_sql('Fact_TV_Show', conn, if_exists='replace', chunksize=10000, index=False)

    conn.close()
    print("ETL Process completed successfully!")

if __name__ == '__main__':
    main()
