# Wykorzystanie metod AI do projektowania procesu ETL 

Głównym celem projektu jest zbadanie możliwości autogeneracji kodu procesu ETL przez LLM na podstawie zadanego formatu zbioru danych wejściowych oraz docelowego modelu danych. Eksperyment polega na generowaniu potoku ETL przy wykorzystaniu promptów o różnym poziomie szczegółowości, a następnie na porównaniu jakości otrzymanych rozwiązań.

Jako dane wejściowe wykorzystano plik `TMDB_tv_dataset_v3.csv`, a proces ETL jest realizowany w środowisku Python z wykorzystaniem biblioteki `pandas`. Model LLM użyty w analizie to Google Gemini 3 Pro High.

## Jak to uruchomić?

Wymagana jest tylko instalacja biblioteki pandas:
```bash
pip install pandas
```

Skrypty wygenerowane przez AI dla poszczególnych wariantów promptów znajdują się w odpowiadających im folderach. Aby uruchomić wybrany wariant:
```bash
cd "1.Minimal Prompt"
python3 etl.py
```
Gotowe i przetworzone pliki CSV pojawią się wewnątrz folderu po wykonaniu skryptu.

---

## Wyniki Analizy i Ewaluacja

Dla każdego z wariantów wygenerowany został kod procesu ETL, który był uruchamiany i oceniany na podstawie określonych w projekcie metryk jakościowych.

### 1. Zachowanie danych 
*(Wskaźnik zachowania danych - procent rekordów poprawnie przeniesionych z danych źródłowych do hurtowni danych)*

Sprawdzono, ile wierszy z oryginalnego CSV (168 639 rekordów) trafiło do wygenerowanej tabeli faktów. Relacja serial -> fakt to 1:1, więc docelowa tabela powinna mieć dokładnie tyle samo wierszy.

* **P1 Minimalny**: Okazało się, że skrypt wygenerował własne dane (4 rekordy). Baza źródłowa została całkowicie pominięta z powodu błędu ścieżki.
* **P2, P3, P4, P6**: Skrypty przepisały 100% danych, bez żadnych strat.
* **P5, P7**: Zauważalne straty (w P5 zostało 164 705 wierszy, w P7 167 059). 

**Wniosek:** AI bywa nadgorliwe. W P5 i P7 skrypty z automatu wywoływały metody typu `.dropna()`, ucinając wiersze z brakami danych (np. brak daty premiery). To pokazuje, że bez wyraźnego zakazu w prompcie, model ma tendencję do cichego czyszczenia danych "po swojemu", co zaburza statystyki.

### 2. Integralność powiązań
*(Integralność - procent poprawnie utworzonych powiązań pomiędzy tabelą faktów a tabelami wymiarów)*

Pod kątem integralności wszystkie wygenerowane skrypty spisały się wzorowo. Zastosowanie funkcji `merge()` oraz standardowego mapowania w pandas sprawia, że nie powstają tzw. wolne elektrony. Każdy klucz obcy w tabeli faktów miał odpowiednik w wygenerowanych tabelach wymiarów. Można przyjąć, że w tym aspekcie kod z AI jest bezpieczny.

### 3. Mapowanie relacji N:M 
*(Pokrycie relacji N:M - stopień poprawności odwzorowania relacji wiele-do-wielu poprzez tabele pośrednie)*

Kluczowym elementem schematu było utworzenie tabel pośrednich N:M dla pól, w których dane były wymienione po przecinku w jednej komórce (np. gatunki, twórcy).

* **P1**: Skrypt założył najprostszy scenariusz i stworzył tylko jeden mostek dla gatunków. Resztę zignorował, bo po prostu zabrakło mu detali w prompcie.
* **P2-P7**: Model poprawnie zaimplementował wszystkie 4 tabele mostkowe. Zgodność ze schematem hurtowni została w pełni zachowana od wariantu 2 wzwyż.

