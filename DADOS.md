# Dicionário de dados (`dados/`)

Todos os CSV usam `;` como separador e UTF-8 com BOM. Registros MS têm 9 dígitos e devem ser lidos como texto.

## `registros_estatinas.csv` — 328 registros de estatinas (dados abertos da Anvisa, atualização de 13/10/2026; CMED de 08/11/2026)
| coluna | descrição |
|---|---|
| `registro` | número de registro do produto no Ministério da Saúde (9 dígitos) |
| `estatina` | princípio ativo (atorvastatina, fluvastatina, lovastatina, pitavastatina, pravastatina, rosuvastatina, sinvastatina) |
| `associacao` | `True` se associação em dose fixa (ezetimiba, anlodipino etc.) — excluída do corpus |
| `produto`, `substancias`, `empresa`, `cnpj` | como constam no registro |
| `categoria` | categoria regulatória da Anvisa: Novo, Genérico ou Similar |
| `referencia_declarada`, `eh_referencia` | texto do campo “medicamento de referência” do registro e indicador derivado |
| `situacao`, `vencimento` | situação do registro (Ativo se qualquer apresentação estiver ativa; o arquivo da Anvisa tem uma linha por apresentação) e vencimento |
| `cmed_apresentacoes`, `cmed_comercializado_2025`, `cmed_pmc18_min`, `cmed_pmc18_max` | apresentações na lista CMED, declaração de comercialização em 2025 e faixa do preço-teto ao consumidor (PMC, ICMS 18%) |
| `link_bulario` | abre a busca do Bulário Eletrônico com o registro já preenchido (clique em “Consultar”) |

## `corpus_bulas.csv` — bulas identificadas (109 PDFs de estatinas; 92 no corpus)
| coluna | descrição |
|---|---|
| `registro_ms` | registro lido no texto da bula |
| `estatina`, `produto`, `empresa`, `categoria`, `eh_referencia_declarada` | do registro |
| `no_corpus` | `Sim` = registro ativo em monofármaco (unidade de análise) |
| `motivo_fora` | associação, registro inativo, registro não lido ou versão posterior à coleta (mesmo registro) |
| `sha1` | impressão digital do PDF usado (confira se a sua versão é a mesma) |
| `lote` | `1` = coleta de 11 a 13/11/2026 (85 bulas, B001–B085); `2` = 7 registros incluídos em 14/11/2026, depois da correção da situação dos registros (B086–B092) |

## `exclusoes_sem_bula.csv` — 10 registros ativos sem bula no Bulário (verificado em 13 e 14/11/2026)

## `interacoes_graves_referencia.csv` — 268 pares estatina × fármaco (interações *major* do Drugs.com)
| coluna | descrição |
|---|---|
| `estatina` | estatina (DCB) |
| `farmaco_drugscom` | nome do fármaco interagente no Drugs.com (inglês) |
| `farmaco_dcb` | nome em português: Denominação Comum Brasileira, quando existe (fármacos sem registro no Brasil podem não ter DCB) |
| `registros_ativos_brasil`, `registros_total_brasil`, `registro_ativo_no_brasil` | registros do fármaco interagente no Brasil (dados abertos) |

## `drugscom_major_2026-11-13.json` (só no pacote do Zenodo, não no GitHub) — listas *major* por estatina, como publicadas (inclui “liver disease”/“renal dysfunction”, interações com doença excluídas na análise)

## `amostra_validacao.csv` — 12 bulas (1 por estatina × categoria, sorteada entre as bulas do lote 1; semente 2026; recriada por `estudo/amostra.py`)

## `estatisticas_preclassificacao_v02.json` — resultados da pré-classificação automática, motor v2
`estatisticas_revisadas.json` = mesmas chaves, calculadas com `classificacao_revisada.csv` (números finais do estudo; diferem da pré-classificação pelas correções do consenso e da auditoria).
`estatisticas_preclassificacao.json` = mesmo arquivo para o motor v1 (regras da versão 0.1.0 aplicadas às 92 bulas).
| chave | descrição |
|---|---|
| `geral` | completude mediana e IIQ: `ampla` (nominal + classe), `estrita` (nominal), `ampla_br` (só fármacos registrados no Brasil) |
| `por_estatina`, `por_categoria` | mesmas medidas por estatina e por categoria regulatória |
| `kruskal_categorias_geral`, `generico_vs_similar_por_estatina` | valores de p (Kruskal-Wallis; Mann-Whitney dentro de cada estatina) |
| `manejo_entre_citadas`, `local_entre_citadas` | contagens entre os pares citados |
| `mais_omitidas_registro_br` | fármacos registrados no Brasil omitidos em ≥ 50% das bulas da estatina |

