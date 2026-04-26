# AI ETL Pipeline 

Głównym celem jest użycie modelu AI do autowygenerowania i zaplanowania kodu przekształcającego  brudne dane w ustrukturyzowany model **Hurtowni Danych**.

Jako dane wejściowe wykorzystaliśmy publicznie udostępniony plik `netflix_titles.csv`, który potraktowaliśmy za pomocą biblioteki `pandas` środowiska Python.

## Czego potrzebujesz?
Aby projekt zadziałał, jedyne co musisz zainstalować to najnowszy bliotekę pandas:
```bash
pip install pandas
```

## Jak to odpalić? 

**1. Faza E&T**
Odpal ten skrypt jako pierwszy.
```bash
python 1_clean_and_transform.py
```

**2. Faza Modelowania i Ładowania**
Odpal ten skrypt jako drugi.
```bash
python 2_build_data_warehouse.py
```

 Gotowe i przetworzone pliki CSV pojawią się w folderze.
