#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""completo.py - extração completa de uma bula: seções inteiras, subtítulos (negrito), composição, alertas e índice clínico."""
import os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texto as eb       # noqa: E402
import campos as ec      # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))

NOMES_SECAO = {
    "indicacoes": "1. Indicações", "resultados_eficacia": "2. Resultados de eficácia",
    "caracteristicas_farmacologicas": "3. Características farmacológicas", "contraindicacoes": "4. Contraindicações",
    "advertencias_precaucoes": "5. Advertências e precauções", "interacoes": "6. Interações medicamentosas",
    "armazenamento": "7. Cuidados de armazenamento", "posologia": "8. Posologia e modo de usar",
    "reacoes_adversas": "9. Reações adversas", "superdose": "10. Superdose", "dizeres_legais": "III. Dizeres legais",
}


# ---------------- subtitulos pelo negrito do PDF ----------------
def linhas_em_negrito(pdf):
    """Conjunto de linhas (normalizadas) que estao TODAS em negrito no PDF = subtitulos."""
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    neg = set()
    try:
        doc = pymupdf.open(pdf)
        for pg in doc:
            for b in pg.get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    spans = [s for s in ln["spans"] if s["text"].strip()]
                    if not spans:
                        continue
                    todos = all((s["flags"] & 16) or re.search(r"bold|black|heavy|semibold|demi", s["font"], re.I) for s in spans)
                    if todos:
                        t = re.sub(r"\s+", " ", "".join(s["text"] for s in spans)).strip(" :-–•·")
                        if 3 <= len(t) <= 110:
                            neg.add(eb.norm(t))
    except Exception:
        pass
    return neg


def divide_subtitulos(texto, negritos):
    """Divide o texto de uma secao em [{titulo, texto}] usando os subtitulos em negrito. Nao perde nenhuma linha."""
    blocos, titulo, buf = [], "", []
    for l in texto.split("\n"):
        s = re.sub(r"^[\-•–·\s]+", "", l.strip()).rstrip(": ").strip()
        ehtit = bool(s) and len(s) <= 110 and eb.norm(s) in negritos and not s.endswith(".")
        if ehtit:
            if "".join(buf).strip() or titulo:
                blocos.append({"titulo": titulo, "texto": "\n".join(buf).strip()})
            titulo, buf = s, []
        else:
            buf.append(l)
    if "".join(buf).strip() or titulo:
        blocos.append({"titulo": titulo, "texto": "\n".join(buf).strip()})
    return blocos


# ---------------- composicao: ativos e excipientes ----------------
RX_LIDER = re.compile(r"^(?P<nome>.+?)\s*[.…·]{2,}\s*(?P<qtd>[\d.,]+\s*[A-Za-zµ%/ ]{1,14}.*)$")
RX_TAB = re.compile(r"^(?P<nome>(?:\d+\s*mM\s+)?\d?[A-Za-zÀ-ú][^\n]{2,80}?)\s{2,}(?P<qtd>\d[\d.,]*\s*(?:mg|mcg|µg|g|mL|ml|UI|U)\b.*)$")
UNID_Q = r"(?:mg|mcg|µg|ug|g|mL|ml|UI|U|%|mEq|mmol|MBq|mCi)(?:/(?:mL|ml|g|L|dose))?"
NUM_Q = r"\d[\d.,]*"
RX_PAR = re.compile(
    r"(?P<qtd>" + NUM_Q + r"(?:\s*" + UNID_Q + r"\b(?:\s*\([^)]{1,40}\))?)?(?:\s*(?:,|ou|e|a)\s*" + NUM_Q + r"(?:\s*" + UNID_Q + r"\b(?:\s*\([^)]{1,40}\))?)?)*)\s*(?:de|do|da)\s+"
    r"(?P<nome>.+?)(?=,\s+\d|\s+e\s+\d|;|\.\s|\.$|$)", re.I)


