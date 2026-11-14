<!-- AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi) -->

# Brazilian data sources: ZARC, MapBiomas, IBGE PAM, Monitor de Secas

> **Background research, not a product decision.** It describes where the data is, in what format, under which terms, and what it cannot do. It does not recommend crops, rules or thresholds. Read on **2026-11-14** (Sergipe, Brazil). None of these sources is NASA data: all four are **third-party data** and must be credited as such (see "Credits" at the end).

Open question in the PRD this answers: *"ZARC data access: is it a file or an API, and at what granularity?"* (`_bmad-output/planning-artifacts/prds/prd-nether-field-shift-2026-2026-11-14/prd.md`, open question 5). Short answer: **a set of CSV files on the MAPA open-data portal (CC BY), one per harvest year, no server-side filter and no API for the rows.**

## Summary

| Source | Provider | Format | API / download | Granularity | Sergipe | Licence |
|---|---|---|---|---|---|---|
| **ZARC** (Tábua de Risco) | MAPA / SPA, with Embrapa | CSV (`;`, UTF-8 with BOM), 220 to 550 MB per file, whole country | CKAN catalog API for the file list; files are plain downloads, **no row filter** | Municipality x crop x soil class x cycle x management x harvest year; planting window in 36 ten-day periods (decêndios) with a risk class | All 75 municipalities for beans and maize; cassava as one "perennial" file | CC BY (catalog metadata) |
| **MapBiomas** Cobertura e Uso da Terra, Collection 11 | MapBiomas Brasil | GeoTIFF via Google Earth Engine; XLSX statistics | GEE assets and a GEE script (map file downloads are suspended); XLSX files by direct URL | 30 m, annual 1985 to 2025 | Yes (state and biome statistics checked) | "open, public and free with attribution", CC BY 4.0 (footer; licence URL and terms page not verified) |
| **IBGE PAM** (Produção Agrícola Municipal) | IBGE | JSON (SIDRA API) or CSV/XLSX (SIDRA web) | `https://apisidra.ibge.gov.br/values/...` and `https://servicodados.ibge.gov.br/api/v3/agregados/...` (both checked live) | Municipality (and UF, region, country) x crop x variable x year, 1974 to 2025 | 75 municipalities, 2025 already published | Not verified (IBGE terms pages blocked automated access) |
| **Monitor de Secas** | ANA, with FUNCEME and partners | Shapefile ZIP, PNG, PDF; tabular series (web table, spreadsheet export) | Plain file links on the "Dados SIG" page of the web app; no documented API | Monthly national polygons by severity class (S0 to S4), not municipal | Yes (point checks inside Sergipe) | Not stated on the pages read |

How each item was checked: **verified live** means I called the URL or API and read the answer on 2026-11-14; **from the page** means read on the official site (web app or documentation); **not verified** is stated explicitly.

---

## 1. ZARC: Zoneamento Agrícola de Risco Climático (MAPA / Embrapa)

**Third-party data. Not NASA.**

### What it is

The ZARC tells, per crop, municipality, soil class and cycle, which ten-day periods ("decêndios") of the year have a **planting window**, with the **risk level** (20%, 30% or 40% in the official panel legend; "Sem Zoneamento" outside the zoning). It is published as ministerial *portarias* (the legal text, PDFs per state on gov.br) and as an open table, the **Tábua de Risco**.

- **Official sources**
  - Open data catalog (MAPA): `https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico` (**verified live**; organization "Ministério da Agricultura e Pecuária", maintainer named in the metadata; the dataset was created 2019-06-10 and modified 2026-11-13).
  - Official panel "ZARC - Painel Oficial" (**from the page**): `https://mapa-indicadores.agricultura.gov.br/publico/extensions/Zarc/Zarc.html` (listed on `https://indicadores.agro.gov.br/`, last updated 2026-09-10 there). It has tabs "Tabua de Risco", "Dados", "Indicadores", "Comparação de Safras", filters by month and decêndio, and buttons "Exportar Excel" / "Exportar CSV" / "Exportar tudo (Excel)". Contact shown: `zoneamento@agro.gov.br`.
  - Portarias (legal reference): PDFs on `www.gov.br/agricultura`, organized by state (path pattern seen in search results: `.../riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/safra-vigente/<state>/<file>.PDF`; I did not verify the Sergipe folder).
