#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""campos.py - campos estruturados de uma bula (registro, via, composição, apresentações, farmacocinética...)."""
import hashlib, os, re, sys, time, unicodedata
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texto as eb  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
LINK = "https://consultas.anvisa.gov.br/#/bulario/q/?expediente={}"


def nn(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", "", s)


def base_nome(arq):
    b = re.sub(r"\.pdf$", "", arq, flags=re.I)
    b = re.sub(r"\s*\[\d{10}\]$", "", b)
    return re.sub(r"\s*\(\d+\)$", "", b).strip()


def registros_do_texto(txt):
    """Numeros de registro MS (9 digitos) citados perto da palavra 'Registro' ou 'MS'.
    Aceita '1.0043.1577', 'Registro 50 mg: 1.0043.1578' e '1.0107.365' (ultimo bloco com 3 digitos)."""
    ls = txt.split("\n")
    achados = set()
    for i, l in enumerate(ls):
        if re.search(r"registro|\bMS\b", l, re.I):
            prox = ls[i + 1] if i + 1 < len(ls) else ""
            for x in re.findall(r"\b(1)\.(\d{4})\.(\d{3,4})\b", l + " " + prox):
                achados.add(x[0] + x[1] + x[2].zfill(4))
    return sorted(achados)


# ---------------- utilidades de texto ----------------
def plano(t):
    return re.sub(r"\s+", " ", t).strip()


def frases(t):
    return [f.strip() for f in re.split(r"(?<=[.;])\s+(?=[A-ZÀ-Ú(])", plano(t)) if f.strip()]


def corta(s, n=420):
    return s if len(s) <= n else s[: n - 1] + "…"


def md5(s):
    return hashlib.md5(plano(s).lower().encode()).hexdigest()[:8]


# ---------------- identificacao ----------------
def head_da_bula(txt, m):
    if m["identificacao"]:
        return m["identificacao"].split("\n")
    ls = txt.split("\n")
    b = next((i for i, l in enumerate(ls) if "INFORMACOES TECNICAS" in eb.norm(l) and "MODELO DE BULA" not in eb.norm(l)), min(len(ls), 150))
    return ls[:b]


def campo_composicao(head):
    a = next((i for i, l in enumerate(head) if eb.norm(l).startswith("COMPOSICAO")), None)
    if a is None:
        return ""
    fim = len(head)
    for i in range(a + 1, len(head)):
        if re.match(r"^(APRESENTACOES?|VIAS? DE ADMINISTRACAO|USO |VIA |INFORMACOES AO PACIENTE)\b", eb.norm(head[i])):
            fim = i
            break
    return plano(" ".join(head[a:fim]))[:1500]


# forma farmaceutica: (nome canonico, regex sobre texto sem acento e minusculo). Ordem = prioridade (mais especifica primeiro).
FORMAS = [
    ("comprimido revestido de liberacao prolongada", r"comprimidos? revestidos? de liberacao (?:prolongada|retardada|modificada|controlada)"),
    ("comprimido de liberacao prolongada", r"comprimidos? de liberacao (?:prolongada|retardada|modificada|controlada)"),
    ("comprimido revestido", r"comprimidos? revestidos?"),
    ("comprimido mastigavel", r"comprimidos? mastigaveis?"),
    ("comprimido orodispersivel", r"comprimidos? orodispersiveis?|\bodt\b"),
    ("comprimido dispersivel", r"comprimidos? dispersiveis?"),
    ("comprimido efervescente", r"comprimidos? efervescentes?"),
    ("comprimido sublingual", r"comprimidos? sublinguais?"),
    ("comprimido", r"comprimidos?"),
    ("capsula gelatinosa mole", r"capsulas? (?:gelatinosas? )?moles?"),
    ("capsula gelatinosa dura", r"capsulas? (?:gelatinosas? )?duras?"),
    ("capsula de liberacao prolongada", r"capsulas? de liberacao (?:prolongada|retardada|modificada)"),
    ("capsula", r"capsulas?"),
    ("dragea", r"drageas?"),
    ("pastilha", r"pastilhas?"),
    ("granulado", r"granulados?"),
    ("po liofilizado para solucao/suspensao injetavel", r"po liofilizado(?: para (?:solucao|suspensao)(?: injetavel| para infusao| oral)?)?"),
    ("po para solucao injetavel", r"po para (?:solucao|suspensao) (?:injetavel|para infusao)"),
    ("po para suspensao oral", r"po para (?:suspensao|solucao) oral"),
    ("solucao injetavel", r"solucao injetavel|solucao para infusao|solucao diluente|solucao para diluicao"),
    ("solucao oral", r"solucao oral"),
    ("solucao nasal", r"solucao nasal"),
    ("solucao oftalmica", r"solucao oftalmica|colirio"),
    ("solucao topica", r"solucao (?:topica|cutanea)"),
    ("suspensao injetavel", r"suspensao injetavel"),
    ("suspensao oral", r"suspensao oral"),
    ("emulsao", r"emulsao"),
    ("xarope", r"xarope"),
    ("gotas", r"gotas"),
    ("elixir", r"elixir"),
    ("creme", r"cremes?"),
    ("pomada", r"pomadas?"),
    ("gel", r"gel|geis"),
    ("locao", r"locao|locoes"),
    ("spray/aerossol", r"sprays?|aerossol|aerossois|inaladores?"),
    ("adesivo transdermico", r"adesivos?|sistemas? transdermicos?"),
    ("supositorio", r"supositorios?"),
    ("ovulo", r"ovulos?"),
    ("implante/sistema intrauterino", r"implantes?|sistemas? intrauterinos?|dispositivos? intrauterinos?"),
    ("anel vaginal", r"aneis? vaginais?|anel vaginal"),
    ("vacina", r"vacinas?"),
    ("injetavel", r"injetavel|injetaveis"),
]
FORMAS_RX = [(nome, re.compile(r"\b(?:" + rx + r")\b")) for nome, rx in FORMAS]
RX_CONC = re.compile(r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|ug|g|mL|ml|UI|U|%|mEq|mmol|MBq|mCi)(?:\s*/\s*(?:mL|ml|g|kg|dose|comprimido|cap|dia|h))?", re.I)
RX_EMB = re.compile(r"((?:cada )?(?:embalagem|embalagens|cartuchos?|caixas?|frascos?|blisteres?|blisters?|ampolas?|envelopes?|bisnagas?|strips?)\b[^.;]*)", re.I)


def formas_farmaceuticas(texto):
    """Formas farmaceuticas citadas, na ordem em que aparecem (cada trecho conta uma vez)."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    achados = []
    for nome, rx in FORMAS_RX:
        for m in list(rx.finditer(t)):
            achados.append((m.start(), nome))
            t = t[: m.start()] + " " * (m.end() - m.start()) + t[m.end():]  # evita contar 'comprimido' dentro de 'comprimido revestido'
    achados.sort()
    return list(dict.fromkeys(n for _, n in achados))


def campo_apresentacoes(head):
    """Bloco 'APRESENTACAO(OES)' como escrito + itens (forma, concentracoes, embalagem) + forma da capa."""
    a = next((i for i, l in enumerate(head) if re.match(r"^APRESENTAC(AO|OES)\b", eb.norm(l))), None)
    capa = [l.strip() for l in head if l.strip()][:8]
    forma_capa = formas_farmaceuticas(" ".join(capa))
    if a is None:
        return {"texto": "", "itens": [], "forma_farmaceutica": forma_capa, "forma_na_capa": forma_capa, "fonte_forma": "capa" if forma_capa else ""}
    fim = len(head)
    for i in range(a + 1, len(head)):
        if re.match(r"^(VIAS? DE ADMINISTRACAO|USO |VIA |COMPOSICAO|INFORMACOES AO PACIENTE)", eb.norm(head[i])):
            fim = i
            break
    bloco = [head[a].strip()] + [l for l in head[a + 1:fim]]
    texto = plano(" ".join(bloco))
    corpo = re.sub(r"^APRESENTA[CÇ][AÃ]O|^APRESENTA[CÇ][OÕ]ES", "", texto, flags=re.I).lstrip(" :-")
    partes = [p.strip(" -–") for p in re.split(r"\s*[•·▪]\s*|(?<=\.)\s+(?=[A-ZÀ-Ú])|\s;\s", corpo) if p.strip(" -–")]
    itens = []
    for p in partes:
        if itens and re.match(r"^(embalagem|embalagens|cada embalagem|cartucho|caixa|frasco|blister)", unicodedata.normalize("NFKD", p).encode("ascii", "ignore").decode().lower()):
            itens[-1]["texto"] += " " + p
        else:
            itens.append({"texto": p})
    def preenche(it):
        sem_emb = RX_EMB.sub(" ", it["texto"])  # "10 cápsulas" da embalagem nao e forma farmaceutica
        it["formas"] = formas_farmaceuticas(sem_emb)
        it["concentracoes"] = list(dict.fromkeys(re.sub(r"\s+", "", c) for c in RX_CONC.findall(it["texto"])))[:8]
        e = RX_EMB.search(it["texto"])
        it["embalagem"] = plano(e.group(1)) if e else ""
    for it in itens:
        preenche(it)
    fundidos = []
    for it in itens:
        if fundidos and not it["formas"]:  # trecho so de embalagem/complemento: pertence ao item anterior
            fundidos[-1]["texto"] += " " + it["texto"]
            preenche(fundidos[-1])
        else:
            fundidos.append(it)
    itens = fundidos
    formas = list(dict.fromkeys(f for it in itens for f in it["formas"])) or formas_farmaceuticas(RX_EMB.sub(" ", corpo))
    fonte = "apresentacoes" if formas else ("capa" if forma_capa else "")
    if not formas:
        formas = forma_capa
    return {"texto": texto[:1500], "itens": itens[:12], "forma_farmaceutica": formas, "forma_na_capa": forma_capa,
            "fonte_forma": fonte}


def campo_via_uso(head):
    """Via de administracao e populacao de uso, como escritas na bula (sem inferir nada)."""
    vias, pop = [], []
    for l in head:
        s = plano(l)
        n = eb.norm(s)
        if re.match(r"^VIAS? DE ADMINISTRACAO\b", n):
            vias.append(s.split(":", 1)[1].strip() if ":" in s else s)
        elif re.match(r"^(USO|VIA)\b", n):
            (pop if re.search(r"ADULTO|PEDIATRIC|INFANTIL|GERIATR|IDOSO", n) else vias).append(s)
    uniq = lambda xs: list(dict.fromkeys(xs))[:6]
    return {"via_administracao": uniq(vias), "uso_populacao": uniq(pop)}


# ---------------- secao 3: farmacodinamica x farmacocinetica ----------------
RX_PD = re.compile(r"^(PROPRIEDADES )?FARMACODINAMIC[AO]S?$")
RX_PK = re.compile(r"^(PROPRIEDADES )?FARMACOCINETIC[AO]S?$")
RX_SEG = re.compile(r"^(DADOS DE SEGURANCA|SEGURANCA (PRE ?CLINICA|NAO CLINICA)|TOXICIDADE|TOXICOLOGIA|CARCINOGENESE|GENOTOXICIDADE|"
                    r"FARMACOLOGIA DE SEGURANCA|FERTILIDADE E GRAVIDEZ|EMBRIOTOXICIDADE)")
RX_MEC = re.compile(r"^MECANISMOS? DE ACAO")
RX_PD_SUB = re.compile(r"^(EFEITOS? FARMACODINAMIC|ELETROFISIOLOGIA|EFEITO NO INTERVALO|ATIVIDADE (ANTI|ANTIVIRAL)|POLISSONOGRAFIA)")
SUB_PK = [
    ("absorcao", re.compile(r"^(ABSORCAO|BIODISPONIBILIDADE)")),
    ("distribuicao", re.compile(r"^DISTRIBUICAO")),
    ("metabolismo", re.compile(r"^(METABOLISMO|BIOTRANSFORMACAO)")),
    ("eliminacao", re.compile(r"^(ELIMINACAO|EXCRECAO)")),
    ("linearidade", re.compile(r"^LINEARIDADE")),
    ("populacoes_especiais", re.compile(r"^(POPULACOES? ESPECIAIS|INFORMACOES ADICIONAIS PARA POPULACOES|INSUFICIENCIA (RENAL|HEPATICA)|"
                                       r"PACIENTES (IDOSOS|COM INSUFICIENCIA|PEDIATRICOS|GERIATRICOS)|IDOSOS|CRIANCAS|POPULACAO PEDIATRICA|"
                                       r"SEXO|RACA|GENERO|PESO CORPOREO|TABAGISMO|FARMACOGENOMICA|OUTRAS CARACTERISTICAS)")),
]


def titulo_limpo(l):
    s = l.strip()
    if not (2 < len(s) <= 80) or s.endswith((".", ";", ",")):
        return ""
    s = re.sub(r"^[\-•–·\s]+", "", s)
    s = re.sub(r"^\d+(\.\d+)*\s+", "", s)
    return eb.norm(s).rstrip(": ").strip()


def segmenta_secao3(s3):
    """Divide a secao 3 em farmacodinamica / farmacocinetica / seguranca nao clinica, por titulos conhecidos."""
    blocos = []  # (top, sub, [linhas])
    top, sub, atual = "pd", "intro", []
    achou = {"pd": False, "pk": False, "seg": False}
    blocos_aberto = [top, sub, atual]
    def abrir(t, s):
        nonlocal blocos_aberto
        if blocos_aberto[2]:
            blocos.append(tuple(blocos_aberto))
        blocos_aberto = [t, s, []]
    for l in s3.split("\n"):
        h = titulo_limpo(l)
        t, s = blocos_aberto[0], blocos_aberto[1]
        if h:
            if RX_SEG.match(h) and t != "seg":
                achou["seg"] = True
                abrir("seg", "geral")
                continue
            if RX_PK.match(h):
                achou["pk"] = True
                abrir("pk", "geral")
                continue
            if RX_PD.match(h):
                achou["pd"] = True
                abrir("pd", "geral")
                continue
            if t != "seg":
                nomeado = next((k for k, rx in SUB_PK if rx.match(h)), None)
                if nomeado:
                    if t != "pk":
                        achou["pk"] = True
                    abrir("pk", nomeado)
                    continue
                if RX_MEC.match(h):
                    achou["pd"] = True
                    abrir("pd", "mecanismo")
                    continue
                if t == "pd" and RX_PD_SUB.match(h):
                    abrir("pd", "efeitos")
                    continue
        blocos_aberto[2].append(l)
    if blocos_aberto[2]:
        blocos.append(tuple(blocos_aberto))
    pd, pk, seg = defaultdict(list), defaultdict(list), []
    for t, s, ls in blocos:
        tx = plano(" ".join(ls))
        if not tx:
            continue
        if t == "pd":
            pd[s].append(tx)
        elif t == "pk":
            pk[s].append(tx)
        else:
            seg.append(tx)
    pd = {k: " ".join(v) for k, v in pd.items()}
    pk = {k: " ".join(v) for k, v in pk.items()}
    return pd, pk, " ".join(seg), achou


UN = r"(?:%|horas?|h\b|minutos?|min\b|dias?|semanas?|L/h|L/kg|L\b|mL/min(?:/kg)?|ng/mL|µg/mL|mcg/mL|mg/L|ng·h/mL|µg·h/mL|mcg·h/mL)"
RX_VAL = re.compile(r"(\d+(?:[.,]\d+)?(?:\s*(?:a|–|-|e|ou)\s*\d+(?:[.,]\d+)?)?)\s*(" + UN + ")", re.I)
CHAVES_PK = {
    "tmax": r"\bT\s?m[aá]x\b|tempo (?:para|at[eé]) (?:atingir|alcan[cç]ar)|tempo m[eé]dio para",
    "cmax": r"\bC\s?m[aá]x\b|concentra[cç][aã]o (?:plasm[aá]tica |s[eé]rica )?m[aá]xima",
    "biodisponibilidade": r"biodisponibilidade",
    "volume_distribuicao": r"volume de distribui[cç][aã]o|\bV(?:d|ss|z)(?:/F)?\b",
    "clearance": r"clearance|depura[cç][aã]o|\bCL/F\b|\bCLT\b",
    "meia_vida": r"meia[- ]vida|\bt\s?1/2\b|t½",
    "excrecao": r"excret|recuperad|urina|fezes",
}


def valores_pk(texto):
    out = {}
    fr = frases(texto)
    for chave, rx in CHAVES_PK.items():
        achados = []
        for f in fr:
            if re.search(rx, f, re.I):
                vals = [" ".join(v) for v in RX_VAL.findall(f)]
                if vals:
                    achados.append({"trecho": corta(f), "valores": vals[:8]})
        out[chave] = achados[:4]
    lig = []
    for f in fr:
        if re.search(r"prote[ií]nas?|albumina", f, re.I) and re.search(r"liga", f, re.I) and "%" in f:
            lig.append({"trecho": corta(f), "valores": re.findall(r"(\d+(?:[.,]\d+)?(?:\s*(?:a|–|-)\s*\d+(?:[.,]\d+)?)?)\s*%", f)[:6]})
    out["ligacao_proteica"] = lig[:3]
    return out


RX_ENZ = r"\b(?:CYP\s?\d[A-Z]\d{1,2}|UGT\s?\d[A-Z]\d{1,2})\b"


def enzimas(texto):
    """'Citada' NAO e 'substrato' (pode ser inibicao/inducao): revisar pelo trecho. Frases negadas ficam separadas."""
    cit, neg, tr = set(), set(), []
    for f in frases(texto):
        if re.search(r"metaboli|CYP|UGT|biotransforma", f, re.I):
            tr.append(corta(f))
            achadas = {e.replace(" ", "") for e in re.findall(RX_ENZ, f)}
            if re.search(r"\bn[aã]o\b|nenhum|sem efeito", f, re.I):
                neg |= achadas
            else:
                cit |= achadas
    return {"enzimas_citadas": sorted(cit)[:20], "enzimas_em_frase_negada": sorted(neg - cit)[:20], "trechos": tr[:3]}


def campo_armazenamento(sec7, head):
    t = plano(sec7 or "")
    grau = "[°º\uf0b0]?"  # \uf0b0 = simbolo de grau da fonte Symbol
    temp = re.findall(r"(\d{1,2})\s*" + grau + r"\s*C?\s*(?:a|e|–|-)\s*(\d{1,2})\s*" + grau + r"\s*C\b", t)
    val = []
    for f in frases(t + " " + plano(" ".join(head))):
        if re.search(r"validade|prazo|utilizado por|data de fabrica", f, re.I):
            val += re.findall(r"(\d{1,3})\s*(meses|mes|dias|anos)", f, re.I)
    return {"temperatura_c": [f"{a}-{b}" for a, b in temp][:3],
            "menciona_refrigeracao": bool(re.search(r"geladeira|refrigerad", t, re.I)),
            "validade": sorted({f"{n} {u.lower()}" for n, u in val})[:3], "trecho": corta(t, 500)}


# ---------------- extracao de um PDF ----------------
def extrair_um(pdf):
    arq = os.path.basename(pdf)
    t0 = time.time()
    pages, motor = eb.pdf_para_paginas(pdf)
    bruto = sum(len(p) for p in pages)
    txt, hist, _ = eb.limpar(pages)
    secoes, ocorr, _ = eb.separar_secoes(txt)
    m = eb.meta(txt, arq)
    regs_pdf = registros_do_texto(txt)
    exp, cands, met = "", [], "nao_resolvido"  # o expediente não está no texto da bula; a identificação é pelo registro MS
    head = head_da_bula(txt, m)
    s3 = secoes.get("caracteristicas_farmacologicas", "")
    pd, pk, seg, achou = segmenta_secao3(s3)
    pd_texto = " ".join(pd.values())
    pk_texto = " ".join(pk.values())
    mec = pd.get("mecanismo", "")
    mec_metodo = "subtitulo" if mec else ""
    if not mec and pd_texto:
        mec, mec_metodo = pd.get("geral", "") or pd.get("intro", "") or pd_texto, "inicio_da_farmacodinamica (revisar)"
    campos = {
        "nome": m["nome_capa"], "registro": regs_pdf or ([m["registro"]] if m["registro"] else []),
        "empresa": m["empresa"], "aprovada_anvisa": m["aprovada_anvisa"],
        **campo_via_uso(head),
        "composicao": campo_composicao(head), "apresentacoes": campo_apresentacoes(head),
        "indicacoes": plano(secoes.get("indicacoes", "")),
        "farmacodinamica": {"titulo_encontrado": achou["pd"], "texto": pd_texto[:15000], "mecanismo_de_acao": mec[:3000],
                            "mecanismo_metodo": mec_metodo, "efeitos_farmacodinamicos": pd.get("efeitos", "")[:5000]},
        "farmacocinetica": {"titulo_encontrado": achou["pk"], "texto": pk_texto[:20000],
                            "subsecoes": {k: v[:6000] for k, v in pk.items()},
                            "valores": valores_pk(pk_texto or s3), "metabolismo_enzimas": enzimas(pk_texto or s3)},
        "seguranca_nao_clinica": seg[:6000],
        "armazenamento": campo_armazenamento(secoes.get("armazenamento", ""), head),
    }
    problemas = []
    if bruto < 500 * max(1, len(pages)) * 0.2:
        problemas.append("POUCO_TEXTO (possivel escaneado)")
    if "\ufffd" in txt:
        problemas.append("caracteres_invalidos")
    if not regs_pdf:
        problemas.append("sem_registro_lido")
    falt = [k for k in eb.ESPERADAS if len(secoes.get(k, "")) < 15]
    if len(falt) >= 3:
        problemas.append("secoes_faltando: " + ",".join(falt))
    if not s3:
        problemas.append("sem_secao_3 (caracteristicas farmacologicas)")
    else:
        if not pd_texto:
            problemas.append("farmacodinamica_vazia")
        if not pk_texto:
            problemas.append("farmacocinetica_vazia")
    if not campos["composicao"]:
        problemas.append("sem_composicao")
    if not campos["via_administracao"]:
        problemas.append("sem_via_administracao")
    if not campos["apresentacoes"]["forma_farmaceutica"]:
        problemas.append("sem_forma_farmaceutica")
    if not campos["apresentacoes"]["itens"]:
        problemas.append("sem_apresentacoes")
    if not campos["indicacoes"]:
        problemas.append("sem_indicacoes")
    return {
        "arquivo": arq, "expediente": exp, "expediente_metodo": met, "expediente_candidatos": cands,
        "fonte_link": LINK.format(exp) if exp else "", "fontes_candidatas": [LINK.format(e) for e in cands] if not exp else [],
        "paginas": len(pages), "motor": motor, "secoes_encontradas": sorted(secoes),
        "hash_texto": md5(txt), "hash_secoes": {k: md5(v) for k, v in secoes.items()},
        "campos": campos, "problemas": problemas, "segundos": round(time.time() - t0, 2),
    }