def ativos_inline(texto):
    """'contem 100 mg de A, 50 mg de B e 75 mg de C' -> [{nome, quantidade}]."""
    t = re.sub(r"\s+", " ", texto).strip()
    out = []
    for m in RX_PAR.finditer(t):
        nome = re.split(r",?\s+em\s+(?:solu|ve[ií]c|base|[aá]lcool|excip)", m.group("nome"), maxsplit=1, flags=re.I)[0].strip(" .:")
        if not nome or re.match(r"^cada\b", nome, re.I) or not re.search(UNID_Q, m.group("qtd"), re.I):
            continue
        eq = ""
        mm = re.search(r"\s+equivalente[s]?\s+a\s+(.*)$", nome, re.I)
        if mm:
            eq, nome = mm.group(1).strip(), nome[: mm.start()].strip()
        out.append({"nome": nome, "quantidade": m.group("qtd").strip(), "equivalente_a": eq, "texto": m.group(0).strip()})
    return out


def limpa_nome(n):
    n = re.sub(r"^princ[ií]pios?\s+ativos?\s*:\s*", "", n.strip(), flags=re.I)
    n = re.sub(r"^[•·▪]\s*|^o\s+(?=[A-ZÀ-Ú])|^-\s+", "", n.strip())
    return re.sub(r"^\d(?=[A-Za-zÀ-ú])", "", n).strip(" :*")


def separa_lista(s):
    """Separa 'a, b (c, d), e e f' respeitando parenteses. So o ULTIMO item e dividido por ' e ' (evita partir
    'acetato e succinato de hipromelose')."""
    itens, nivel, atual = [], 0, ""
    for ch in s:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel = max(0, nivel - 1)
        if ch in ",;" and nivel == 0:
            itens.append(atual)
            atual = ""
        else:
            atual += ch
    itens.append(atual)
    itens = [i.strip() for i in itens if i.strip()]
    if itens and "(" not in itens[-1]:
        ult = re.split(r"\s+e\s+(?=[a-zà-ú])", itens[-1])
        if len(ult) == 2 and len(ult[0].split()) <= 6:
            itens = itens[:-1] + ult
    out = []
    for sub in itens:
        sub = sub.strip(" .*")
        if sub and not re.search(r"[A-Za-z]+_[A-Za-z0-9_]+", sub):  # descarta rodape de PDF que vazou (ex.: LLD_Bra_CDSv3.0...)
            out.append(sub)
    return out


def excipientes_de_paragrafos(texto):
    """Texto apos 'Excipientes:' (pode ter varios paragrafos 'Rotulo: lista.') -> (lista, por_grupo, observacoes)."""
    por_grupo, obs, todos = {}, [], []
    for par in re.split(r"\n\s*\n", texto.strip()):
        par = re.sub(r"\s+", " ", par).strip()
        par = re.sub(r"\s*[.…·]{3,}[^;]*?(?=,\s*[A-Za-zÀ-ú]|;|$)", "", par).strip()
        par = re.split(r"\.\s+(?=Cada\b|Este\b|Esta\b|Ver\b|Veja\b)", par)[0].strip()
        if re.match(r"^(cada|este|esta|ver|veja)\b", par, re.I):
            obs.append(par)
            continue
        if not par:
            continue
        m = re.match(r"^(?P<rot>[^:]{1,70}):\s*(?P<lista>.+)$", par)
        if m and re.match(r"^(aten[cç][aã]o|observa[cç][aã]o|nota|advert[eê]ncia|cuidado)", m.group("rot"), re.I):
            obs.append(par)
            continue
        rot, lista = (m.group("rot"), m.group("lista")) if m else ("", par)
        itens = separa_lista(lista)
        if rot:
            por_grupo[rot] = itens
        todos += itens
    return list(dict.fromkeys(todos)), por_grupo, obs


RX_FORCA = re.compile(r"^\d[\d.,/ ]*\s*(?:mg|mcg|µg|g|mL|UI)\s*(?:[+/][^:]*)?:\s*$", re.I)  # titulo de sub-bloco: '20 mg:'
RX_EXC_NOME = re.compile(r"\b(adjuvantes?|conservantes?)\b|fenoxietanol|^[aá]gua\b|^ve[ií]culo\b", re.I)
RX_EXC_VAC = re.compile(r"^(?:\d+\s*mM\s+)?(?:acetato de s[oó]dio|cloreto de s[oó]dio|sacarose|trometamol|polissorbato)", re.I)
RX_ANTIGENO = re.compile(r"polissacar|toxoide|ant[ií]geno|vacina|v[ií]rus", re.I)