## `preclassificacao_v02.csv` — tabela de pares do motor v2 (4.211 linhas); permite recalcular as estatísticas sem os PDFs
(`python reproduzir_estudo.py --tabela dados/preclassificacao_v02.csv`). Mesmas colunas da saída abaixo.

## Saída `resultados/preclassificacao.csv` (gerada) — 1 linha por bula × interação
`id_bula (B001…B092, código usado no artigo), registro_ms, estatina, categoria, produto, empresa, farmaco_dcb, registro_ativo_no_brasil, citacao (nominal|classe|nao citada),
classe_citada, local (secao de interacoes|outra secao|ambas), manejo (contraindicar/evitar|limite de dose|monitorar|sem orientacao|nao se aplica),
secoes, evidencia` (motor v2: frase da bula que decide o manejo, com a seção entre colchetes; motor v1 tem também `confianca`).

## `configuracao/` — regras do motor v2 (fármacos, classes, expressões). Ver `configuracao/LEIA-ME.md`.

## `classificacao_revisada.csv`
As 4.211 linhas de `preclassificacao_v02.csv` (sem `secoes` e `evidencia`) após a revisão do primeiro avaliador (14–15/11/2026)
e as correções do consenso entre os dois avaliadores e da auditoria pré-publicação (16/11/2026). As colunas `citacao`,
`classe_citada`, `local` e `manejo` têm a classificação final. Montagem em camadas (motor corrigido → mudanças do revisor →
consenso → auditoria), descrita em `NOTAS_DE_VERSAO.md`.

| coluna | conteúdo |
|---|---|
| `conferencia` | como a linha foi conferida: `lida` (lida uma a uma), `texto idêntico ao de bula já lida` (confirmada em bloco com a decisão da bula lida), `ausência verificada no texto` (nem o fármaco nem suas classes aparecem na bula) |
| `alterado_na_revisao` | `Não`, ou `Sim:` seguido das colunas alteradas |
| `observacao_revisao` | nota do revisor |
| `alterado_no_consenso` | `Não`, ou `Sim:` com a coluna, o valor anterior e o novo e a origem: 12 pares (clofibrato em 3 bulas de sinvastatina, amiodarona e fenofibrato/ácido fenofíbrico na B065: frases unidas ou cortadas na extração; 6 fármacos na B056: alinhados às outras 36 bulas de rosuvastatina com o mesmo texto) |
| `alterado_na_auditoria` | `Não`, ou `Sim:` com cada coluna que mudou em relação à classificação anterior à auditoria pré-publicação (separação de seções corrigida; vocabulário de classes alinhado à tabela da FDA; B091 levanlodipino) |

## `avaliacao_dupla/` — classificação às cegas de uma amostra (12 bulas, 477 pares) e consenso
- `amostra_dupla_avaliacao.csv`: `id_bula, registro_ms, estatina, farmaco_dcb, citacao_avaliador1, manejo_avaliador1,
  citacao_avaliadora2, manejo_avaliadora2`. Avaliador 1 = classificação revisada ANTES do consenso; avaliadora 2 = respostas às
  cegas (formulário com citação e manejo; sem local). Recalcule com `python ferramentas/concordancia_avaliadores.py`
  (citação: κ = 0,858, IC95% 0,818–0,898, PABAK 0,862; manejo: κ = 0,536, IC95% 0,484–0,588, PABAK 0,539).
- `decisoes_consenso.csv`: as 12 decisões do consenso (cada item agrupa pares divergentes com o mesmo trecho de bula):
  `A1` = como o avaliador 1, `A2` = como a avaliadora 2.
- `correcoes_consenso.csv`: as alterações aplicadas a `classificacao_revisada.csv` (`id_bula, farmaco_dcb, campo, de, para,
  origem, motivo`), estendidas a todas as bulas do corpus com o mesmo texto.

## `auditoria/correcoes_auditoria.csv` — correções pontuais da auditoria pré-publicação (16/11/2026)
Mesmas colunas de `avaliacao_dupla/correcoes_consenso.csv`. As demais mudanças da auditoria vêm do motor corrigido e estão na
coluna `alterado_na_auditoria` de `classificacao_revisada.csv`.