- **Licence and terms:** the catalog metadata says **Creative Commons Attribution (`cc-by`, `http://www.opendefinition.org/licenses/cc-by`)** (verified live). The "licença de uso" link in the footer of the MAPA panels was not readable. No non-commercial clause seen.
- **Update cadence:** catalog says "Semanal" (weekly); the PDF data dictionary says "Diário" (daily). Treat the files as living documents.

### How the data is published

CKAN catalog API (verified live):

```bash
curl -s 'https://dados.agricultura.gov.br/api/3/action/package_show?id=tabua-de-risco-zoneamento-agricola-de-risco-climatico'
```

It lists one **CSV resource per harvest year** (2016/2017 to 2026/2027), one for **"Perene, Olerícola e Sem Safra"**, and the data dictionary PDF. Direct file URLs (verified live, HTTP 200, `text/csv`):

| Resource | URL (prefix `https://dados.agricultura.gov.br/dataset/6d3d141c-885e-41a4-ab7f-dc8ff323b96f/resource/`) | Size seen |
|---|---|---|
| Safra 2026/2027 | `139e5a60-1f43-4cc8-aeab-a35dbbf816c0/download/dados-abertos-tabua-de-risco-safra-2026-2027.csv` | 248 MB |
| Safra 2025/2026 | `f9d597f9-0fee-47eb-9344-8642274ca9da/download/dados-abertos-tabua-de-risco-safra-2025-2026.csv` | 223 MB |
| Perene, Olerícola e Sem Safra | `dae65d31-683f-4ac4-ab90-3abd0c1583ba/download/dados-abertos-tabua-de-risco-safra-perene-olericola-sem-safra.csv` | 550 MB |
| Data dictionary (PDF) | `bebb0ebb-bc75-460c-b900-a7a1ebd87bee/download/dicionario-de-dados-tabua-de-risco-2026.pdf` | 0.8 MB |

Older harvest years follow the same pattern (the resource IDs are in the `package_show` answer). The CKAN `datastore_search` action is **not** enabled (verified), so there is **no server-side filter**: to get Sergipe you download a whole-country file and filter it.

### Format

CSV, `;` separated, UTF-8 **with BOM**, CRLF line endings. Columns (from the file header and the dictionary): `Nome_cultura, SafraIni, SafraFin, Cod_Cultura, Cod_Ciclo, Cod_Solo, geocodigo, UF, municipio, Cod_Clima, Nome_Clima, Cod_Outros_Manejos, Nome_Outros_Manejos, Produtividade, Cod_NM, Cod_Munic, Cod_Meso, Cod_Micro, Portaria, dec1 ... dec36`.

- `geocodigo` is the **IBGE municipality code** (7 digits), so it joins directly with IBGE PAM and MapBiomas municipal tables. `Cod_Munic` is a different code (SICOR); do not mix them.
- `dec1` to `dec36` are the ten-day periods of the year ("separated by decêndios from 1 to 36" in the dictionary); the values seen in the file are `0`, `20`, `30`, `40`. The dictionary does not explain the values; the official panel legend gives 20%, 30% and 40% as risk levels and "Sem Zoneamento" for no zoning, so `0` is read here as "not in the zoning" (**interpretation, to confirm with MAPA**).
- `Cod_Solo`: `1` Arenoso, `2` Textura Média, `3` Argiloso (older and perennial files) or `11` to `16` = AD1 to AD6 (available-water classes, used by the 2026/2027 maize and bean files). **The soil classification changes between harvest years and crops**, so a join across years needs a lookup per file.
- `Cod_Ciclo`: `13` Perene, `19` Semiperene, `20` to `26` Groups I to VI (cycle length groups).
- `Cod_Outros_Manejos`: `1` Sequeiro (rainfed), `2` Irrigado, `3` Irrigado com controle de geada. `Cod_Clima`: `0` not applicable (the value seen for Sergipe) to `11`.
- `Portaria`: the ordinance number and date, e.g. `Port.237_de_10-07-2026`.

