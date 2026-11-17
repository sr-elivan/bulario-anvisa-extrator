#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""classificar.py - motor v0.2 da classificação de cada par bula × interação grave, POR FRASE.

Implementa o livro de códigos da leitura integral de referência (docs/LIVRO_DE_CODIGOS.md):
- citação  : nominal (nome DCB, ou grafia errada conhecida, em qualquer seção) | classe (classe/mecanismo em seção orientadora) | nao citada
- local    : seções em que o fármaco é tratado (nome em qualquer seção; classe nas orientadoras) -> interações / outra / ambas
- manejo   : o mais restritivo que se aplica AO FÁRMACO, frase a frase:
             contraindicar/evitar > limite de dose > monitorar > sem orientação
  * a orientação é lida só na frase que cita o fármaco (não "vaza" para a vizinha);
  * a frase SEGUINTE com anáfora ("estes medicamentos", "os medicamentos citados", "esta combinação"...) transmite a orientação;
  * exceções explícitas ("exceto fenofibrato", "fibratos diferentes de genfibrozila ou fenofibrato") são respeitadas;
  * restrição só para uma combinação ("letermovir coadministrado com ciclosporina") não se transfere a cada fármaco;
  * contraindicação condicionada à dose ("com doses > 40 mg") = limite de dose; restrição só para subpopulação = monitorar;
  * fármaco listado em tabela de efeito na exposição cuja bula manda ajustar a dose = limite de dose
    (exceto se a própria bula afirmar que não há interação clinicamente relevante com aquele fármaco);
  * classe usada como título ("- Bloqueadores do canal de cálcio - verapamil ou diltiazem: ...") só recebe a orientação escrita antes dela.
