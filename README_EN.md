# Anvisa package-insert extractor (Brazil) — English summary

Open-source tool that converts Brazilian professional package inserts (PDF, standardized by Anvisa RDC 47/2009, from the
Anvisa Electronic Package Insert Database — *Bulário Eletrônico*) into structured data: full sections, bold subheadings,
composition (active ingredients and excipients), presentations, pharmacokinetics, Ministry of Health registration number and a
SQLite database with full-text search.

It also reproduces, with one command, the study *“Information on major drug-drug interactions in Brazilian statin package
inserts: a documentary agreement study against an international reference database”*:
92 professional inserts of five statins (atorvastatin, pitavastatin, pravastatin, rosuvastatin, simvastatin) compared with
Drugs.com *major* interactions (retrieved 13 Nov 2026).

```bash
pip install -r requirements.txt            # plus Poppler (pdftotext), required for identical results
python reproduzir_estudo.py --tabela dados/preclassificacao_v02.csv   # level 1: statistics from the frozen pair table, no PDFs
python reproduzir_estudo.py --pdfs FOLDER_WITH_THE_INSERTS            # level 2: full pipeline from the PDFs
python -m pytest tests                     # 76 tests (engine configuration, rules, sentence-level engine v2, synthetic insert, frozen data)
```
Each PDF is identified by the registration number printed inside it (file names are ignored), and its SHA-1 is checked against
`dados/corpus_bulas.csv`. With the same PDFs, results are identical to the published ones (tested from the .zip in a fresh folder with 134 randomly named PDFs: 92 inserts, 4,211 identical pairs).
The automatic pre-classification (engine v2, sentence-level, codebook-based; 99.7% agreement with a full AI-assisted reference reading of the development set, 95% on a blind external test) is a suggestion; in the study, all 4,211 pairs were reviewed by the first rater (1 changed, annotation only;
`dados/classificacao_revisada.csv`) and a sample was rated blind by a second rater. Code: MIT. Data: see `LICENSE-DATA` (study data CC BY 4.0; Anvisa open data). Since v0.2.1 the raw Drugs.com list is not redistributed (site terms of use); `dados/interacoes_graves_referencia.csv` keeps only the study pairs in Brazilian names (DCB).
Authors: Elivan da Silva (ORCID 0009-0005-9191-7846); Lohana Souza Galvão (ORCID 0009-0006-9034-9004); Ana Beatriz Lucena Brito
(ORCID 0009-0000-8860-5001); Iara Leão Luna de Souza (ORCID 0000-0002-5309-2979), supervisor. Release notes: `NOTAS_DE_VERSAO.md` (Portuguese).

**Configurable engine (v0.2.0).** The drugs searched for, the drug classes/mechanisms and the management expressions are read from
tables in `configuracao/` (CSV, or one Excel workbook via `ferramentas/configuracao_planilha.py`), not from the code. Copy the folder,
edit it for another drug class and run with `--config`. Instructions (in Portuguese): `configuracao/LEIA-ME.md`; codebook:
`docs/LIVRO_DE_CODIGOS.md`.

**Changes in v0.2.0.** Corrected corpus (a registration is active when any of its presentations is active): 102 active
single-ingredient registrations, 92 inserts (7 added as batch 2, B086–B092). Engine rules moved to configuration files (identical
results). Two reproduction levels (`--tabela`, `--pdfs`).