**Wniosek:** Wystarczyło lekko uszczegółowić prompt (nawet bez wchodzenia w szczegóły, jak w P2), żeby model bezbłędnie wyłapał wzorzec i poprawnie rozbił listy z przecinkami na tabele asocjacyjne.

### 4. Odtwarzalność procesu
*(Odtwarzalność procesu - sprawdzenie, czy wielokrotne uruchomienie wygenerowanego kodu nie powoduje błędów, duplikacji danych ani naruszenia integralności bazy)*

Skrypty z Wariantów 2-7 zostały wygenerowane w taki sposób, że każde odpalenie nadpisuje wygenerowane pliki CSV (parametr `index=False` w `to_csv`). Sprawia to, że kod jest odporny i można go odpalać wielokrotnie bez obawy o powielenie danych.

### 5. Odporność na błędy 
*(Liczba błędów wykonania - liczba błędów pojawiających się podczas pierwszego uruchomienia wygenerowanego kodu)*

* **P1, P2, P3**: Model na sztywno hardkodował ścieżki do pliku wejściowego (zakładał, że CSV leży w tym samym folderze co `etl.py`). Skutkowało to od razu rzucaniem wyjątku `FileNotFoundError` przy pierwszym uruchomieniu.
* **P4**: Pojawił się błąd `KeyError` podczas wykonywania skryptu. AI przyjęło, że skoro w hurtowni robimy `Dim_Creator`, to w surowym CSV też na pewno jest kolumna `creators`. W rzeczywistości kolumna nazywała się `created_by`. Klasyczny przykład halucynacji modelu.
* **P5-P7**: Skrypty wykonały się gładko za pierwszym razem, bez rzucania błędami w konsoli.

### Podsumowanie i wnioski
Patrząc z inżynierskiego punktu widzenia, najwięcej problemów w wygenerowanych procesach sprawiały dwie rzeczy: halucynacje nazw kolumn oraz twarde hardkodowanie lokalnych ścieżek do plików. 

Najlepiej w testach wypadł **prompt P6**, skrypt nie rzucił żadnym błędem, zbudował architekturę 1:1 z założeniami i nie zgubił ani jednego rekordu. Co ciekawe, podrzucenie jeszcze większej ilości tekstu do analizy (**prompt P7**) wcale nie pomogło. Wręcz przeciwnie, model uznał, że zrobi nam przysługę i sam trochę "zoptymalizuje" bazę wyrzucając nulle, przez co usunięto ok. 1% poprawnych rekordów.

Wniosek końcowy: najlepszy prompt do zadań ETL to taki, który wymusza konkretną, twardą strukturę bazy, ale **blokuje** modelowi inicjatywę w kwestii samodzielnego, nieautoryzowanego czyszczenia danych. Do zapytań warto też zawsze wklejać nagłówki oryginalnego pliku, żeby skrypty nie wywalały się na prostych literówkach w nazwach kolumn.

---

## Dodatek: Zestawienie użytych wariantów promptów

Przygotowano 7 wariantów promptów o rosnącym poziomie szczegółowości. Poniżej znajduje się kompletna lista użytych zapytań. Tam, gdzie pojawia się znacznik [ZAŁĄCZ ZDJĘCIE DIAGRAMU], do zapytania bezpośrednio załączany był zrzut ekranu wizualnego schematu bazy danych.

### Wariant 1
*(jedynie ogólny opis zadania polegającego na przygotowaniu procesu ETL dla danych o serialach telewizyjnych, bez dodatkowego kontekstu, schematu danych.)*

> Napisz mi skrypt w Pythonie, który zrobi proces ETL dla bazy seriali z pliku CSV. Podziel to na tabele faktów i wymiarów i wypluj jako nowe pliki CSV.

### Wariant 2
*(zawierający opis tabel hurtowni danych i ich atrybutów, bez relacji między tabelami, bez diagramu oraz bez szczegółowych wymagań technicznych.)*