def reclassifica_blocos(blocos):
    """Move para excipientes itens que vieram no meio dos ativos (adjuvante, conservante, agua, veiculo; em vacinas tambem sais/sacarose).
    So age quando sobra ao menos um ativo no bloco."""
    for b in blocos:
        ativos = b["ativos"]
        vac = any(RX_ANTIGENO.search(a["nome"]) for a in ativos)
        mover = [a for a in ativos if not a["nome"].startswith("(") and (RX_EXC_NOME.search(a["nome"]) or (vac and RX_EXC_VAC.search(a["nome"])))]
        if not mover or len(mover) >= len([a for a in ativos if not a["nome"].startswith("(")]):
            continue
        for a in mover:
            ativos.remove(a)
            if not re.match(r"^ve[ií]culo\b", a["nome"], re.I):
                b["excipientes"].append(a["nome"])


def composicao_estruturada(head):
    """Composicao em blocos (por apresentacao/sabor): ativos com quantidade e excipientes. Texto original sempre preservado."""
    a = next((i for i, l in enumerate(head) if eb.norm(l).startswith("COMPOSIC")), None)
    vazio = {"texto_original": "", "blocos": [], "ativos_todos": [], "excipientes_todos": [], "observacoes": [], "revisar": True}
    if a is None:
        return vazio
    fim = len(head)
    for i in range(a + 1, len(head)):
        nl = eb.norm(head[i])
        if re.match(r"^(APRESENTAC(AO|OES)|VIAS? DE ADMINISTRACAO|USO |VIA |INFORMACOES AO PACIENTE)\b", nl):
            if re.match(r"^APRESENTAC(AO|OES)\b", nl) and re.search(r"\d", nl):
                continue  # linha de tabela ('Apresentacao de 50 ml', 'Apresentacao 20 mg 40 mg'), nao o titulo
            fim = i
            break
    linhas = [l.rstrip() for l in head[a + 1:fim]]
    texto = "\n".join(head[a:fim]).strip()
    blocos, atual, modo, buf_exc = [], None, "ativos", []
    obs_geral = []

    def novo(titulo):
        nonlocal atual
        fechar()
        atual = {"titulo": titulo, "ativos": [], "excipientes": [], "excipientes_por_grupo": {}, "texto": ""}
        blocos.append(atual)

    def fechar():
        nonlocal buf_exc
        if atual is not None and buf_exc:
            exc, grp, obs = excipientes_de_paragrafos("\n".join(buf_exc))
            atual["excipientes"] += exc
            atual["excipientes_por_grupo"].update(grp)
            obs_geral.extend(obs)
        buf_exc = []

    i = 0
    while i < len(linhas):
        l = re.sub(r"^-\s+(?=[A-Za-zÀ-ú])", "", linhas[i].strip())
        if modo == "exc":
            prox_nb = next((x.strip() for x in linhas[i + 1:] if x.strip()), "")
            if (re.search(r"\bcont[eéê]m\b", l, re.I) and not re.match(r"^\*{0,3}\s*excipientes?", l, re.I)) \
                    or re.match(r"^(esta vacina|este medicamento|esta composi|princ[ií]pios? ativos?\b|subst[aâ]ncias? ativas?\b)", l, re.I) \
                    or (l.endswith(":") and (re.search(r"\bcont[eéê]m\b", prox_nb, re.I) or RX_LIDER.match(prox_nb) or RX_TAB.match(prox_nb))):
                modo = "ativos"
            else:
                buf_exc.append(linhas[i])
                i += 1
                continue
        if not l:
            i += 1
            continue
        if re.match(r"^(aten[cç][aã]o|observa[cç][aã]o|nota)\s*:", l, re.I):
            obs_geral.append(l)
            i += 1
            continue
        m_lider = RX_LIDER.match(l)
        if m_lider and re.match(r"^\*{0,3}\s*(?:excipientes?|outros componentes)", m_lider.group("nome"), re.I):
            if atual is None:
                novo("")
            atual["ativos"].append({"nome": "(excipientes q.s.p.)", "quantidade": re.sub(r"\s+", " ", m_lider.group("qtd")).strip(), "equivalente_a": "", "texto": l})
            i += 1
            k = i
            while k < len(linhas) and not linhas[k].strip():
                k += 1
            if k < len(linhas) and linhas[k].strip().startswith("("):
                inner, k2 = linhas[k].strip(), k + 1
                while ")" not in inner and k2 < len(linhas) and linhas[k2].strip():
                    inner += " " + linhas[k2].strip()
                    k2 += 1
                atual["excipientes"] += separa_lista(inner.strip("() ."))
                i = k2
            elif k < len(linhas) and linhas[k].strip().startswith("*") and not re.match(r"^\*+\s*(?:excipientes?|outros componentes)", linhas[k].strip(), re.I) and not re.search(r"\b(é|foi|são|composto|cont[eéê]m)\b", linhas[k][:120], re.I):
                inner, k2 = linhas[k].strip(), k + 1
                while k2 < len(linhas) and linhas[k2].strip():
                    inner += " " + linhas[k2].strip()
                    k2 += 1
                atual["excipientes"] += separa_lista(inner.strip("* ."))
                i = k2
            continue
        if re.match(r"^\*{0,3}\s*(?:excipientes?|outros componentes)\b", l, re.I):
            if atual is None:
                novo("")
            resto = re.sub(r"^\*{0,3}\s*(?:excipientes?|outros componentes)\s*\**\s*:?\s*", "", l, flags=re.I)
            buf_exc = [resto] if resto else []
            modo = "exc"
            i += 1
            continue
        if RX_FORCA.match(l):
            novo(l.strip(" :"))
            i += 1
            continue
        m_pa = re.match(r"^princ[ií]pios?\s+ativos?\s*:\s*(?P<n>.+?)\s*$", l, re.I)
        if m_pa and not m_lider and not re.search(r"cont[eéê]m|^cada\b", m_pa.group("n"), re.I):
            if atual is None:
                novo("")
            nome_pa = re.sub(r"\s*[.…·]{2,}.*$", "", m_pa.group("n")).strip()
            qtd_pa, k = "", i + 1
            while k < len(linhas) and not linhas[k].strip():
                k += 1
            if k < len(linhas) and re.match(r"^\d", linhas[k].strip()):
                qtd_pa, i = re.sub(r"\s+", " ", linhas[k].strip()), k
            atual["ativos"].append({"nome": nome_pa, "quantidade": qtd_pa, "equivalente_a": "", "texto": l})
            i += 1
            continue
        m_tab = RX_TAB.match(l)
        if re.match(r"^apresenta[cç][aã]o\b", l, re.I) and re.search(r"\d", l) and not re.search(r"\bcont[eé]m\b", l, re.I):
            if not m_tab:
                novo(re.sub(r"\s+", " ", l).strip(" :"))
            i += 1
            continue
        m_agua = re.match(r"^(?P<nome>[aá]gua[^\d.]{0,40}?)\s+q\.?s\.?p\.?\b", l, re.I)
        if m_agua and atual is not None:
            atual["excipientes"].append(m_agua.group("nome").strip(" :*"))
            i += 1
            continue
        if m_tab and atual is not None and re.match(r"^[aá]gua\b", m_tab.group("nome").strip(), re.I) and "contém" not in l:
            atual["excipientes"].append(re.sub(r"\s+q\.?s\.?p\.?.*$", "", m_tab.group("nome").strip(" :*"), flags=re.I))
            i += 1
            continue
        if m_tab and not m_lider and atual is not None and not re.match(r"^(apresenta|volume|substancia seca|q\.?s\.?p|[aá]gua)", eb.norm(m_tab.group("nome")), re.I | re.S) and "contém" not in l:
            atual["ativos"].append({"nome": limpa_nome(m_tab.group("nome")), "quantidade": re.sub(r"\s+", " ", m_tab.group("qtd")).strip(), "equivalente_a": "", "texto": l})
            i += 1
            continue
        if re.search(r"\bcont[eéê]m\b", l, re.I) and not m_lider and not l.startswith("(") and not re.search(r"\bn[aã]o\s+cont[eéê]m\b", l, re.I):
            j, junto = i + 1, l
            while not junto.rstrip().endswith((".", ":")) and j < len(linhas):
                if not linhas[j].strip():
                    if junto.count("(") > junto.count(")") or re.search(r"\b(equivalentes?|a|de|e|ou)$", junto.rstrip()):
                        j += 1
                        continue
                    break
                junto += " " + linhas[j].strip()
                j += 1
            novo(re.sub(r"\s+", " ", l.split("cont", 1)[0] + "contém").strip(" :-"))
            apos = re.split(r"cont[eéê]m", junto, maxsplit=1)[-1]
            ativos_b = ativos_inline(apos)
            prox = next((x.strip() for x in linhas[j:] if x.strip()), "")
            if not ativos_b and (RX_FORCA.match(prox) or RX_LIDER.match(prox) or RX_TAB.match(prox) or re.match(r"^apresenta[cç][aã]o\b", prox, re.I)):
                atual["texto"] = junto
                i = j
                continue
            if not ativos_b:
                # formato descritivo (soros, imunoglobulinas, vacinas): o que vem depois de 'contem' ate 'Excipiente' e' o ativo
                if apos.strip(" :"):
                    desc = [apos.strip(" :")]
                else:
                    desc, k = [], j
                    while k < len(linhas) and not linhas[k].strip():
                        k += 1
                    bullets = k < len(linhas) and linhas[k].strip().startswith("-")
                    while k < len(linhas) and not re.match(r"^\*?\s*(excipientes?|q\.?s\.?p)", linhas[k].strip(), re.I) and not re.search(r"\bcont[eé]m\b", linhas[k], re.I):
                        t = linhas[k].strip()
                        if not t:
                            if not bullets:
                                break
                            k += 1
                            continue
                        if bullets and not t.startswith("-") and desc and not desc[-1].rstrip().endswith((";", ".")):
                            desc[-1] += " " + t
                        elif bullets and not t.startswith("-"):
                            break
                        else:
                            desc.append(t)
                        k += 1
                    j = k
                for n_d, d in enumerate(desc):
                    if n_d > 0 and d.lstrip().startswith("-"):
                        atual["excipientes"].append(re.sub(r"\s{2,}.*$", "", re.sub(r"^[-•*\s]+", "", d)).strip(" ;.:"))
                        continue
                    ml = RX_LIDER.match(d)
                    nome_d, qtd_d = (ml.group("nome"), re.sub(r"\s+", " ", ml.group("qtd")).strip()) if ml else (d, "")
                    nome_d = re.sub(r"^[-•*\s]+", "", nome_d).strip(" .:")
                    if nome_d and not re.match(r"^(excipientes?|[aá]gua)\b", nome_d, re.I):
                        ativos_b.append({"nome": nome_d[:200], "quantidade": qtd_d, "equivalente_a": "", "texto": d, "descritivo": True})
            atual["ativos"] += ativos_b
            m_em = re.search(r"\bem\s+(?:solu[cç][aã]o|ve[ií]culo|base|[aá]lcool|excipiente)[^()]{0,60}\(([^)]{5,300})\)", junto, re.I)
            if m_em:
                it_em = separa_lista(m_em.group(1))
                if len(it_em) >= 2:
                    atual["excipientes"] += it_em
            atual["texto"] = junto
            i = j
            continue
        if m_lider:
            if atual is None:
                novo("")
            atual["ativos"].append({"nome": limpa_nome(m_lider.group("nome")), "quantidade": re.sub(r"\s+", " ", m_lider.group("qtd")).strip(), "equivalente_a": "", "texto": l})
            i += 1
            continue
        if atual is None:
            novo("")
        atual["texto"] = (atual["texto"] + " " + l).strip()
        i += 1
    fechar()
    reclassifica_blocos(blocos)
    # blocos de titulo ('TRIKAFTA (comprimido ...)') sem ativos nem excipientes ficam so como texto
    ativos = list(dict.fromkeys(a["nome"] for b in blocos for a in b["ativos"] if not a["nome"].startswith("(")))
    exc = list(dict.fromkeys(e for b in blocos for e in b["excipientes"]))
    revisar = not ativos or (not exc and "excipiente" in texto.lower())
    return {"texto_original": texto, "blocos": blocos, "ativos_todos": ativos, "excipientes_todos": exc,
            "observacoes": obs_geral, "revisar": revisar}


