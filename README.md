# bulario-anvisa-extrator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24205712.svg)](https://doi.org/10.5281/zenodo.24205712)
![código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-blue)
![dados: CC BY 4.0](https://img.shields.io/badge/dados-CC%20BY%204.0-green)
![Python 3.13](https://img.shields.io/badge/python-3.13-informational)

**Um robô de código aberto que lê bulas.** Ele recebe as bulas para o profissional de saúde do Bulário Eletrônico da Anvisa
(em PDF) e, para cada interação medicamentosa de uma lista de referência, responde: **a bula cita?** (pelo nome ou pela
classe), **onde cita?** e **qual conduta indica?** (contraindicar/evitar, limitar a dose, monitorar ou nenhuma). Cada decisão
vem com a frase da bula que a justifica, para que uma pessoa possa conferir.

O motor não é um modelo de inteligência artificial: são regras explícitas e determinísticas, escritas num livro de códigos
(`docs/LIVRO_DE_CODIGOS.md`), e o vocabulário (fármacos, classes, expressões de conduta) fica em planilhas (`configuracao/`),
não no código. O código foi escrito com apoio de IA generativa (Claude, via Claude Code), e a leitura de referência usada para
desenvolver as regras também foi feita com essa ferramenta; o artigo declara cada uso.

| Estudo das estatinas (92 bulas, 4.211 pares) | |
|---|---|
| Concordância entre avaliadores, segunda avaliadora às cegas (12 bulas, 477 pares; kappa) | **0,86** citação · **0,54** manejo |
| Concordância com a leitura de referência, no conjunto em que as regras foram desenvolvidas¹ | 100% citação · 99,7% manejo |
| Completude mediana das bulas | **82,5%** das interações graves citadas |

¹ Não é acurácia independente: a leitura de referência foi feita com apoio de IA, nas mesmas 85 bulas usadas para ajustar as
regras. A validação do método é preliminar (ver as limitações do artigo e a seção "Limitações conhecidas" abaixo).

```bash
pip install -r requirements.txt
python reproduzir_estudo.py --tabela dados/preclassificacao_v02.csv   # refaz as estatísticas do artigo (≈1 min)
python extrair.py --help                                               # extrai seções e campos de qualquer bula em PDF
```

**Em andamento:** a mesma rotina aplicada a **anticoagulantes orais** e a **benzodiazepínicos com opioides** (XVIII EICEA,
2026), e uma base aberta de bulas brasileiras. Sugestões e correções são bem-vindas nas *issues*.

**Como citar:** Silva, E. da; Galvão, L. S.; Brito, A. B. L.; Souza, I. L. L. de. *Extrator de bulas do Bulário Eletrônico
da Anvisa e dados do estudo de interações graves em bulas de estatinas*. Versão 0.2.0. Zenodo, 2026.
DOI: [10.5281/zenodo.24205712](https://doi.org/10.5281/zenodo.24205712). O botão “Cite this repository” usa o `CITATION.cff`.

---

## Extrator de bulas do Bulário Eletrônico da Anvisa (v0.2.0)

Código e dados do estudo **“Informação sobre interações medicamentosas graves nas bulas brasileiras de estatinas:
estudo documental de concordância com base de referência internacional”**.

Há três coisas aqui:
- uma **ferramenta geral** (`extrair.py` + `bulario/`) que transforma qualquer bula profissional em PDF (padrão da RDC nº 47/2009)
  em dados estruturados: seções completas, subtítulos, composição (ativos e excipientes), apresentações, farmacocinética,
  registro MS e um banco SQLite com busca de texto;
- um **motor de classificação configurável** (`estudo/classificar.py` + `configuracao/`): os fármacos, as classes e as expressões
  de manejo ficam em tabelas (CSV ou planilha), não no código; com outra configuração, o motor serve para outras classes de medicamentos;
- o **estudo das estatinas** (`reproduzir_estudo.py` + `estudo/` + `dados/`), que reproduz os resultados do artigo com um comando.

## Novidades da versão 0.2.0 (15/11/2026)
- Corpus corrigido: a situação de um registro passou a ser "Ativo" quando **qualquer** apresentação está ativa (antes, valia a
  primeira linha do arquivo da Anvisa, que tem uma linha por apresentação). São 102 registros ativos em monofármaco (eram 94);
  7 dos registros incluídos têm bula (lote 2, B086–B092) e 1 não tem. O corpus passou de 85 para **92 bulas**.
- Configuração do motor v2 em `configuracao/` (antes escrita em `estudo/regras.py`), com validação e conversão para planilha.
  As regras carregadas são idênticas às da versão anterior (teste `tests/test_configuracao.py`).
- O marcador de lista "●" passou a separar frases (uma bula do lote 2 o usa); nenhuma classificação das 85 bulas do lote 1 mudou.
- Reprodução em dois níveis: sem PDFs, a partir da tabela de pares (`--tabela`), e completa, a partir dos PDFs (`--pdfs`).
- A saída traz o código da bula usado no artigo (`id_bula`, B001–B092).

## Reproduzir o estudo
**Nível 1 — sem baixar bulas (cerca de 1 minuto).** Recalcula todas as estatísticas a partir da tabela de pares congelada:
`pip install -r requirements.txt` e depois `python reproduzir_estudo.py --tabela dados/preclassificacao_v02.csv`.
Deve terminar em “comparação …: IDÊNTICO ✓”.

**Nível 2 — completo, a partir dos PDFs (passo a passo):**
1. **Instale** o Python (testado no 3.13) e o `pdftotext` do **Xpdf 4.00** (Glyph & Cog) — **obrigatório para resultados idênticos**
   (sem ele o programa usa o PyMuPDF, que quebra o texto de outro jeito). No Windows, ele já vem com o Git for Windows
   (`mingw64/bin`); em qualquer sistema: https://www.xpdfreader.com/download.html ("Xpdf command line tools", pasta no PATH).
   O `pdftotext` do Poppler não foi testado. Depois: `pip install -r requirements.txt` (versões exatas em `requirements-lock.txt`;
   no Windows, use `py -3` no lugar de `python`).
2. **Baixe as bulas para o profissional de saúde** das estatinas no Bulário Eletrônico (https://consultas.anvisa.gov.br/#/bulario/).
   A lista está em `dados/corpus_bulas.csv` (coluna `registro_ms`; `no_corpus = Sim`). O link da coluna `link_bulario` de
   `dados/registros_estatinas.csv` abre a busca do Bulário com o número de registro já preenchido: clique em “Consultar” e baixe
   a “Bula do Profissional”. Pode salvar com **qualquer nome**, numa pasta só ou em subpastas:
   o programa identifica cada bula pelo número de registro escrito no próprio PDF e ignora duplicatas e PDFs de outros medicamentos.
3. **Rode**: `python reproduzir_estudo.py --pdfs PASTA_DAS_BULAS`
4. **Confira** a saída:
   - “92 no corpus (esperado: 92 = 102 registros ativos − 10 sem bula no Bulário)” e “mesma versão do estudo: 92 de 92”
     → você tem exatamente os mesmos PDFs;
   - “comparação …: IDÊNTICO ✓” → os números batem com os do estudo.
   Resultados em `resultados/`: `identificacao.csv`, `json/`, `bulas_estatinas.db`, `preclassificacao.csv`,
   `completude_por_bula.csv` e `estatisticas.json`.
5. Com a classificação revisada por humanos (`dados/classificacao_revisada.csv`):
   `python reproduzir_estudo.py --pdfs PASTA_DAS_BULAS --classificacao dados/classificacao_revisada.csv`
   (ou, sem os PDFs, `--tabela dados/preclassificacao_v02.csv --classificacao dados/classificacao_revisada.csv`); deve terminar em
   “comparação com estatisticas_revisadas.json: IDÊNTICO ✓”.

**Por que o resultado pode mudar:** as empresas atualizam as bulas. Se o programa disser que alguma bula está em
“versão diferente da usada no estudo”, os números podem diferir — isso é esperado e o SHA-1 em `dados/corpus_bulas.csv`
mostra qual versão foi usada. O Drugs.com e os dados da Anvisa também mudam; por isso as listas estão congeladas em `dados/`.
O estudo foi feito com Python 3.13, pdftotext 4.00 (Xpdf), PyMuPDF 1.28, pandas 3.0 e SciPy 1.18 (`requirements-lock.txt`).
Teste de reprodução a partir do .zip deste depósito, numa pasta nova e num ambiente Python novo (PyMuPDF 2.1, pandas 3.1):
134 PDFs com nomes aleatórios (109 de estatinas, 20 de outros medicamentos e 5 cópias) → 92 bulas e 4.211 pares idênticos aos
do estudo, com os dois motores. As versões mínimas de `requirements.txt` (PyMuPDF 1.24, pandas 2.2, SciPy 1.14) também
passaram nos testes e no nível 1.

## Limitações conhecidas
- A pré-classificação é uma **sugestão por regras**. No estudo, o primeiro avaliador revisou os 4.211 pares
  (`dados/classificacao_revisada.csv`, coluna `conferencia`: 1.287 lidos um a um, 2.249 confirmados por texto idêntico ao de
  uma bula já lida, 675 com ausência verificada no texto) e alterou um (anotação da classe citada, sem mudança de citação, local ou
  manejo). Uma amostra de 12 bulas (477 pares) foi classificada às cegas por uma segunda avaliadora (κ = 0,86 na citação e
  0,54 no manejo); o consenso entre os dois corrigiu 12 pares do corpus (coluna `alterado_no_consenso`), o que muda só as
  contagens de manejo de `estatisticas_revisadas.json` em relação a `estatisticas_preclassificacao_v02.json`.
- Motor v2 (padrão): leitura **frase a frase** segundo um livro de códigos (exceções, orientação na frase seguinte, restrição só de
  combinação ou de subpopulação, contraindicação condicionada à dose, tabela de exposição com regra de ajuste de dose, grafias
  erradas da bula). Concordância com a leitura integral de referência das 85 bulas do lote 1: 100% citação, 100% local (a leitura partiu do mesmo texto segmentado; ver a auditoria abaixo), 99,7% manejo (conjunto de
  desenvolvimento; a leitura de referência foi assistida por IA, ver o artigo); em 100 frases de bulas de OUTROS medicamentos
  lidas às cegas: 95% no manejo (gabarito feito com apoio da mesma ferramenta de IA; serve como teste de regressão, não como
  validação independente). O motor v1 (`--motor v1`) aplica as regras da versão 0.1.0 (por janela de caracteres).
- A extração depende do padrão da RDC nº 47/2009; bulas fora do padrão ou escaneadas podem ter seções faltando
  (o campo `problemas` de cada JSON avisa).
- A busca de citações usa nomes em DCB e radicais; grafias muito diferentes podem escapar da pré-marcação.
- O motor v2 depende da separação das frases: texto embaralhado pela extração do PDF (colunas, cabeçalhos no meio da frase)
  ainda causa erros pontuais (12 de 3.858 pares no lote 1, sempre para o lado mais restritivo).
- Palavras hifenizadas na quebra de linha não são reunidas. No estudo, o único fármaco partido ("ciclos-porina", numa bula de
  rosuvastatina) aparecia inteiro em outros trechos da mesma bula, sem efeito no resultado; em outras classes isso pode causar
  omissão.
- A validação é preliminar: as regras foram ajustadas e avaliadas nas mesmas bulas, e só 12 bulas tiveram avaliação humana
  independente e às cegas.
- Testado em Windows 11 (Python 3.13, pdftotext 4.00). Não há código específico de Windows, mas Linux/Mac não foram testados.

## Testes automatizados
`python -m pytest tests` executa 80 testes; sem os PDFs e sem a lista bruta do Drugs.com (não incluída no GitHub), 77 passam e 3 são
pulados. Eles cobrem: configuração do motor (as tabelas reproduzem as regras do estudo, a planilha equivale
aos CSV, configurações inválidas são recusadas e uma configuração alterada muda o motor), regras (radicais DCB, nome só no início da palavra, classes, manejo, negação, leitura do registro MS, cada regra do motor v2 com trechos reais),
uma bula **sintética** gerada no próprio teste que percorre todo o fluxo (extração → banco → identificação → pré-classificação),
a integridade dos dados congelados, o sorteio da amostra e a reprodução a partir da tabela de pares (pré-classificada e revisada). Com `BULARIO_PDFS=PASTA` também roda a reprodução completa
(com os dois motores; deve terminar em “IDÊNTICO”). Os testes foram verificados por mutação feita à mão, sem ferramenta
automatizada: removendo de propósito uma regra do código ou uma expressão da configuração (contraindicação, exceção, retomada
na frase seguinte), eles falham. São testes de regressão e de unidade: garantem que o comportamento não mudou e que cada regra
faz o que o livro de códigos diz, mas não medem acurácia contra um gabarito humano independente.

As análises do artigo que não saem de `reproduzir_estudo.py` (Tabela 4, divergências entre bulas e VigiMed) estão em
`estudo/analises_complementares/`.

## Configurar o motor (outras classes de medicamentos)
Edite as tabelas de `configuracao/` (ou de uma cópia) e rode com `--config`. As instruções completas, com exemplos de expressões,
estão em `configuracao/LEIA-ME.md`. Para trabalhar numa planilha única:
```bash
python ferramentas/configuracao_planilha.py --para-xlsx configuracao minha_configuracao.xlsx
python ferramentas/configuracao_planilha.py --validar minha_configuracao.xlsx
python reproduzir_estudo.py --pdfs PASTA_DAS_BULAS --config minha_configuracao.xlsx
```

## Usar a ferramenta com outras bulas
```bash
python extrair.py PASTA_COM_PDFS --saida saida --db bulas.db
python bulario/buscar.py --db bulas.db --ativo sinvastatina --texto claritromicina
python bulario/buscar.py --db bulas.db --excipiente lactose
```
Limitações: PDFs escaneados (imagem) precisam de OCR antes; as camadas estruturadas (composição, farmacocinética) são
heurísticas — confira sempre no texto da seção, que é guardado na íntegra.

## Conteúdo
- `bulario/` – núcleo de extração: `texto.py` (PDF → texto limpo e seções), `campos.py` (campos estruturados),
  `completo.py` (bula completa + subtítulos pelo negrito), `banco.py` (SQLite + FTS5), `buscar.py` (consultas).
- `configuracao/` – regras do motor v2 em CSV: `alvos`, `referencia_ignorar`, `farmacos`, `classes`, `expressoes` (+ `LEIA-ME.md`).
- `docs/LIVRO_DE_CODIGOS.md` – critérios de citação, local e manejo que o motor implementa.
- `estudo/` – `identificar.py` (bula pelo registro MS e SHA-1), `regras.py` (lê e valida a configuração), `regras_v01.py`
  (regras congeladas do motor v1),
  `amostra.py` (sorteio da amostra de validação, semente 2026),
  `classificar.py` (motor v2, por frase), `preclassificar.py` (motor v1, versão 0.1.0), `estatisticas.py` (completude, Kruskal-Wallis, Mann-Whitney).
- `dados/` – `interacoes_graves_referencia.csv`
  (pares estatina × fármaco, DCB, registro ativo no Brasil; a lista do Drugs.com foi obtida nas páginas públicas de interação
  de cada estatina em 13/11/2026 e conferida manualmente no site em 14/11/2026, cada estatina por uma de duas pesquisadoras:
  194 de 194 confirmadas como graves, nenhuma grave ausente — veja as licenças em `LICENSE-DATA`), `registros_estatinas.csv` (dados abertos da Anvisa, atualização
  13/10/2026, + CMED), `corpus_bulas.csv` (registro, categoria, SHA-1, lote), `exclusoes_sem_bula.csv`, `amostra_validacao.csv`
  (estratificada, semente 2026), `Estatinas_Brasil.xlsx` (registros e preços CMED), `preclassificacao_v02.csv` (tabela de pares do motor v2),
  `estatisticas_preclassificacao_v02.json` (v1: `estatisticas_preclassificacao.json`), `classificacao_revisada.csv` (os mesmos
  pares após a revisão humana e o consenso), `estatisticas_revisadas.json` e `avaliacao_dupla/` (amostra da classificação às
  cegas: respostas dos dois avaliadores antes do consenso, decisões e correções do consenso).
- `ferramentas/` (opcional) – `concordancia_avaliadores.py` (kappa, IC95% e PABAK da dupla avaliação); `configuracao_planilha.py` (CSV ↔ planilha, validação); `gerar_registros.py` e `gerar_referencia.py` recriam `registros_estatinas.csv` e
  `interacoes_graves_referencia.csv` a partir dos dados abertos da Anvisa (com os mesmos arquivos de origem, o resultado é idêntico).
- `tests/` – testes automatizados (pytest). `DADOS.md` – dicionário de dados. `README_EN.md` – resumo em inglês.
- `instrumentos/` – formulários (Google Apps Script) usados na classificação cega e na validação manual, e o anexo de
  pertinência às classes entregue à avaliadora (`Anexo_pertinencia_classes.pdf`).

As bulas em PDF não são redistribuídas (documentos das empresas, públicos no Bulário).
No GitHub, a lista bruta do Drugs.com (`drugscom_major_2026-11-13.json`) também fica de fora, porque não é coberta pela CC BY;
ela está no pacote do Zenodo (DOI 10.5281/zenodo.24205712), junto com o restante do estudo.

## Versões
Veja `NOTAS_DE_VERSAO.md` (o que mudou em cada versão e o que está planejado).

## Como citar
Veja `CITATION.cff` (o DOI aparece na página do Zenodo). Licenças: código **MIT** (`LICENSE`); dados produzidos no estudo
**CC BY 4.0**; dados da Anvisa e do Drugs.com seguem as condições das fontes (detalhes em `LICENSE-DATA`).
Autores: Elivan da Silva (ORCID 0009-0005-9191-7846); Lohana Souza Galvão (ORCID 0009-0006-9034-9004); Ana Beatriz Lucena Brito (ORCID 0009-0000-8860-5001); Profa. Dra. Iara Leão Luna de Souza (ORCID 0000-0002-5309-2979),
orientadora. Lohana e Ana Beatriz conduziram a validação do método (conferência da lista de referência no Drugs.com e da
extração das seções); a Profa. Iara foi a segunda avaliadora da classificação às cegas. Versões: `NOTAS_DE_VERSAO.md`.
Uso de IA: o código, a leitura integral de referência que serviu para desenvolver o motor e parte da documentação foram feitos
com apoio de assistente de IA (Claude, por meio do Claude Code, Anthropic) e revisados pelos autores; o artigo descreve cada etapa.