Retorna, para cada par, também as evidências (frases) que justificam a decisão."""
import re
import sqlite3

from regras import (ALIASES, ANAFORA_V2, CLASSES_V2, DCB, DOSE_CONDICIONAL_V2, EQUIVALENTE, EXCECAO_V2, MANEJO_V2, NEGA_PARCIAL_V2, NEGA_V2, ORIENT_TRANSP_V2,
                    PARAGRAFO_TRANSP_V2,
                    SEM_AJUSTE_V2, SUBPOPULACAO_V2, TABELA_FIM_V2, OATP_V2, BCRP_V2, TABELA_INICIO_V2, TABELA_REGRA_V2, rx_farmaco, sa)

SECOES = ["interacoes", "contraindicacoes", "advertencias_precaucoes", "posologia", "caracteristicas_farmacologicas"]
ORIENTADORAS = {"interacoes", "contraindicacoes", "advertencias_precaucoes", "posologia"}
PRIOR = {"C": 4, "L": 3, "M": 2, "S": 1, "N": 1}
MANEJO = {"C": "contraindicar/evitar", "L": "limite de dose", "M": "monitorar", "S": "sem orientacao", "N": "sem orientacao"}
# "●" (marcador de lista da bula UNAK) também inicia frase, como "•" (14/11/2026)
# não quebra a frase depois de "item 5." / "itens 4." / "vide 8." (referência a seção, não fim de frase)
_QUEBRA = re.compile(r"(?<![Ii]tem \d\.)(?<![Ii]tens \d\.)(?<![Vv]ide \d\.)(?<![Vv]er \d\.)(?<!\be \d\.)(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕ\-•●(−–])")


# item de lista que começa em minúscula depois do ponto: "... dose. fenofibratos / derivados do ácido fíbrico: ..." / "... 75 mg. ticagrelor: ..."
_ITEM = re.compile(r"(?<=[.;])\s+(?=[-−–]?\s*[a-záéíóúâêôãõç][\w\s/,()-]{2,70}?:\s)")


# cabeçalho/rodapé de página no meio do texto ("rosuvastatina cálcica - comprimido revestido - Bula para o profissional de saúde 13")
_CABECALHO = re.compile(r"[\wÀ-ÿ®]+(?: [\wÀ-ÿ®]+){0,3}\s*[-–−]\s*comprimidos? revestidos?\s*[-–−]\s*bula para o profissional(?: d[ae])?(?: sa[uú]de)?\s*\d*", re.I)


def frases(txt):
    out = []
    for f in _QUEBRA.split(_CABECALHO.sub(" ", txt or "")):
        out += [g for g in _ITEM.split(f) if g.strip()]
    return [re.sub(r"\s+", " ", sa(f)).strip() for f in out if f.strip()]


def rx_nome(dcb_pt, en):
    base = rx_farmaco(en).pattern
    if dcb_pt in ALIASES:
        base += r"|(?<![a-z])(?:" + ALIASES[dcb_pt] + ")"
    return re.compile(base)


_REMISSAO = re.compile(r"\((?:vide|veja|ver|consulte|conforme)[^)]*\)?|(?:vide|veja|ver)(?: os| o)? (?:itens?|secao|secoes|tabela)?[^.;]{0,90}?(?:precaucoes|contraindicacoes|posologia e modo de usar|interacoes medicamentosas)|advertencias e precaucoes")


def _cues(s):
    """rótulo de uma frase (sem considerar a quem se aplica). Remissões a seções ('vide Advertências e Precauções') não contam."""
    s = _REMISSAO.sub(" ", s)
    if re.search(SEM_AJUSTE_V2, s) and not re.search(MANEJO_V2[0][1], s):
        return "N"
    neg = re.search(NEGA_V2, s) and not re.search(NEGA_PARCIAL_V2, s)
    for rot, rx in MANEJO_V2:
        if re.search(rx, s):
            if rot == "C" and re.search(DOSE_CONDICIONAL_V2, s):
                return "L"
            if rot == "C" and re.search(SUBPOPULACAO_V2, s):
                return "M"
            return rot
    return "N" if neg else "S"


def _excluido(s, rx):
    """o fármaco aparece logo depois de 'exceto/além de/diferente de ...' (exceção explícita)?"""
    for m in re.finditer(EXCECAO_V2, s):
        trecho = s[m.end():m.end() + 160]
        corte = re.search(r"\b(?:a dose|nao deve|podem|estes|deve-se)\b", trecho)
        if rx.search(trecho[:corte.start()] if corte else trecho):
            return True
    return False


def _combinacao(s, rx_f, rx_outros):
    """'... X coadministrado com Y' + restrição: a restrição é da COMBINAÇÃO, não do fármaco isolado."""
    m = rx_f.search(s)
    if not m:
        return False
    viz = s[max(0, m.start() - 40):m.end() + 40]
    return bool(re.search(r"coadministrad\w* com", viz)) and any(r.search(viz) for r in rx_outros)


def _regiao_tabela(fs):
    """índices das frases que formam a tabela de efeito na exposição, se a bula tiver a regra de ajuste de dose."""
    txt = " ".join(fs)
    if not re.search(TABELA_REGRA_V2, txt):
        return set()
    dentro, ids = False, set()
    for i, f in enumerate(fs):
        if not dentro and re.search(TABELA_INICIO_V2, f):
            dentro = True
        if dentro:
            fim = re.search(TABELA_FIM_V2, f)
            ids.add(i)
            if fim and not re.search(TABELA_INICIO_V2, f[:fim.start()]):
                break
    return ids


def classificar_bula(secs, referencia):
    """secs: {chave_secao: texto}; referencia: [(dcb_pt, en)] -> {dcb_pt: dict(citacao, classe_citada, local, manejo, evidencias)}"""
    F = {k: frases(secs.get(k, "")) for k in SECOES}
    tab = {k: (_regiao_tabela(F[k]) if k == "interacoes" else set()) for k in SECOES}
    rx = {d: rx_nome(d, en) for d, en in referencia}
    outros = {d: [r for o, r in rx.items() if o != d] for d in rx}
    res = {}
    for d, _ in referencia:
        ev = []   # (tipo, seção, rótulo, frase, classe)
        nega_especifica = False
        for k in SECOES:
            fs = F[k]
            for i, s in enumerate(fs):
                nx = fs[i + 1] if i + 1 < len(fs) else ""
                herda = bool(nx) and re.search(ANAFORA_V2, nx) and not any(r.search(nx) for r in rx.values())
                transp = bool(re.search(PARAGRAFO_TRANSP_V2, s)) and bool(re.search(ORIENT_TRANSP_V2, " ".join(fs[i + 1:i + 7])))
                # --- pelo nome
                if rx[d].search(s):
                    if _excluido(s, rx[d]) or _combinacao(s, rx[d], outros[d]):
                        rot = "S"
                    else:
                        rot = _cues(s)
                        if k == "contraindicacoes" and rot not in ("L", "M"):
                            rot = "L" if re.search(DOSE_CONDICIONAL_V2, s) else "C"
                        if herda and PRIOR[_cues(nx)] > PRIOR[rot]:
                            rot = _cues(nx)
                        if transp and PRIOR["L"] > PRIOR[rot]:
                            rot = "L"
                        if i in tab[k] and rot != "N":
                            ant = s[:rx[d].search(s).start()]
                            rot = "S" if re.search(r"diminuic\w* da asc", ant) else max(rot, "L", key=PRIOR.get)
                    if re.search(r"nao ha interac\w* (?:medicamentosa )?clinicamente relevante entre o", s):
                        nega_especifica = True
                    ev.append(("nome", k, rot, s, "", i in tab[k]))
                # --- pela classe (só seções orientadoras)
                if k not in ORIENTADORAS:
                    continue
                for nome, (crx, membros) in CLASSES_V2.items():
                    if nome.startswith("inibidores das proteínas transportadoras"):  # quais transportadores a bula nomeou ali
                        ctx = (fs[i - 1] if i else "") + " " + s
                        membros = set(OATP_V2) | (set(BCRP_V2) if re.search(r"bcrp|abcg2", ctx) else set())
                    alvo = d if d in membros else (EQUIVALENTE.get(d) if EQUIVALENTE.get(d) in membros else None)
                    if not alvo:
                        continue
                    m = re.search(crx, s)
                    if not m:
                        continue
                    # "o glecaprevir e o pibrentasvir SÃO inibidores de OATP1B1": predicado sobre fármacos nomeados, não uma classe
                    if re.search(r"(?:^|\s)(?<!que )sao\s+(?:potentes\s+|fortes\s+|fracos\s+)?$", s[:m.start()]):  # "X e Y sao inibidores ..." (nao "medicamentos QUE sao"; "a sinvastatina e um inibidor da BCRP" = conjuncao)
                        continue
                    # aposto que descreve o fármaco nomeado: "itraconazol (um inibidor do CYP3A4)", "o cetoconazol, um inibidor potente"
                    if re.search(r"(?:\(|,)\s*uma?\s+$", s[:m.start()]):
                        continue
                    rx_alvo = rx[d] if alvo == d else rx_nome(alvo, _en(alvo))
                    if _excluido(s, rx_alvo) or _excluido(s, rx[d]) or (d in EQUIVALENTE and _excluido(s, rx_nome(EQUIVALENTE[d], _en(EQUIVALENTE[d])))):
                        continue
                    titulo = bool(re.match(r"\s*\)?\s*[-:]", s[m.end():m.end() + 4]))
                    rot = _cues(s[:m.start()]) if titulo else _cues(s)
                    if k == "contraindicacoes" and rot not in ("L", "M"):
                        rot = "L" if re.search(DOSE_CONDICIONAL_V2, s) else "C"
                    exemplos = bool(re.match(r"\s*\(", s[m.end():m.end() + 3]))
                    if herda and not exemplos and PRIOR[_cues(nx)] > PRIOR[rot]:
                        rot = _cues(nx)
                    if transp and PRIOR["L"] > PRIOR[rot]:
                        rot = "L"
                    ev.append(("classe", k, rot, s, nome, False))
            # equivalência: frase que cita o fenofibrato pelo nome vale como citação por classe do ácido fenofíbrico
            if d in EQUIVALENTE and k in ORIENTADORAS:
                eq = EQUIVALENTE[d]
                req = rx_nome(eq, _en(eq))
                for s in fs:
                    if req.search(s) and not _excluido(s, req):
                        rot = _cues(s)
                        if rot in ("C", "L", "M"):
                            ev.append(("classe", k, rot, s, f"fibratos ({d} = {eq})", False))
        if nega_especifica:   # a bula afirma que não há interação relevante com ESTE fármaco: a tabela não impõe limite
            ev = [e if not e[5] else (e[0], e[1], "N", e[3], e[4], e[5]) for e in ev]
            # ... nem a orientação genérica dos transportadores (a própria bula exclui o fármaco do grupo)
            ev = [e if not (e[0] == "classe" and e[4].startswith("inibidores das proteínas transportadoras")) else (e[0], e[1], "N", e[3], e[4], e[5]) for e in ev]
        nom = [e for e in ev if e[0] == "nome"]
        cla = [e for e in ev if e[0] == "classe"]
        if not nom and not cla:
            res[d] = {"citacao": "nao citada", "classe_citada": "", "local": "", "manejo": "nao se aplica", "evidencias": []}
            continue
        ss = {e[1] for e in ev}
        local = "ambas" if "interacoes" in ss and len(ss) > 1 else "secao de interacoes" if "interacoes" in ss else "outra secao"
        top = max(ev, key=lambda e: (PRIOR[e[2]], e[0] == "nome"))
        res[d] = {"citacao": "nominal" if nom else "classe",
                  "classe_citada": "" if nom else max(cla, key=lambda e: PRIOR[e[2]])[4],
                  "local": local, "manejo": MANEJO[top[2]],
                  "evidencias": [(e[0], e[1], e[2], e[3][:600], e[4]) for e in sorted(ev, key=lambda e: -PRIOR[e[2]])]}
    return res


def _en(dcb_pt):
    for en, (pt, _) in DCB.items():
        if pt == dcb_pt:
            return en
    raise KeyError(dcb_pt)


def secoes_do_banco(db):
    """{bula_id: {chave: texto}} com os subtítulos juntados na ordem de inserção."""
    con = sqlite3.connect(db)
    out = {}
    for bid, chave, txt in con.execute("select bula_id, chave, texto from secoes order by bula_id, chave, id"):
        out.setdefault(bid, {}).setdefault(chave, []).append(txt or "")
    return {b: {k: " ".join(v) for k, v in d.items()} for b, d in out.items()}


def classificar(db, bulas, referencia):
    """mesma interface do preclassificar.py v0.1: bulas {bula_id: dict(registro_ms, estatina, ...)}; referencia: linhas do CSV."""
    secs = secoes_do_banco(db)
    linhas = []
    for bid, b in bulas.items():
        ref = [(r["farmaco_dcb"], _en(r["farmaco_dcb"])) for r in referencia if r["estatina"] == b["estatina"]]
        res = classificar_bula(secs.get(bid, {}), ref)
        reg = {r["farmaco_dcb"]: r["registro_ativo_no_brasil"] for r in referencia if r["estatina"] == b["estatina"]}
        for d, _ in ref:
            x = res[d]
            ev = x["evidencias"][0] if x["evidencias"] else None
            linhas.append({**b, "farmaco_dcb": d, "registro_ativo_no_brasil": reg[d], "citacao": x["citacao"], "classe_citada": x["classe_citada"],
                           "local": x["local"], "manejo": x["manejo"], "secoes": ", ".join(sorted({e[1] for e in x["evidencias"]})),
                           "evidencia": f"[{ev[1]}] {ev[3]}" if ev else ""})
    return linhas
