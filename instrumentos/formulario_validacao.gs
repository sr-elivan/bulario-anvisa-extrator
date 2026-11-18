// Cole num projeto do Apps Script e execute criarFormularioValidacao.
const PASTA = 'Bulas_amostra_avaliadora2';
const INTRO = "Obrigado por ajudar a validar o método do artigo sobre interações graves nas bulas de estatinas!\n\nEscolha o seu LOTE (A ou B) na próxima página. Cada lote tem duas tarefas curtas:\n\nPARTE 1 · CONFERÊNCIA DO DRUGS.COM (padrão de referência)\nAbra o link indicado (já filtrado para interações \"major\") e confira, para cada fármaco da lista:\n• \"Confirmado como major\": o fármaco aparece na lista com a etiqueta major.\n• \"Aparece, mas com outra gravidade\": está no site, porém como moderate ou minor.\n• \"Não encontrado no site\": não aparece em nenhuma gravidade.\nDepois, anote os fármacos MAJOR que estão no site e faltam na nossa lista (ignore \"liver disease\" e \"renal dysfunction\", que são interações com doenças).\n\nPARTE 2 · VALIDAÇÃO DA EXTRAÇÃO AUTOMÁTICA\nPara cada bula, abra o PDF e o TXT (texto que o programa extraiu da seção de interações). Compare:\n• Completa: o TXT tem toda a seção de interações do PDF, do título até o início da seção seguinte.\n• Parcial: faltou algum parágrafo, tabela ou subtítulo (ex.: faltou a tabela de interações; cortou no meio).\n• Com texto a mais: trouxe junto parte de outra seção (ex.: começou a \"Reações adversas\").\n• Errada/vazia: o TXT não corresponde à seção de interações.\nPequenas diferenças de formatação (quebras de linha, hifenização, tabelas viradas em texto corrido) NÃO contam como erro.\n\nAnote a data da consulta. Tempo estimado: 40–60 min por lote.";
// v0.2.1: a lista de fármacos do Drugs.com foi retirada (termos de uso do site). Para reaplicar o formulário,
// preencha "rows" com a sua própria consulta às páginas indicadas em "url".
const DRUGS = {"atorvastatina": {"en": "atorvastatin", "url": "https://www.drugs.com/drug-interactions/atorvastatin-index.html?filter=3", "rows": []}, "pitavastatina": {"en": "pitavastatin", "url": "https://www.drugs.com/drug-interactions/pitavastatin-index.html?filter=3", "rows": []}, "pravastatina": {"en": "pravastatin", "url": "https://www.drugs.com/drug-interactions/pravastatin-index.html?filter=3", "rows": []}, "rosuvastatina": {"en": "rosuvastatin", "url": "https://www.drugs.com/drug-interactions/rosuvastatin-index.html?filter=3", "rows": []}, "sinvastatina": {"en": "simvastatin", "url": "https://www.drugs.com/drug-interactions/simvastatin-index.html?filter=3", "rows": []}};
const LOTES = {"A": ["atorvastatina", "pitavastatina", "pravastatina"], "B": ["rosuvastatina", "sinvastatina"]};
const BULAS_LOTE = {"A": ["B005", "B014", "B017", "B018", "B022", "B026"], "B": ["B031", "B052", "B066", "B081", "B082", "B083"]};
const BULAS = {"B005": {"produto": "ATORVASTATINA CÁLCICA", "estatina": "atorvastatina", "empresa": "Brainfarma Indústria Química E Farmacêutica S.A"}, "B014": {"produto": "CITALOR", "estatina": "atorvastatina", "empresa": "Viatris Farmaceutica Do Brasil Ltda"}, "B017": {"produto": "CRESTOR", "estatina": "rosuvastatina", "empresa": "Astrazeneca Do Brasil Ltda"}, "B018": {"produto": "EBATZ", "estatina": "pitavastatina", "empresa": "Libbs Farmacêutica Ltda"}, "B022": {"produto": "LIVALO", "estatina": "pitavastatina", "empresa": "Biolab Sanus Farmacêutica Ltda"}, "B026": {"produto": "pitavastatina cálcica", "estatina": "pitavastatina", "empresa": "Ems S/A"}, "B031": {"produto": "Pravastatina Sódica", "estatina": "pravastatina", "empresa": "Accord Farmacêutica Ltda"}, "B052": {"produto": "rosuvastatina cálcica", "estatina": "rosuvastatina", "empresa": "Pharlab Indústria Farmacêutica S.A."}, "B066": {"produto": "SINVASMAX", "estatina": "sinvastatina", "empresa": "Laboratório Globo Sa"}, "B081": {"produto": "SINVASTATINA", "estatina": "sinvastatina", "empresa": "Sandoz Do Brasil Indústria Farmacêutica Ltda"}, "B082": {"produto": "TORVILIP", "estatina": "atorvastatina", "empresa": "Multilab Industria E Comercio De Produtos Farmaceuticos Ltda"}, "B083": {"produto": "TREZOR", "estatina": "rosuvastatina", "empresa": "Aché Laboratórios Farmacêuticos S.A"}};