# alertas por palavra-chave (para conferir intolerancias/alergias): (grupo, regex sobre texto minusculo sem acento)
ALERTAS = [
    ("lactose", r"lactose"), ("sacarose/acucar", r"sacarose|acucar|glicose|frutose"), ("sorbitol/manitol/polioois", r"sorbitol|manitol|xilitol|maltitol"),
    ("gluten/trigo", r"gluten|amido de trigo|trigo"), ("fenilalanina (aspartame)", r"aspartame|fenilalanina"),
    ("corante azo (tartrazina etc.)", r"tartrazina|amarelo crepusculo|amarelo (?:n[o.]?\s*)?(?:5|6)|ponceau|vermelho 40|vermelho allura|azorrubina|carmoisina"),
    ("corantes (outros)", r"corante|dioxido de titanio|oxido de ferro|azul brilhante|indigotina"),
    ("parabenos", r"parabeno|metilparabeno|propilparabeno|nipagin|nipazol"), ("benzoato/acido benzoico", r"benzoato|acido benzoico"),
    ("sulfitos", r"sulfito|metabissulfito|bissulfito|metabissulfito"), ("alcool", r"alcool|etanol|etilico"),
    ("propilenoglicol", r"propilenoglicol|propileno glicol"), ("soja/amendoim", r"soja|amendoim|lecitina"),
    ("gelatina (origem animal)", r"gelatina"), ("polissorbato/cremofor", r"polissorbato|polisorbato|cremofor|polioxil"),
    ("benzalconio (conservante)", r"cloreto de benzalconio|benzalconio"), ("alcool benzilico", r"alcool benzilico"),
    ("latex/borracha", r"latex|borracha"), ("sodio (teor)", r"\bsodio\b|cloreto de sodio"), ("potassio", r"potassio"),
]
ALERTAS_RX = [(g, re.compile(rx)) for g, rx in ALERTAS]


