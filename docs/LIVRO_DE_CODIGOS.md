# Livro de códigos

> Critérios de classificação do estudo, que o motor v2 implementa. Escritos para a leitura integral de referência das 85 bulas
> do lote 1 (13/11/2026; leitura feita pela ferramenta de IA e conferida pelos autores) e completados com as decisões da dupla
> avaliação, do consenso entre os avaliadores e da auditoria pré-publicação (16/11/2026). As listas de classes e as expressões
> de manejo estão em `configuracao/` (ver `configuracao/LEIA-ME.md`).

Unidade de análise: bula × interação grave de referência (Drugs.com *major*): 92 bulas, 4.211 pares no estudo final.
Unidade de leitura: cada **trecho distinto** do corpus que cita o fármaco pelo nome ou que cita uma classe/mecanismo.
Cada trecho é lido uma vez e recebe um rótulo; a decisão de cada bula sai dos trechos que ela contém.

## Citação
- **nominal**: o nome (DCB, ou grafia evidente do mesmo fármaco) aparece na bula, inclusive em tabelas de farmacocinética. O motor
  lê as seções 3 a 8 (características farmacológicas, contraindicações, advertências e precauções, interações e posologia); no
  estudo, nenhum par "não citado" tinha o nome em outra parte do PDF.
  Grafia errada da bula (ex.: "bocepravir") conta como nominal e é anotada.
- **classe**: o nome não aparece, mas uma seção orientadora (interações, contraindicações, advertências, posologia) cita uma
  classe ou mecanismo que inclui o fármaco **sem dúvida farmacológica** (ex.: "inibidores potentes do CYP3A4", "inibidores moderados do
  CYP3A4", "inibidores de protease do HIV", "antifúngicos azólicos", "fibratos"). Expressões vagas ("certos medicamentos",
  "fármacos que inibem certas vias enzimáticas") não contam. Decisão do consenso (item 8): "certos inibidores de protease … (consulte
  a Tabela 4)" na rosuvastatina conta como classe para os inibidores de protease não nomeados (a análise de sensibilidade mostra o
  efeito de não contá-los).
- **Título de classe** seguido de exemplos (ex.: "Bloqueadores do canal de cálcio: verapamil, diltiazem, anlodipino") cita por classe
  os demais membros da classe, sem orientação (consenso, item 10: levanlodipino nas bulas de sinvastatina).
- **não citada**: nenhum dos dois.

## Local
Seções em que o fármaco é tratado, pelo nome ou por classe: **seção de interações**, **outra seção**, **ambas**.

## Manejo (o mais restritivo que se aplica AO FÁRMACO, isoladamente)
1. **contraindicar/evitar**: contraindicado, não usar, evitar, não recomendado, suspender/interromper a estatina durante o uso
   (inclusive "considerar a suspensão/interrupção temporária", mesmo com "a menos que os benefícios superem os riscos", ex.:
   daptomicina, ácido fusídico) e menção na lista da seção 4 (Contraindicações). **Exceção (regra 9):** quando o mesmo trecho dá
   como saída o ajuste de dose ("se a coadministração for inevitável, … ajustes da posologia"), registra-se **limite de dose** (ex.:
   parágrafo "terapia concomitante" da rosuvastatina; mantido no consenso, item 1).
2. **limite de dose**: dose máxima, dose inicial reduzida, "ajuste/redução da dose", "menor dose necessária"; inclui o fármaco
   listado em tabela cujo título/regra exige ajuste de dose (ex.: Tabela 4 da rosuvastatina) e contraindicação **condicionada à dose**
   (ex.: "contraindicado com doses > 40 mg").
3. **monitorar**: cautela, precaução, monitorar sinais/CK/INR, avaliar risco-benefício, orientação de horário de administração.
4. **sem orientação**: o fármaco é citado sem nenhuma orientação prática (ex.: só dado de farmacocinética), ou a bula afirma
   ausência de interação relevante.

Regras de aplicação:
- Restrição que vale só para uma **combinação** (ex.: "letermovir + ciclosporina não recomendado") não se transfere a cada fármaco isolado.
- **Exceções explícitas** são respeitadas (ex.: "fibratos, exceto fenofibrato → ≤ 10 mg": não vale para o fenofibrato).
- Negação **parcial** (ex.: "nenhuma interação farmacocinética, mas pode haver interação farmacodinâmica") não anula a orientação.
- Uma orientação genérica de classe vale para os membros da classe também quando citados pelo nome em outro ponto.
- Orientação na **frase seguinte** que retoma o fármaco por anáfora ("estes medicamentos", "os medicamentos citados", "esta combinação",
  "devem ser considerados os benefícios e riscos") vale para ele (verificado por varredura de todas as frases seguintes no estudo).
- Restrição só para uma **subpopulação** (ex.: "não recomendada para pacientes asiáticos") não se transfere: registra-se a orientação geral e uma nota.
- Pertinência a classe: listas do estudo (configuracao/classes.csv) + bula/label oficial do fármaco e tabela da FDA de inibidores de CYP e transportadores (ex.: teriflunomida e vadadustate inibem BCRP).
- Grafia errada da bula (ex.: "bocepravir", "BCPR") é lida como o termo correto, com nota.
- Ácido fenofíbrico é a forma ativa do fenofibrato: quando a bula fala do fenofibrato e não nomeia o ácido fenofíbrico, este é
  citado por classe, com a mesma orientação e as mesmas exceções do fenofibrato.
- Na dúvida entre duas categorias, registra-se a **menos restritiva** e uma nota.
- "Não é necessário ajuste de dose" anula a orientação de dose, mas não a de monitorar ou de cautela na mesma frase.
- Equivalências: só pró-fármaco → forma ativa listados separadamente na referência (ácido fenofíbrico → fenofibrato). Enantiômeros
  (levanlodipino, levocetoconazol) são fármacos distintos na referência e só são citados pelo nome ou por uma classe que os inclua.
- Força da inibição do CYP3A4 (potente/moderado/fraco): tabela da FDA (consulta em 16/11/2026); para fármacos fora dela, a bula do
  próprio fármaco (ex.: mifepristona = potente, Korlym: aumento de 10–16 vezes da ASC da sinvastatina). "Inibidores do CYP3A4" sem
  qualificação inclui potentes, moderados e fracos.

## Rótulos usados na leitura
`C` contraindicar/evitar · `L` limite de dose · `M` monitorar · `S` citado sem orientação · `N` bula afirma ausência de interação ·
`0` o trecho não se refere a este fármaco (ex.: só cita para outra combinação; falso alarme).
