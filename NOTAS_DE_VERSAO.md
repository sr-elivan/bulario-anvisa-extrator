# Notas de versão

Formato: versão (data) — o que mudou. Versões seguem [SemVer](https://semver.org/lang/pt-BR/): mudança de dados ou de regra
que altera resultados sobe a versão intermediária; correção sem efeito nos resultados sobe a última.

## 0.2.1 (18/11/2026) — dados de terceiros, transparência e análises complementares
Nenhum resultado do estudo mudou.
- **Drugs.com:** os termos de uso do site proíbem copiar ou redistribuir partes dele sem autorização. Saíram do depósito a lista
  bruta (`drugscom_major_2026-11-13.json`), a coluna `farmaco_drugscom` de `interacoes_graves_referencia.csv` e a lista em inglês
  embutida em `instrumentos/formulario_validacao.gs`. Ficam os pares do estudo em DCB, necessários para verificar a classificação
  (não cobertos pela CC BY; ver `LICENSE-DATA`).
- **Análises complementares** (`estudo/analises_complementares/`): sensibilidade (Tabela 4 do artigo), divergências entre bulas
  da mesma estatina e VigiMed, com os resultados agregados.
- **README:** a validação independente (kappa, 12 bulas) aparece antes da concordância no conjunto de desenvolvimento; uso de IA
  explicado; limitações de hifenização e de validação preliminar; contagem correta dos testes.
- `bulario/texto.py`: docstring indica o Xpdf 4.00.

## 0.2.0 (16/11/2026) — versão do artigo do XVIII EICEA
Autores: Elivan da Silva; Lohana Souza Galvão; Ana Beatriz Lucena Brito; Iara Leão Luna de Souza (orientadora).
- Corpus: 92 bulas de cinco estatinas com registro ativo (7 incluídas após a revisão da lista de registros: B086–B092).
- Motor v2: leitura frase a frase segundo o livro de códigos (`docs/LIVRO_DE_CODIGOS.md`); regras em tabelas editáveis
  (`configuracao/`, ou planilha via `ferramentas/configuracao_planilha.py`).
- Classificação revisada por humanos: os 4.211 pares conferidos pelo avaliador 1 (`classificacao_revisada.csv`).
- Validação do método: conferência da lista de referência no Drugs.com e da extração das seções (Lohana e Ana Beatriz).
- Dupla avaliação às cegas de 12 bulas (avaliadora 2) e consenso: 12 pares corrigidos no corpus (`avaliacao_dupla/`,
  coluna `alterado_no_consenso`); só as contagens de manejo mudaram.
- Reprodução em um comando (`reproduzir_estudo.py`) e testes automatizados (`tests/`).

### Auditoria pré-publicação (16/11/2026), incorporada à 0.2.0
Três instâncias independentes da ferramenta de IA (Claude) receberam o pacote, o vocabulário em planilha e os PDFs, reproduziram
o estudo (tudo "IDÊNTICO") e auditaram o processo; os autores conferiram e corrigiram:
- **Separação de seções** (`bulario/texto.py`): subtítulo "Interações medicamentosas" dentro da seção 5 não abre mais a seção 6
  quando a bula numera os títulos; títulos "5.ADVERTÊNCIAS" e "5. ADVERTÊNCIAS E" (partido) reconhecidos. Corrige o campo `local`
  em 24 bulas de sinvastatina, B056 e B079 (271 pares; "só seção de interações" entre as citadas: 638 → 301).
- **Vocabulário** (`configuracao/classes.csv`), alinhado à tabela da FDA consultada em 16/11/2026: ranolazina e amiodarona saem de
  "moderados" (são fracos); conivaptana passa de "potentes" a "moderados"; mifepristona passa a "potentes" (bula do Korlym);
  danazol sai das classes do CYP3A4 (sem mecanismo estabelecido nas fontes); ciclosporina e ticagrelor (fracos) entram em
  "inibidores do CYP3A4"; oteseconazol entra em BCRP; genfibrozila e darolutamida, em OATP1B1. Efeito: 43 citações por classe
  retiradas; completude ampla mediana inalterada (82,5%), sinvastatina 89,2% → 87,7%, atorvastatina 81,6% → 79,6%.
- **B091 levanlodipino**: limite de dose → sem orientação (`dados/auditoria/correcoes_auditoria.csv`).
- **Livro de códigos**: regra 9 (suspensão/interrupção temporária e a exceção do ajuste de dose), decisões do consenso, regra
  da seção 4, equivalências e força de inibição documentadas.
- **Licença**: retirado o texto literal do Drugs.com (cabeçalhos do JSON e abas da planilha); fica só a lista de fármacos.
- **README**: o `pdftotext` que reproduz o estudo é o do Xpdf 4.00.
- Limitações conhecidas, sem efeito no corpus atual: o motor não lê a coluna `subtitulo` (linhas em negrito); "não é necessário
  ajuste" na mesma frase de "cautela" anula também a cautela; "rifampina" não é reconhecida como grafia de rifampicina.
- Decisões de interpretação mantidas (consenso) e sua sensibilidade: ler o parágrafo de terapia concomitante da rosuvastatina como
  contraindicação inverteria o manejo predominante (cerca de 900 pares de limite para contraindicar); não contar "certos inibidores
  de protease" como classe reduziria a completude ampla mediana para 72,5%.

## 0.1.0 (14/11/2026) — interna, não publicada
- Primeira versão do extrator e do motor (regras por janela de caracteres; ainda disponível com `--motor v1`).

## Planejado (projeto de 6 meses ou mais, mesma equipe)
- Banco de dados aberto de interações medicamentosas descritas nas bulas brasileiras, a partir deste motor.
- Ampliação para outras classes terapêuticas e para a bula do paciente; atualização periódica do corpus.
- Revisão do vocabulário de classes e mecanismos com especialistas; nova rodada de validação com dupla avaliação.