### Coverage of Sergipe for the v1 crops (checked in the 2026/2027 files, 2026-11-14)

| Crop name in the file | Municipalities (of 75) | Soil codes | Cycle codes | Management | Ordinance in the file |
|---|---|---|---|---|---|
| `Milho 1ª Safra` | 75 | 11 to 16 (AD1 to AD6) | 20, 21, 22 | Sequeiro | Port. 237 of 2026-07-10 |
| `Milho 1ª Safra consorciado com Braquiária` | 75 | 11 to 16 | 20, 21, 22 | Sequeiro | Port. 262 of 2026-07-14 |
| `Feijão` | 75 | 11 to 16 | 20, 21 | **Irrigado** only | Port. 45 of 2026-03-16 |
| `Feijão 2ª Safra` | 75 | 11 to 16 | 20, 21 | Sequeiro | Port. 372 of 2026-08-24 |
| `Feijão Caupi` | 75 | 1 to 3 | 20, 21, 22 | Sequeiro | Port. 136 of 2026-05-26 |
| `Mandioca (aipim, macaxeira)` (file "Perene, Olerícola e Sem Safra") | 75 | 1 to 3 | 13 (Perene) | Sequeiro | **Port. 17 of 2020-02-12** (no harvest year, `SafraIni` empty, `SafraFin` = `/PERENE`) |

Observations that matter for a user of the data (not recommendations):

- There is **no "Milho 2ª Safra" row for Sergipe** in the 2026/2027 file and no cassava row in the harvest-year files; cassava is only in the perennial file, with a 2020 ordinance and 3 soil classes (225 rows = 75 municipalities x 3 soils).
- "Bean" is three different crops in the table (`Feijão`, `Feijão 2ª Safra`, `Feijão Caupi`), with different soil and management coding.
- In 2025/2026 the Sergipe maize and bean files used soil codes 1 to 3 for maize (`Port. 194 of 2025-05-27`) and AD classes for the irrigated bean (`Port. 65 of 2025-04-11`): the coding is not stable.
- The file is **whole country**: 2026/2027 has 10,651 rows for Sergipe in a 248 MB file; the perennial file has 24,362 Sergipe rows in 550 MB.

### How to download and read it (example)

```bash
# 1. list the files (JSON); pick the harvest year you need
curl -s 'https://dados.agricultura.gov.br/api/3/action/package_show?id=tabua-de-risco-zoneamento-agricola-de-risco-climatico' \
  | python3 -c "import json,sys; [print(r['name'], r['url']) for r in json.load(sys.stdin)['result']['resources']]"

# 2. download (plain GET; send a normal User-Agent, about 250 MB)
curl -A 'Mozilla/5.0' -o zarc_2026_2027.csv '<resource url from step 1>'
```

```python
import csv
with open("zarc_2026_2027.csv", encoding="utf-8-sig", newline="") as f:
    rows = [r for r in csv.DictReader(f, delimiter=";") if r["UF"] == "SE"]   # Sergipe only
```

A streaming download that keeps only `UF == "SE"` rows avoids storing the 250 MB. The official panel can also export Excel/CSV after filtering by state and crop (not tested here).

### Limitations and risks

