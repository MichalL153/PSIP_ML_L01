# PSIP_ML_L01
- Michał- biłgorajski
- Jakub - chełmski
- Jan - miński
- Tymoteusz - toruński
- Dominik - koniński
- Stanisław - turecki
- Marcin - miński
- Bartek - radomszczański
- Kacper - legnicki
- Daniel - sochaczewski
- Julia - hajnowski
- Dawid - bocheński

## Laboratorium 2

Zakres: zadanie 1 oraz zadanie 2 do punktu 3 włącznie. Dane wejściowe
pozostają bez zmian: `data/powiat.shp` zawiera powiat bocheński, TERYT 1201.
To świadomy wybór dla tej realizacji; powyższa lista przydziałów z zajęć 1
pozostaje historyczną listą zespołu.

### Środowiska

| Branch | Projekt Compose | Wolumen bazy | Port w DinD | Port na Windows |
| --- | --- | --- | --- | --- |
| env-test | remote-db-env-test | remote-db-env-test-pgdata | 5444 | 127.0.0.1:5544 |
| env-qa | remote-db-env-qa | remote-db-env-qa-pgdata | 5445 | 127.0.0.1:5545 |
| main (prod) | remote-db-main | remote-db-main-pgdata | 5446 | 127.0.0.1:5546 |

Bazy działają w silniku Docker-in-Docker, dlatego są widoczne przez
`docker exec psip-github-runner docker ps`. Zewnętrzne kontenery w Docker
Desktop to `psip-docker-engine` i `psip-github-runner`.
Istniejące kontenery z laboratorium 1 mają osobne dane i porty.

### Runner i GitHub Actions

`docker-compose-runner.yml` uruchamia lokalnego runnera z etykietą `psip-lab`
oraz DinD. Połączenie używa TLS na porcie 2376. Nazwa `docker-engine` jest
uwzględniona w certyfikacie. Wolumen roboczy `/workspace` jest zamontowany
pod tą samą ścieżką w obu kontenerach, co umożliwia poprawne bind mounty
kodu i danych w zagnieżdżonym Dockerze. Rejestracja runnera jest zachowywana
w osobnym wolumenie `runner-state`.

DinD używa serwera DNS Docker Desktop `192.168.65.7`, potwierdzonego na tym
komputerze. Na innym komputerze można zmienić `DOCKER_DNS` w `.env` na adres
z `/etc/resolv.conf` zwykłego kontenera. Zapobiega to użyciu niedostępnych
publicznych resolverów wewnątrz zagnieżdżonych kontenerów.

Przy pierwszej rejestracji ustaw w bieżącej sesji PowerShell `RUNNER_TOKEN`
na krótkotrwały token rejestracyjny GitHuba (Settings → Actions → Runners),
uruchom `docker compose -f docker-compose-runner.yml up -d`, a potem usuń
zmienną przez `Remove-Item Env:RUNNER_TOKEN`. Tokena nie zapisuj w kodzie.
Przy późniejszym uruchomieniu istniejącej rejestracji wystarczy tymczasowa
wartość `RUNNER_TOKEN=reuse-existing-registration`, wymagana tylko do
walidacji Compose. Usunięcie wolumenu `runner-state` wymaga nowej rejestracji.
Jeżeli do ćwiczenia utworzono klasyczny PAT, usuń go po cyklu zajęć zgodnie
z wytycznymi prowadzącego.

Sekrety repozytorium: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
Środowiska GitHuba: `env-test`, `env-qa`, `main`. Hasło lokalne jest wyłącznie
w ignorowanym `.env`. Plik `.env.example` pokazuje nazwy zmiennych.

- `start_services.yml`: push na dany branch uruchamia jego bazę, importuje
  granicę i siatki, a następnie sprawdza geometrię i pokrycie. Dostępne jest
  także ręczne uruchomienie ze wskazaniem środowiska.
- `stop_services.yml`: ręczne zatrzymanie wybranego środowiska; dane zostają.
- `destroy_services.yml`: ręczne usunięcie wybranego projektu razem z jego
  wolumenem. Wymaga wpisania dokładnej nazwy projektu w polu `confirmation`.
- `checks.yml`: kontrola workflow i testy generatora na runnerze GitHuba.

Workflow korzystające z lokalnego runnera wykonują się tylko dla właściciela
tego repozytorium. Pull requesty nie uruchamiają kodu na lokalnym runnerze.
Operacje dla jednego środowiska są kolejkowane, także między workflow.
Ręczne workflow są dostępne w zakładce Actions po trafieniu na branch domyślny.

### Generator H3 i import danych

`app/python/h3_generator.py` odczytuje dokładnie jeden powiat, przelicza
współrzędne do EPSG:4326 i generuje kolejne rozdzielczości H3: 6, 7 i 8.
Większa rozdzielczość oznacza mniejsze komórki. Wybierane są pełne komórki
przecinające powiat, także wzdłuż granic. Nie są przycinane, aby zachować
kształt H3. Z tego powodu część komórek wykracza poza granicę powiatu.
Biblioteka H3 4.3.1 jest przypięta ze względu na używany eksperymentalny
tryb `overlap`. Lista rozdzielczości może być zmieniona przez `H3_RESOLUTIONS`.

`app/load.py` pobiera połączenie wyłącznie ze zmiennych `PG*` przekazywanych
przez Compose i zapisuje:

- `public.powiat`: TERYT, nazwę i granicę powiatu;
- `grid.hexagons`: identyfikator H3, rozdzielczość, TERYT, powierzchnię pełnej
  komórki w m² oraz geometrię EPSG:4326 z indeksem przestrzennym.

Ponowny import odświeża wskazane rozdzielczości i powiat bez duplikatów.
Operacja jest transakcyjna. `app/verify.py` sprawdza poprawność geometrii,
liczebność, pokrycie powiatu z tolerancją 1 m² i skrót identyfikatorów,
pozwalający porównać siatki między środowiskami.

Samodzielny eksport GeoJSON, wykonywany na runnerze z katalogu repozytorium:

```bash
docker compose -f docker-compose-remote.yml -p remote-db-env-test run --rm --no-deps python python3 /app/python/h3_generator.py --resolutions 6,7,8
```

Domyślne pliki `/tmp/grid` są wewnątrz kontenera. Aby je zachować, dodaj
montowanie katalogu wyjściowego i podaj `--output-dir` wskazujący ten katalog.

### Sprawdzenie w QGIS

Utwórz połączenie PostgreSQL z hostem `127.0.0.1`, portem 5544, 5545 albo
5546 i bazą `psip`. Dane logowania są w lokalnym `.env`. Dodaj warstwy
`public.powiat` i `grid.hexagons`; filtr `resolution = 6` (lub 7, 8)
pozwala obejrzeć pojedynczą siatkę. Docker Desktop i kontener DinD muszą działać.

Pobranie BDOT10K, schemat `bdot` i agregacje są punktami 4–5 zadania 2
i pozostają poza zakresem tej realizacji.

Dokumentacja: [H3 Python](https://uber.github.io/h3-py/api_quick.html),
[runner](https://github.com/myoung34/docker-github-actions-runner/wiki/Usage),
[TLS Dockera](https://docs.docker.com/engine/security/protect-access/).
