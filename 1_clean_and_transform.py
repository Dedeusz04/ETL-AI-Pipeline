import pandas as pd
import re

print("\n=== FAZA 1: Czyszczenie i Transformacja (E & T) ===")
# EXTRACT
try:
    df = pd.read_csv('netflix_titles.csv')
    print(f"[1] Pobrano brudną bazę wejściową z dysku. Liczba wierszy: {len(df)}")
except Exception as e:
    print(f"Błąd podczas wczytywania: {e}")
    exit(1)


# TRANSFORM 
print("[2] Rozpoczynam naprawianie błędów i literówek w danych (Transform)...")

# Czyszczenie dat z tekstu
df['date_added_clean'] = pd.to_datetime(df['date_added'].str.strip(), format='%B %d, %Y', errors='coerce')

# Wyciąganie samego intigera z czasu trwania 
def extract_duration(val):
    if pd.isna(val):
        return None
    match = re.search(r'\d+', str(val))
    return int(match.group()) if match else None

df['duration_numeric'] = df['duration'].apply(extract_duration)

# Generowanie klucza czasowego
df['date_id'] = df['date_added_clean'].dt.strftime('%Y%m%d')

# Zapisanie "pół-produktu" do pliku tymczasowego
df.to_csv('cleaned_netflix_temp.csv', index=False)
print("[3] Zakończono proces wstępnego czyszczenia i zapisano na dysku 'cleaned_netflix_temp.csv'.")
print("=== KONIEC FAZY 1 ===\n")