function criarFormularioValidacao() {
  const pasta = DriveApp.getFoldersByName(PASTA).next();
  const pdf = {}, txt = {};
  const arqs = pasta.getFiles();
  while (arqs.hasNext()) {
    const f = arqs.next(), n = f.getName(), id = n.slice(0, 4);
    if (!/^B\d{3}/.test(n)) continue;
    f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    if (/\.pdf$/i.test(n)) pdf[id] = f.getUrl();
    if (/\.txt$/i.test(n)) txt[id] = f.getUrl();
  }
  const form = FormApp.create('Validação do método – Drugs.com e extração das bulas (colaboradoras)');
  form.setDescription(INTRO).setProgressBar(true).setAllowResponseEdits(true);
  form.addTextItem().setTitle('Seu nome').setRequired(true);
  form.addDateItem().setTitle('Data da consulta ao Drugs.com').setRequired(true);
  const escolha = form.addMultipleChoiceItem().setTitle('Qual é o seu lote?').setRequired(true);
  const inicio = {};
  Object.keys(LOTES).forEach(function (lote) {
    let primeira = null;
    LOTES[lote].forEach(function (est) {
      const d = DRUGS[est];
      const pg = form.addPageBreakItem().setTitle('Lote ' + lote + ' · Parte 1 · Drugs.com – ' + est)
        .setHelpText('Abra: ' + d.url + '\n(se pedir, aceite apenas os cookies necessários). Confira cada fármaco da lista abaixo (' + d.rows.length + ' itens).');
      if (!primeira) primeira = pg;
      form.addGridItem().setTitle(est + ' · interações graves (major) da nossa lista')
        .setRows(d.rows).setColumns(['Confirmado como major', 'Aparece, mas com outra gravidade', 'Não encontrado no site']).setRequired(true);
      form.addParagraphTextItem().setTitle(est + ' · Fármacos MAJOR no site que NÃO estão na lista (um por linha; escreva "nenhum" se não houver)').setRequired(true);
      form.addTextItem().setTitle(est + ' · Total de interações major que o site informa (número no topo da página)');
    });
    BULAS_LOTE[lote].forEach(function (id) {
      const b = BULAS[id];
      form.addPageBreakItem().setTitle('Lote ' + lote + ' · Parte 2 · Extração – ' + id + ' ' + b.produto + ' (' + b.estatina + ')')
        .setHelpText('Empresa: ' + b.empresa + '\nPDF da bula: ' + (pdf[id] || '?') + '\nTexto extraído (TXT): ' + (txt[id] || '?'));
      form.addMultipleChoiceItem().setTitle(id + ' · A seção de interações extraída está:')
        .setChoiceValues(['Completa', 'Parcial (faltou trecho)', 'Com texto a mais (de outra seção)', 'Errada ou vazia']).setRequired(true);
      form.addParagraphTextItem().setTitle(id + ' · O que faltou ou sobrou? (opcional)');
    });
    inicio[lote] = primeira;
  });
  escolha.setChoices(Object.keys(LOTES).map(function (l) {
    return escolha.createChoice('Lote ' + l + ' (' + LOTES[l].join(', ') + ' + bulas ' + BULAS_LOTE[l].join(', ') + ')', inicio[l]);
  }));
  // quem termina o lote A vai direto para o envio (não continua no lote B)
  inicio['B'].setGoToPage(FormApp.PageNavigationType.SUBMIT);
  const ss = SpreadsheetApp.create('Respostas – validação do método (colaboradoras)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  DriveApp.getFileById(form.getId()).moveTo(pasta);
  DriveApp.getFileById(ss.getId()).moveTo(pasta);
  Logger.log('EDITAR: ' + form.getEditUrl());
  Logger.log('LINK PARA AS COLABORADORAS: ' + form.getPublishedUrl());
  Logger.log('PLANILHA: ' + ss.getUrl());
  Logger.log('PDF: ' + Object.keys(pdf).length + ' | TXT: ' + Object.keys(txt).length);
}
