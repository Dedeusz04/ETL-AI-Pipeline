# AI ETL Pipeline z użyciem Pandas 🚀

Ten projekt został stworzony na zaliczenie u dr inż. Anny Gorawskiej. 
Głównym celem było użycie modelu AI do autowygenerowania i zaplanowania logicznego kodu przekształcającego (transformującego) brudne dane w ustrukturyzowany model **Hurtowni Danych (Schemat Gwiazdy)**.

Jako dane wejściowe wykorzystaliśmy publicznie udostępniony plik `netflix_titles.csv`, który potraktowaliśmy za pomocą biblioteki `pandas` środowiska Python.

## Czego potrzebujesz?
Aby projekt zadziałał, jedyne co musisz zainstalować to najnowszy bliotekę pandas:
```bash
pip install pandas
```

## Jak to odpalić? 🤔
Projekt dla profesjonalizmu został rozbity na 2-fazowy potok (tzw. Pipeline) w kodzie Python, gdzie logika oddziela ekstrakcję od modelowania.

**1. Faza E&T (Ekstrakcja i Transformacja)**
Odpal ten skrypt jako pierwszy, aby załadować plik wejściowy (Extract), wyczyścić daty, wyrzucić brzydkie napisy (typu "Seasons" i "min") programując formaty na liczby (Transform). Powstanie plik pośredni.
```bash
python 1_clean_and_transform.py
```

**2. Faza Modelowania i Ładowania (Data Warehouse & Load)**
Odpal ten skrypt jako drugi. Czyta wyczyszczone dane i rozbija je logicznie na docelowy model Schematu Gwiazdy (dzieli zbiór na Fakty oraz Wymiary Czasu i Reżysera).
```bash
python 2_build_data_warehouse.py
```

I... to tyle! Gotowe i przetworzone pliki CSV pojawią się w folderze, skąd błyskawicznie można je zasilać np. do systemów takich jak PowerBI czy Tableau 📊.