> Napisz mi skrypt ETL w Pythonie, który wrzuci dane z pliku "TMDB_tv_dataset_v3.csv" do hurtowni. Hurtownia ma mieć dokładnie takie tabele i ani jednej więcej:
> Fact_TV_Show: show_id, title_id, first_air_date_id, last_air_date_id, show_attributes_id, popularity, vote_average, vote_count.
> Dim_Title: title_id, name, original_name, overview, tagline, status, type, original_language.
> Dim_Date: date_id, full_date, year, month, day, quarter.
> Dim_ShowAttributes: show_attributes_id, number_of_seasons, number_of_episodes, episode_run_time, in_production.
> Dim_Genre: genre_id, genre_name.
> Bridge_Show_Genre: show_id, genre_id.
> Dim_Creator: creator_id, creator_name.
> Bridge_Show_Creator: show_id, creator_id.
> Dim_Network: network_id, network_name.
> Bridge_Show_Network: show_id, network_id.
> Dim_ProductionCompany: company_id, company_name.
> Bridge_Show_ProductionCompany: show_id, company_id.
> Zapisz to wszystko do osobnych CSV.

### Wariant 3
*(zawierający opis tabel oraz relacji pomiędzy nimi, w tym relacji 1:N oraz N:M, bez schematu graficznego oraz bez dodatkowego kontekstu.)*

> Mam zdenormalizowany plik CSV z serialami ("TMDB_tv_dataset_v3.csv"). Napisz mi skrypt ETL w Pythonie, który zbuduje z tego schemat gwiazdy.
> Oczekiwana struktura docelowa tabel:
> Fact_TV_Show: show_id, title_id, first_air_date_id, last_air_date_id, show_attributes_id, popularity, vote_average, vote_count.
> Dim_Title: title_id, name, original_name, overview, tagline, status, type, original_language.
> Dim_Date: date_id, full_date, year, month, day, quarter.
> Dim_ShowAttributes: show_attributes_id, number_of_seasons, number_of_episodes, episode_run_time, in_production.
> Dim_Genre: genre_id, genre_name.
> Dim_Creator: creator_id, creator_name.
> Dim_Network: network_id, network_name.
> Dim_ProductionCompany: company_id, company_name.
>
> Główną tabelą jest Fact_TV_Show. Ta tabela łączy się relacjami 1:N z wymiarami: Dim_Title po title_id, Dim_ShowAttributes po show_attributes_id i dwa razy z Dim_Date po first_air_date_id i last_air_date_id.
> 
> Seriale mają też atrybuty, gdzie w jednej komórce jest po kilka wartości np. gatunki po przecinku. Musisz to ogarnąć robiąc relacje N:M przez tabele mostkowe bridge:
> Gatunki przez Bridge_Show_Genre (show_id, genre_id) do Dim_Genre.
> Twórcy przez Bridge_Show_Creator (show_id, creator_id) do Dim_Creator.
> Sieci TV przez Bridge_Show_Network (show_id, network_id) do Dim_Network.
> Produkcje przez Bridge_Show_ProductionCompany (show_id, company_id) do Dim_ProductionCompany.
> 
> Wyciągnij to ze źródła, połącz jak trzeba i zapisz jako CSVki.

### Wariant 4
*(zawierający schemat hurtowni danych w postaci diagramu oraz krótki opis zadania, bez szczegółowego opisu tabel i bez specyfikacji technicznej.)*

> [ZAŁĄCZ ZDJĘCIE DIAGRAMU Z OBRAZKA dbdiagram.io]
> 
> Masz na obrazku projekt hurtowni danych z serialami. Napisz mi skrypt w Pythonie, który weźmie jakiś przykładowy plik CSV i wygeneruje z niego taką strukturę tabel, jak widać na schemacie. Zapisz wynikowe tabele na dysk.