def alertas_composicao(composicao, texto_secoes):
    """Marca excipientes/ingredientes de atencao presentes na COMPOSICAO (e cita avisos da bula sobre eles)."""
    base = unicodedata.normalize("NFKD", composicao["texto_original"]).encode("ascii", "ignore").decode().lower()
    achou = []
    for g, rx in ALERTAS_RX:
        m = rx.search(base)
        if m:
            achou.append({"grupo": g, "termo": m.group(0), "contexto": base[max(0, m.start() - 40): m.end() + 40].strip()})
    return achou


# ---------------- indice clinico por tema ----------------
TEMAS = {
    "gravidez": r"gravid|gestan|gesta[cç]|teratogen|malforma|embri|fetal|fetos?\b|contracepti",
    "lactacao": r"lacta[cç]|amament|leite materno",
    "idosos": r"idos[oa]s?\b|geri[aá]tric|65 anos|75 anos",
    "pediatria": r"pedi[aá]tric|crian[cç]as?\b|neonat|lactentes?\b|adolescentes?\b|menores de \d+ anos",
    "insuficiencia_renal": r"insufici[eê]ncia renal|disfun[cç][aã]o renal|clearance de creatinina|clcr|di[aá]lise|hemodi[aá]lise|fun[cç][aã]o renal|nefrotox",
    "insuficiencia_hepatica": r"insufici[eê]ncia hep[aá]tica|disfun[cç][aã]o hep[aá]tica|child-?pugh|fun[cç][aã]o hep[aá]tica|hepatotox|les[aã]o hep[aá]tica",
    "dirigir_veiculos": r"dirigir|operar m[aá]quinas|sonol[eê]ncia|tontura",
    "alcool": r"[aá]lcool|etanol|bebidas? alco[oó]licas?",
    "alimentos_e_habitos": r"alimentos?\b|refei[cç][aã]o|jejum|suco de (?:toranja|grapefruit)|toranja|grapefruit|cafe[ií]na|tabagismo|fumantes?\b|leite\b",
    "exames_laboratoriais": r"exames? laboratoria|interfer[eê]ncia (?:em|nos|com)|falso[- ]positivo|falso[- ]negativo|teste de coombs|resultados? de exame",
    "farmacogenetica": r"metabolizadores (?:lentos|pobres|intermedi[aá]rios|r[aá]pidos|ultra)|polimorfismo|\bHLA-|gen[oó]tipo|G6PD|deficiencia de glicose-6",
    "intervalo_qt": r"intervalo QT|\bQTc?\b|torsades",
    "hipersensibilidade_alergia": r"hipersensibilidade|alergi|anafil|angioedema|stevens|necr[oó]lise epid[eé]rmica|dress\b",
    "peso_obesidade": r"obes|peso corp[oó]reo|[ií]ndice de massa corp[oó]rea|\bIMC\b",
    "sistema_nervoso_central": r"sedativ|depress[aã]o (?:do )?respirat|depress[aã]o do sistema nervoso|convuls|suicid",
    "cardiovascular": r"hipertens|hipotens|taquicardia|bradicardia|arritmia|infarto|insufici[eê]ncia card",
    "metabolico_glicemia": r"hipoglic|hiperglic|glicemia|diabetes",
    "eletrolitos": r"hipercal[eê]mia|hipocal[eê]mia|hipon?atr[eê]mia|hipernatr[eê]mia|eletr[oó]litos?",
}
TEMAS_RX = {k: re.compile(v, re.I) for k, v in TEMAS.items()}