- **Not a forecast and not agronomic advice by itself**: it is a regulatory zoning (it conditions rural credit and insurance, Proagro/PSR) with the legal text in the *portarias*. For any legal or contractual use the **portaria PDF prevails over the CSV**.
- **Schema drift**: soil classes (1 to 3 vs AD1 to AD6), crop names and management labels change between harvest years and crops; the "Safra" is the planting season, not the calendar year.
- **Cassava** relies on a 2020 ordinance (perennial file), while maize and beans are re-issued each harvest year.
- **Size and latency**: no filter, 220 to 550 MB per download; the catalog is updated weekly or daily (documents disagree).
- Granularity is the **municipality** (not the field); the risk classes are fixed ranges (20/30/40%), and the decêndio is a 10-day bin.
- The catalog page and CSV downloads worked with a browser-like User-Agent; automated access policies could change.

---

## 2. MapBiomas: Cobertura e Uso da Terra (Collection 11)

**Third-party data. Not NASA.** (Landsat-based; the underlying imagery is NASA/USGS Landsat, but the product, classification and licence are MapBiomas'.)

- **Official source:** MapBiomas Brasil, `https://brasil.mapbiomas.org/`; product page `https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-30m/` (**from the page**).
- **Most recent collection:** **Collection 11**, annual maps **1985 to 2025**, 30 m, "more than 30 classes"; release announced on **2026-08-12** (`https://brasil.mapbiomas.org/mapbiomas-lanca-colecao-11-de-cobertura-e-uso-da-terra/`). Collection 10 was published in August 2025 (1985 to 2024).
- **Licence and terms:** the footer of every page says "Os dados do MapBiomas são de uso público, aberto e gratuito mediante referência. **CC BY 4.0**". The link target of "CC BY 4.0" was not exposed, and the "Termos de uso" page (`https://brasil.mapbiomas.org/termos-de-uso/`) returned **404** on 2026-11-14, so the licence URL and any extra terms are **not verified**. No non-commercial clause was found. **Citation (FAQ item 18):** "Projeto MapBiomas – Coleção [versão] da Série Anual de Mapas de Cobertura e Uso da Terra do Brasil, acessado em [data] através do link: [LINK]"; reference article: Souza et al. (2020), *Remote Sensing* 12(17), doi:10.3390/rs12172735.
- **Format and download**
  - **Map downloads are suspended** on the Downloads page: "A função de baixar mapas está temporariamente suspensa. Acesse os dados diretamente pelos assets no Google Earth Engine (GEE)" (`https://brasil.mapbiomas.org/downloads/`, **from the page**).
  - **Clipped GeoTIFFs by state, biome or municipality** through a GEE script (needs a Google Earth Engine account; non-commercial registration is linked on the page): `https://brasil.mapbiomas.org/downloads/baixe-mapas-recortados-geotiff-via-google-earth-engine/` (script `users/mapbiomas/user-toolkit:mapbiomas-user-toolkit-lulc.js`).
  - **GEE asset** (public, one band per year): the asset ID in the documentation is **not verified** (a summary gave `projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_coverage_v3`; check it in the toolkit before relying on it). Direct `storage.googleapis.com/mapbiomas-public/...` GeoTIFF URLs I tried (two patterns) answered **HTTP 403**, so they are **not** documented here.
  - **Statistics tables (XLSX, hectares by class and year, no login):** `https://brasil.mapbiomas.org/downloads/estatisticas/`. Verified live: `https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/08/MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE.xlsx` (HTTP 200, 17.9 MB; sheets `COVERAGE_11`, `TRANSITION_11`, `LEGEND_CODE`...; `COVERAGE_11` has columns `biome, region, state, class, class_level_0..4, y1985 ... y2025`; **Sergipe rows present**, e.g. biome Caatinga). The page also links a municipality-level workbook on Google Drive (not opened) and agriculture-related workbooks such as `.../2026/09/MAPBIOMAS-BRAZIL-AGRICULTURE-USE-SECOND-CROP-MUNICIPALITY.xlsx` (not opened; see the "Uso agrícola" product page `https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/agricultura/uso-agricola/`).
  - **Legend CSV (verified live):** `https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/08/legend_code_mapbiomas_brazil_collection_11.csv` (`class_id, class_name_pt_br, class_name_en, hex_code`).
- **Granularity:** 30 m pixels, one map per year (annual only), national mosaic, statistics by state, biome and municipality.
- **Coverage of Sergipe:** yes (the product is national; Sergipe rows are in the state/biome statistics).
- **Classes relevant to farming (Collection 11 legend, verified live):** 15 Pastagem, 39 Soja, 20 Cana, 40 Arroz, 62 Algodão (beta), **41 Outras Lavouras Temporárias**, 46 Café, 47 Citrus, 35 Dendê, 48 Outras Lavouras Perenes, 9 Silvicultura, **21 Mosaico de usos**. **There is no separate class for maize, beans or cassava** (they would fall in "Outras Lavouras Temporárias" or in "Mosaico de usos", which mixes uses that the satellite cannot separate).
- **Limitations and risks**
  - Land cover and land use, not crop type, for the v1 crops; annual maps cannot see the season inside a year.
  - Accuracy is global and per class (about 85,000 validation points, 1985 to 2024 per the accuracy page); no Sergipe-specific figure found. Beta classes are preliminary.
  - **Area caveat from the FAQ**: do not multiply pixel counts by 900 m² at national scale; use the GEE `pixelArea` method. Differences from IBGE areas are below 0.2% (up to 0.5% in small municipalities).
  - A new collection is released about once a year and re-processes the full series, so numbers change between collections; always record the collection number.
  - Map file downloads currently depend on a Google Earth Engine account.

---

## 3. IBGE PAM: Produção Agrícola Municipal (SIDRA)

**Third-party data. Not NASA.**

- **Official source:** IBGE, SIDRA tables (`https://sidra.ibge.gov.br/tabela/5457`, `/tabela/1612`, `/tabela/839`; titles read on the pages) and the **SIDRA API** (`https://apisidra.ibge.gov.br/values/...`) and the **aggregates API** (`https://servicodados.ibge.gov.br/api/v3/agregados/...`). The documentation pages (`apisidra.ibge.gov.br/home/ajuda`, IBGE site pages) answered HTTP 403 to automated requests; the API endpoints themselves work and were **verified live**.
- **Licence and terms:** **not verified.** The IBGE site blocked automated access, and the terms URL I tried returned 404. Check the footer of `https://sidra.ibge.gov.br/` or `https://www.ibge.gov.br/` before publishing; at minimum credit **"Fonte: IBGE, Pesquisa Agrícola Municipal (PAM)"** and keep the table number and access date.
- **Tables (metadata verified live through `https://servicodados.ibge.gov.br/api/v3/agregados/<table>/metadados` and `/periodos`):**

| Table | Content | Years | Territorial levels |
|---|---|---|---|
| **5457** | Area planted or intended for harvest, area harvested, quantity produced, average yield and production value, **temporary and permanent crops** | **1974 to 2025** (annual) | N1 Brasil, N2 region, N3 UF, **N6 municipality**, N8, N9 |
| 1612 | Same, **temporary crops** only | 1974 to 2025 | (same family) |
| 839 | **Maize, 1st and 2nd harvest** (area planted, area harvested, quantity, yield) | 2003 to 2025 | not checked |

- **Variables of table 5457 (verified):** `8331` Área plantada ou destinada à colheita (ha), `216` Área colhida (ha), `214` Quantidade produzida (t), `112` Rendimento médio (kg/ha), `215` Valor da produção (mil R$ since 1994; older currencies before), plus "percentual do total geral" variants (`1008331`, `1000216`, `1000215`).
- **Product classification of table 5457 is `c782`** (86 categories). The codes for the v1 crops (verified): **`40112` Feijão (em grão)**, **`40119` Mandioca**, **`40122` Milho (em grão)**; `83394` Milho verde; `0` Total. Note that "Feijão (em grão)" is the crop total over its harvests, and "Milho (em grão)" is the 1st + 2nd harvest total; table 839 splits maize by harvest.
- **Latest year available on 2026-11-14: 2025** (the `/periodos` endpoint ends at 2025). The release date of PAM 2025 was not verified.

### API syntax and a verified call

`https://apisidra.ibge.gov.br/values/t/<table>/n6/<territories>/v/<variables>/p/<periods>/c<classification>/<categories>[/h/n][/f/a]`

All 75 municipalities of Sergipe (`n6/in n3 28`, UF code 28), last year, three crops, five variables (**verified live: HTTP 200, `application/json`, 1,126 elements, 360 KB**):

```bash
curl -s 'https://apisidra.ibge.gov.br/values/t/5457/n6/in%20n3%2028/v/8331,216,214,112,215/p/last%201/c782/40112,40119,40122'
```

- Output: a JSON **array**. **Element 0 is the header** (it maps the keys to their meaning); elements 1..n are values. Keys: `NC/NN` (level code/name), `MC/MN` (unit code/name), **`V` (value, always a string)**, `D1C/D1N` (municipality code/name, e.g. `2800100` "Amparo do São Francisco - SE"), `D2C/D2N` (variable), `D3C/D3N` (year), `D4C/D4N` (product). The dimension order follows the URL. `/h/n` removes the header element (verified).
- **Request limit: 100,000 values per call** (verified; the error text is "Quantidade de valores solicitados: 289328 excedeu o limite: 100000"). A call for all municipalities, all years would exceed it: split by period or by UF.
- **Missing values:** `V` can be a symbol. In the call above, 210 of 1,125 values were `"-"` (crop not produced there, "zero absoluto"). The SIDRA legend on the table pages: `-` absolute zero, `0` zero from rounding, `X` withheld to protect the informant, `..` not applicable, `...` not available (e.g. crop not surveyed in that municipality). Convert them explicitly, do not parse blindly as numbers.
- **Municipality codes** are the 7-digit IBGE codes (`D1C`), the same as ZARC's `geocodigo` and as MapBiomas municipal tables.

### Limitations and risks

- **Annual and municipal**: no within-year season, no field level; values are survey estimates by municipality (declared by local IBGE agencies).
- **Series changes**: PAM tables and classifications have been revised (crop lists, 1st/2nd harvest splits); check the table notes when comparing years. Values for the latest year are preliminary and may be revised.
- Suppressed (`X`) and missing (`...`) cells are common for small municipalities.
- The documentation and terms pages are not reachable by script, and the licence was not verified.

---

## 4. Monitor de Secas (ANA)

**Third-party data. Not NASA.**

- **Official source:** Monitor de Secas do Brasil, coordinated by the **Agência Nacional de Águas e Saneamento Básico (ANA)** with **FUNCEME** and other state and federal partners: `https://monitordesecas.ana.gov.br/` (a JavaScript web app; the pages below were read in a browser). The ANA gov.br page for the programme returned 404 and `dadosabertos.ana.gov.br` showed no dataset when read, so the web app is the reference.
- **What it is:** a monthly map of drought **severity** produced by consensus of technicians from several institutions ("validators"), not a raw measurement. The "Tabela de Classificação de Severidade da Seca" page defines the classes; the data uses `S0` to `S4` plus "sem seca" (`si`).
- **History and coverage (from the "O Monitor de Secas" page):** started in **2014 as a pilot in the Northeast semi-arid region**; ANA is the central institution since 2017; other states were added gradually until national coverage ("took 5 years"; the page text I could read was truncated, the exact join years per state are **not verified**). Sergipe is a Northeast state, and **Sergipe's state agency (EMDAGRO) published monthly narratives of the Monitor in 2019** (`https://www.emdagro.se.gov.br/wp-content/uploads/2019/08/NARRATIVA_MONITOR_DE_SECAS_JULHO-2019.pdf`), so it takes part at least since then. The September 2026 shapefile (below) covers Sergipe.
- **Products and download (the "Dados SIG" page, `https://monitordesecas.ana.gov.br/dados-sig`, read in a browser):** a table by month with **PNG map, PDF synthesis and a Shapefiles ZIP**, with a year selector (2026 shows January to **September 2026** as the latest on 2026-11-14). Links are plain HTTPS files:
  - ZIP: `https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/uploads/mapas/setembro2026.zip` (the pattern is `<month name in Portuguese><year>.zip`; verified live: HTTP 200, 15.8 MB, last modified **2026-10-16**, i.e. the September map appeared about two weeks after the month ended)
  - PNG: `.../uploads/mapas/147_setembro2026.png`; PDF: `.../uploads/mapas/Monitor_Secas_Sintese_setembro2026.pdf`
- **Shapefile content (September 2026 ZIP, opened):** `setembro26.shp` (cumulative drought areas) and `setembro26_isolado.shp` (non-overlapping areas): **national multipolygons, one feature per class** with fields `uf_codigo` (`si`, `s0`, `s1`, `s2`; no `s3`/`s4` that month) and `Valor` (0 to 3); `202609_MS_IMPACTOS.shp` (impact lines) and `202609_MS_IMPACTOS_TIPO.shp`; `Estados_monitor/UF_Brasil.shp` (state boundaries, 19.8 MB); QGIS project and style files. CRS: **WGS84 geographic (EPSG:4326)**. A point-in-polygon test against the non-overlapping file placed points in Sergipe (Aracaju, Itabaiana, Nossa Senhora da Glória: S0; Poço Verde: S1), which confirms Sergipe is inside the national map.
- **Tabular data (`https://monitordesecas.ana.gov.br/dados-tabulares`):** history of the share of area in each cumulative class (S0-S4, S1-S4, S2-S4, S3-S4) selectable by territory, with an **"Exportar Planilha"** button (the territory options and the file format were not explored).
- **Granularity:** **monthly**; polygons delineated by experts, **not** municipal or gridded values; one mask per class. No pixel values and no municipality identifier in the shapefile.
- **API:** none documented. The web app serves its files from a public S3 bucket through the links above; the file names change every month and are in Portuguese, so a script must build them (or scrape the Dados SIG table).
- **Licence and terms:** **not stated on the pages read** (no licence link found). ANA publishes open data under its own policy, but I could not verify it for this product. Ask through the contact page (`https://monitordesecas.ana.gov.br/contato`) and credit **"Monitor de Secas, ANA / FUNCEME e instituições parceiras"** with the month of the map.
- **Limitations and risks**
  - Monthly and **lagged** (about two weeks after month end); the October 2026 map was not out on 2026-11-14.
  - Qualitative, consensus-based classification: it is an indicator of conditions over large areas, not a station measurement, and boundaries are smooth at state scale.
  - Polygon extents can be coarse for a single municipality; always record the map month.
  - File names and the page structure are those of a web app that can change without notice; there is no versioned API.
  - The "Acesso Restrito" area (validators) is a separate FUNCEME system and is not open.

---

## Credits to keep in the README / project page when any of these is used

| Source | Credit (suggested wording; confirm against the terms above) |
|---|---|
| ZARC | "Zoneamento Agrícola de Risco Climático (ZARC), Tábua de Risco. Ministério da Agricultura e Pecuária (MAPA), dados abertos, licença CC BY." with the harvest year and the portaria. Link: `https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico` |
| MapBiomas | "Projeto MapBiomas – Coleção 11 da Série Anual de Mapas de Cobertura e Uso da Terra do Brasil, acessado em [data] através do link: https://brasil.mapbiomas.org/", CC BY 4.0. |
| IBGE PAM | "Fonte: IBGE, Pesquisa Agrícola Municipal, tabela 5457 (SIDRA), acessado em [data]". Licence to be confirmed. |
| Monitor de Secas | "Monitor de Secas, ANA / FUNCEME e instituições parceiras, mapa de [mês/ano]". Terms to be confirmed. |

None of these is NASA data, so none belongs under "NASA data used" in the README; they go in the third-party data section.
