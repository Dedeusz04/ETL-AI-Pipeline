import pandas as pd
import os

def extract(file_path):
    print(f"Rozpoczęto ekstrakcję danych z {file_path}")
    try:
        df = pd.read_csv(file_path)
        print(f"Pomyślnie załadowano {len(df)} wierszy.")
        return df
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku {file_path}. Zostaną wygenerowane dane przykładowe.")
        return generate_sample_data(file_path)

def generate_sample_data(file_path):
    data = {
        'id': [1, 2, 3, 4],
        'name': ['Breaking Bad', 'Game of Thrones', 'Stranger Things', 'The Wire'],
        'first_air_date': ['2008-01-20', '2011-04-17', '2016-07-15', '2002-06-02'],
        'original_language': ['en', 'en', 'en', 'en'],
        'genre': ['Drama, Crime', 'Sci-Fi & Fantasy, Drama', 'Sci-Fi & Fantasy, Mystery', 'Drama, Crime'],
        'popularity': [85.5, 100.0, 95.2, 70.1],
        'vote_average': [9.3, 9.2, 8.7, 9.3],
        'vote_count': [15000, 20000, 18000, 9000]
    }
    df = pd.DataFrame(data)
    # Zapisz przykładowe dane do pliku, aby posłużyły jako źródło w kolejnych uruchomieniach
    df.to_csv(file_path, index=False)
    print(f"Wygenerowano przykładowy plik źródłowy: {file_path}")
    return df

def transform(df):
    print("Rozpoczęto transformację danych...")
    
    # 1. Wymiar Seriali (Dim_Series)
    dim_series = df[['id', 'name', 'first_air_date', 'original_language']].copy()
    dim_series.rename(columns={'id': 'series_id', 'name': 'title'}, inplace=True)
    # Normalizacja daty
    dim_series['first_air_date'] = pd.to_datetime(dim_series['first_air_date'], errors='coerce')
    
    # 2. Wymiar Gatunków (Dim_Genre)
    # Rozdzielenie gatunków i znalezienie unikalnych
    genres_series = df['genre'].dropna().str.split(', ').explode().unique()
    dim_genre = pd.DataFrame({'genre_id': range(1, len(genres_series) + 1), 'genre_name': genres_series})
    
    # Tabela mapująca Seriale i Gatunki (Bridge_Series_Genre)
    # Ponieważ serial może mieć wiele gatunków, wykorzystujemy tabele mostkową (bridge table)
    series_genre_mapping = []
    for idx, row in df.iterrows():
        series_id = row['id']
        if pd.notna(row['genre']):
            genres = row['genre'].split(', ')
            for genre in genres:
                genre_id = dim_genre.loc[dim_genre['genre_name'] == genre, 'genre_id'].values[0]
                series_genre_mapping.append({'series_id': series_id, 'genre_id': genre_id})
                
    bridge_series_genre = pd.DataFrame(series_genre_mapping)
    
    # 3. Tabela Faktów (Fact_Series_Stats)
    fact_stats = df[['id', 'popularity', 'vote_average', 'vote_count']].copy()
    fact_stats.rename(columns={'id': 'series_id'}, inplace=True)
    # Obliczenie przykładowej dodatkowej metryki, np. ważonej oceny
    fact_stats['weighted_score'] = (fact_stats['vote_average'] * fact_stats['vote_count']) / fact_stats['vote_count'].max()
    
    print("Transformacja zakończona sukcesem.")
    return {
        'Dim_Series': dim_series,
        'Dim_Genre': dim_genre,
        'Bridge_Series_Genre': bridge_series_genre,
        'Fact_Series_Stats': fact_stats
    }

def load(tables_dict, output_dir):
    print(f"Rozpoczęto ładowanie danych do katalogu '{output_dir}'...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Utworzono katalog wyjściowy: {output_dir}")
        
    for table_name, df in tables_dict.items():
        output_path = os.path.join(output_dir, f"{table_name}.csv")
        df.to_csv(output_path, index=False)
        print(f" -> Zapisano tabelę {table_name} do {output_path}")
        
    print("Ładowanie danych zakończone sukcesem.")

def main():
    source_file = 'tv_series_source.csv'
    output_directory = 'etl_output'
    
    print("--- Start procesu ETL ---")
    
    # Extract
    raw_data = extract(source_file)
    
    # Transform
    transformed_tables = transform(raw_data)
    
    # Load
    load(transformed_tables, output_directory)
    
    print("--- Koniec procesu ETL ---")

if __name__ == "__main__":
    main()