### Wariant 5
*(zawierający schemat hurtowni danych wraz z informacją o źródle danych, bez pełnego opisu relacji i wymagań funkcjonalnych.)*

> [ZAŁĄCZ ZDJĘCIE DIAGRAMU]
> 
> Twoim zadaniem jest przerzucenie danych z pliku TMDB_tv_dataset_v3.csv do modelu hurtowni z załączonego obrazka. W pliku źródłowym masz kolumny takie jak name, genres, created_by, first_air_date, number_of_seasons, czy vote_count. Napisz mi w Pythonie najlepiej w pandasie potok ETL, który przekształci ten płaski CSV, połączy wszystko tak jak na rysunku i wyeksportuje jako zestaw plików csv.

### Wariant 6
*(zawierający pełny kontekst projektu, schemat hurtowni danych, opis modelu oraz oczekiwane funkcjonalności procesu ETL, bez szczegółowej specyfikacji technicznej implementacji.)*

> [ZAŁĄCZ ZDJĘCIE DIAGRAMU]
> 
> Robię projekt na uczelnię z hurtowni danych o serialach z bazy TMDB (TMDB_tv_dataset_v3.csv). Muszę dostarczyć bazę, w której analitycy będą mogli łatwo liczyć popularność i oceny dla poszczególnych gatunków, studiów i lat.
> 
> Załączony schemat pokazuje dokładnie, jak to ma wyglądać. Główna tabela to Fact_TV_Show z liczbami. Zwróć uwagę, że seriale mają po kilka wartości w jednej komórce (genres, networks, oddzielone przecinkami w CSV). Dlatego na schemacie zrobiłem układ płatka śniegu i mostki do relacji N:M np. Bridge_Show_Genre.
> 
> Napisz skrypt w Pythonie (Pandas). Ma on robić:
> Rozbijanie list po przecinkach np. explode, żeby zbudować tabele pomostowe dla N:M.
> Ogarnięcie dat i zrobienie porządnego wymiaru czasu (rok, miesiąc, kwartał).
> Bezpieczną zamianę typów np. liczby sezonów czy czasu trwania na inty, usuwając po drodze śmieci tekstowe.

### Wariant 7
*(kompletny, zawierający pełną specyfikację techniczną, diagram modelu, opis datasetu, wymagania dotyczące integralności danych, obsługi relacji N:M oraz założeń dotyczących wielokrotnego uruchamiania procesu ETL.)*

> [ZAŁĄCZ ZDJĘCIE DIAGRAMU]
> 
> Wygeneruj mi skrypt ETL w Pythonie ładujący TMDB_tv_dataset_v3.csv do bazy z załączonego diagramu. To ma działać produkcyjnie, więc trzymaj się tych wytycznych technologicznych:
> 
> Framework: Użyj pandasa i metody explode, żeby dobrze obsłużyć relacje N:M. Listy z przecinkami mapuj na IDki w tabelach mostkowych.
> Dim_Date: Zrób ID daty w formacie YYYYMMDD. Jak jakiejś daty brakuje, to wstaw nulle i podepnij pod sztuczną datę błędu 99991231, a samą datę przeparsuj przez pd.to_datetime().
> Czyszczenie liczb: Czas trwania odcinka episode_run_time bywa zaśmiecony tekstowo. Użyj regexa albo astype, żeby wyciągnąć samego inta i żeby skrypt nie wywalił ValueError.
> Bool: Przerób in_production z tekstu True/False na normalny boolean.
> Idempotentność: Skrypt ma się odpalać za każdym razem tak samo i nie robić duplikatów. Używaj drop_duplicates, usuwaj stare pliki przed nadpisaniem i zrzucaj do csv z flagą index=False.
> Klucze: Numeruj wymiary normalnie od 1 w górę w pętli dla wszystkich _id ze schematu, żeby klucze były spójne i żeby nic nam z bazy nie wyciekło.
