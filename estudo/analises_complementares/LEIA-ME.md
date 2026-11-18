# Análises complementares do artigo

Scripts das análises do artigo que não saem de `reproduzir_estudo.py`. Os dois primeiros leem só
`dados/classificacao_revisada.csv` (classificação final) e gravam em `resultados/`.

| Script | O que reproduz no artigo | Comando |
|---|---|---|
| `sensibilidade.py` | Tabela 4 (estrita 40,8%; ampla 82,5%; sem transportadores 70,0%; L04 e transportadores 82,5%; sem "certos inibidores de protease" 72,5%), peso igual por estatina (73,0%), citações só por classe (48,7%), completude só com orientação de manejo (67,5%) | `python sensibilidade.py` |
| `divergencias_entre_bulas.py` | Consistência entre bulas da mesma estatina: 180 de 194 combinações idênticas (14 variam), 32 pares e 16 bulas fora da classificação mais frequente | `python divergencias_entre_bulas.py` |
| `vigimed_estatinas.py` | Seção sobre o VigiMed (7.020 notificações com estatina; 1.078 com fármaco da lista; sinvastatina + anlodipino 346; etc.) | `python vigimed_estatinas.py PASTA` |

## VigiMed

O script precisa dos três arquivos dos dados abertos da Anvisa (`VigiMed_Notificacoes.csv`, `VigiMed_Medicamentos.csv` e
`VigiMed_Reacoes.csv`, https://dados.anvisa.gov.br/dados/), que não são redistribuídos aqui. O artigo usou a versão de 5 de outubro
de 2026. Como a base é atualizada, uma versão posterior dá números diferentes. Em `resultados/` estão os resultados agregados
daquela execução (`vigimed_resumo.json` e `vigimed_pares_graves.csv`), sem dados por notificação.

## Números que não saem destes scripts

Os 77 pares em que a bula cita o fármaco para negar a interação (mediana de 77,6% sem eles) foram identificados pela marca de
negação da pré-classificação v0.1, que não faz parte deste pacote.
