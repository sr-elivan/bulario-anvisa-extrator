# Configuração do motor v2

O motor v2 (`estudo/classificar.py`) não tem vocabulário escrito no código. Os fármacos que procura, as classes e mecanismos que
reconhece e as expressões que indicam cada tipo de orientação vêm dos arquivos desta pasta. Os arquivos que estão aqui são
os usados no estudo das estatinas. Para estudar outra classe de medicamentos, copie a pasta, edite as tabelas e rode o motor
com `--config` (veja "Usar outra configuração").

Todos os arquivos são CSV com `;` como separador e codificação UTF-8. Abrem no Excel ou no LibreOffice; ao salvar, mantenha
"CSV (separado por ponto e vírgula)" e UTF-8. Se preferir trabalhar numa planilha só, converta:

```bash
python ferramentas/configuracao_planilha.py --para-xlsx configuracao minha_configuracao.xlsx   # uma aba por arquivo
python ferramentas/configuracao_planilha.py --validar minha_configuracao.xlsx                  # confere antes de usar
```

## Arquivos

| arquivo | o que contém | colunas |
|---|---|---|
| `alvos.csv` | fármacos-alvo do estudo (aqui, as estatinas) | `nome_en` (como na base de referência), `dcb` |
| `referencia_ignorar.csv` | itens da base de referência que não são fármacos | `termo_en`, `motivo` |
| `farmacos.csv` | fármacos interagentes procurados nas bulas | `nome_en`, `dcb`, `busca_no_texto`, `grafias_alternativas`, `equivalente_a`, `fonte` |
| `classes.csv` | classes e mecanismos que incluem um fármaco sem dúvida farmacológica | `ordem`, `classe`, `alternativa`, `expressao_no_texto`, `membros_dcb`, `fonte` |
| `expressoes.csv` | expressões de manejo, de negação, de exceção, de retomada e de tabelas | `regra`, `alternativa`, `expressao`, `descricao` |

### `farmacos.csv`
- `busca_no_texto`: radical procurado no texto da bula. Só casa no início de uma palavra: `amprenavir` não é encontrado dentro de
  `fosamprenavir`. Para aceitar mais de uma forma, separe com `|` (ex.: `genfibrozil|gemfibrozil`).
- `grafias_alternativas`: grafias erradas encontradas nas bulas e lidas como o fármaco (ex.: `bocepravir`).
- `equivalente_a`: o fármaco segue as orientações e exceções de outro (ex.: ácido fenofíbrico → fenofibrato, sua forma ativa).

### `classes.csv`
- Cada classe pode ter várias formas de aparecer no texto: uma linha por forma (`alternativa` 1, 2, 3…).
- `membros_dcb` (só na linha da alternativa 1): fármacos da classe, pela DCB, separados por ` | `. Todos precisam existir em
  `farmacos.csv`; se não existirem, o programa para e diz qual falta.
- `ordem`: ordem em que as classes são testadas.
- Duas classes são usadas pelo nome no código: `inibidores do OATP1B1` e `inibidores da BCRP`. A frase "inibidores destas
  proteínas transportadoras" das bulas de rosuvastatina inclui os membros das duas. Mantenha esses nomes se essa regra for útil.

### `expressoes.csv`
Cada `regra` agrupa as expressões de um tipo (uma por linha). O motor junta as linhas da mesma regra com `|`.

| regra | efeito no motor |
|---|---|
| `manejo_contraindicar`, `manejo_limite_dose`, `manejo_monitorar` | orientação da frase que cita o fármaco ou a classe; vale a mais restritiva |
| `sem_ajuste` | "não é necessário ajuste de dose" anula o limite de dose |
| `nega_interacao`, `nega_parcial` | a bula afirma que não há interação relevante, salvo ressalva (ex.: "interação farmacodinâmica pode ocorrer") |
| `dose_condicional` | contraindicação só acima de certa dose: vira limite de dose |
| `subpopulacao` | restrição só para uma subpopulação: não se transfere ao fármaco |
| `excecao` | início de exceção ("exceto", "com exceção de"): o fármaco excetuado não herda a orientação da classe |
| `anafora` | frase seguinte que retoma os fármacos da anterior ("estes medicamentos") e herda a orientação |
| `paragrafo_transportadores`, `orientacao_transportadores` | parágrafo "Terapia concomitante" da rosuvastatina: orientação 1 a 6 frases depois |
| `tabela_regra`, `tabela_inicio`, `tabela_fim` | tabela de exposição com regra de ajuste de dose (ex.: Tabela 4 da rosuvastatina) |

## Como escrever as expressões
São expressões regulares (Python, módulo `re`), comparadas com o texto da bula em minúsculas e sem acentos: escreva
`contraindicad`, não `Contraindicado`. Os recursos mais usados:

| escrito | significa | exemplo |
|---|---|---|
| `\w*` | resto da palavra | `inibidor\w*` casa "inibidor", "inibidores" |
| `\s+` | um ou mais espaços | `nao\s+deve` |
| `(?:a\|b)` | uma das opções | `(?:cyp\s?3a4\|3a4)` |
| `?` | o item anterior é opcional | `doses?` casa "dose" e "doses" |
| `\b` | limite de palavra | `evitar\b` não casa "evitaram" |
| `\d+` | número | `nao mais que \d` |

Para conferir uma configuração nova sem rodar o estudo inteiro, use `--validar`: o programa aponta o arquivo, a linha e o erro
(membro que não existe, expressão inválida, regra obrigatória faltando).

## Usar outra configuração
```bash
python reproduzir_estudo.py --pdfs PASTA_DAS_BULAS --config minha_configuracao        # pasta com os CSV
python reproduzir_estudo.py --pdfs PASTA_DAS_BULAS --config minha_configuracao.xlsx   # ou planilha
```
Também é possível definir a variável de ambiente `BULARIO_CONFIG`. A lista de interações de referência continua em
`dados/interacoes_graves_referencia.csv` (colunas `estatina`, `farmaco_dcb`, `registro_ativo_no_brasil`): no estudo, a coluna
`estatina` é o fármaco-alvo.

## De onde vieram as listas do estudo
A coluna `fonte` registra a origem de cada linha:
- os nomes em português seguem a DCB (Anvisa) quando ela existe, e os nomes em inglês vêm da base de referência;
- a pertinência às classes de CYP3A4 e de transportadores vem da tabela da FDA de inibidores de CYP e transportadores (2026),
  conferida na bula de cada fármaco;
- as demais classes seguem a classificação ATC da OMS.

As expressões de manejo implementam o livro de códigos (`docs/LIVRO_DE_CODIGOS.md`). O artigo descreve como as listas foram
montadas e testadas. Com estes arquivos, o motor dá exatamente os resultados do estudo, e o teste
`tests/test_configuracao.py` garante isso.