def indice_clinico(secoes, max_por_tema=400):
    """Por tema: frases (de TODAS as secoes clinicas) que o mencionam, com a secao de origem. So localiza; nao interpreta."""
    out = {k: [] for k in TEMAS}
    for chave, texto in secoes.items():
        if chave == "dizeres_legais":
            continue
        for f in ec.frases(texto):
            if len(f) < 25:
                continue
            for tema, rx in TEMAS_RX.items():
                if len(out[tema]) < max_por_tema and rx.search(f):
                    out[tema].append({"secao": NOMES_SECAO.get(chave, chave), "trecho": ec.corta(f, 500)})
    return {k: v for k, v in out.items() if v}


# ---------------- bula completa ----------------
def extrair_bula_completa(pdf):
    base = ec.extrair_um(pdf)  # campos de 1a camada (via, farmacodinamica, farmacocinetica, formas...)
    pages, _ = eb.pdf_para_paginas(pdf)
    txt, hist, _ = eb.limpar(pages)
    secoes, _, _ = eb.separar_secoes(txt)
    m = eb.meta(txt, os.path.basename(pdf))
    head = ec.head_da_bula(txt, m)
    neg = linhas_em_negrito(pdf)
    secoes_completas = {}
    for chave, texto in secoes.items():
        secoes_completas[chave] = {"titulo": NOMES_SECAO.get(chave, chave), "texto": texto,
                                   "subsecoes": divide_subtitulos(texto, neg)}
    comp = composicao_estruturada(head)
    base["campos"]["composicao_estruturada"] = comp
    base["campos"]["alertas_composicao"] = alertas_composicao(comp, secoes)
    base["campos"]["indice_clinico"] = indice_clinico(secoes)
    base["secoes_completas"] = secoes_completas
    base["cabecalho_identificacao"] = "\n".join(head).strip()
    base["historico_de_alteracao"] = hist.strip()[:6000]
    base["n_subtitulos_negrito"] = len(neg)
    base["chars_texto_limpo"] = len(txt)
    return base
