#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""texto.py - PDF de bula profissional (RDC 47/2009) -> texto limpo e seções padronizadas da Anvisa."""
import re, shutil, subprocess, unicodedata
from collections import Counter


# chave -> regex (aplicado ao titulo normalizado: sem acento, maiusculo)
SECOES = [
    ("indicacoes", r"INDICACAO|INDICACOES"),
    ("resultados_eficacia", r"RESULTADOS? DE EFICACIA"),
    ("caracteristicas_farmacologicas", r"CARA?C?T?E?RISTICAS? FA?R?MA(?:CO)?COLOGICAS?"),  # aceita "CARATERISTICAS" (erro de grafia visto no XTANDI)
    ("contraindicacoes", r"CONTRA-?INDICACOES?"),
    ("advertencias_precaucoes", r"ADVERTENCIAS(\s+E(\s+PRECAUCOES)?)?"),  # aceita "5. ADVERTENCIAS   E" (titulo partido em 2 linhas)
    ("interacoes", r"INTERACOES MEDICAMENTOSAS"),
    ("armazenamento", r"CUIDADOS DE ARMAZENAMENTO( DO MEDICAMENTO)?|CUIDADOS DE ARMAZENAGEM|CUIDADOS DE CONSERVACAO( DO MEDICAMENTO)?"),
    ("posologia", r"POSOLOGIA E MODO DE USAR"),
    ("reacoes_adversas", r"REACOES ADVERSAS"),
    ("superdose", r"SUPERDOSE|SUPERDOSAGEM"),
    ("dizeres_legais", r"(III\s*[-–.]?\s*)?DIZERES LEGAIS"),
]
# secoes que toda bula profissional deveria ter (dizeres_legais e eficacia podem faltar)
ESPERADAS = ["indicacoes", "contraindicacoes", "advertencias_precaucoes",
             "posologia", "reacoes_adversas", "superdose", "armazenamento"]

RE_HIST = re.compile(r"^\s*(anexo\s+[a-z]\s*)?hist[oó]rico\s+de\s+altera[cç]", re.I)
RE_PAGNUM = re.compile(r"^\s*(p[aá]gina\s+)?\d{1,3}(\s*(de|/)\s*\d{1,3})?\s*$", re.I)


def norm(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()


def pdf_para_paginas(pdf):
    """Texto por página: pdftotext -layout (Xpdf 4.00, versão usada no estudo; Poppler não testado); se faltarem seções (bula em 2 colunas), tenta o PyMuPDF."""
    exe = shutil.which("pdftotext")
    if exe:
        r = subprocess.run([exe, "-layout", "-enc", "UTF-8", pdf, "-"],
                           capture_output=True)
        if r.returncode == 0:
            txt = r.stdout.decode("utf-8", errors="replace")
            pages = txt.split("\f")
            if pages and not pages[-1].strip():
                pages = pages[:-1]
            # bulas em 2 colunas: o pdftotext -layout mistura as colunas. Se faltarem secoes, tenta o PyMuPDF.
            try:
                def _n(pgs):
                    s = separar_secoes(limpar(pgs)[0])[0]
                    return len([k for k in ESPERADAS + ["caracteristicas_farmacologicas"] if len(s.get(k, "")) >= 15])
                if _n(pages) < 6:
                    import pymupdf as _fz
                    alt = [p.get_text("text") for p in _fz.open(pdf)]
                    if _n(alt) > _n(pages):
                        return alt, "pymupdf (colunas)"
            except Exception:
                pass
            return pages, "pdftotext"
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(pdf)
    return [p.get_text("text") for p in doc], "pymupdf"


def limpar(pages):
    """Remove espacos finais, numeros de pagina, rodapes/cabecalhos repetidos."""
    # corta o historico de alteracao (tabela de controle regulatorio)
    # a tabela "Historico de alteracao" fica no FIM da bula: ignora mencoes no inicio (ja cortaram bulas inteiras)
    achados = [(pi, li) for pi, p in enumerate(pages) for li, l in enumerate(p.split("\n")) if RE_HIST.match(l)]
    corte = None
    if achados:
        total = sum(len(p) for p in pages) or 1
        depois = [a for a in achados if a[0] >= len(pages) * 0.5]
        corte = depois[0] if depois else achados[-1]
        removido = sum(len(p) for p in pages[corte[0] + 1:]) + len("\n".join(pages[corte[0]].split("\n")[corte[1]:]))
        if removido > 0.6 * total:  # cortaria mais de 60% do texto: nao e o historico
            corte = None
    historico = ""
    if corte:
        pi, li = corte
        linhas = pages[pi].split("\n")
        historico = "\n".join(linhas[li:] + pages[pi + 1:])
        pages = pages[:pi] + ["\n".join(linhas[:li])]

    pg_lines = [[l.rstrip() for l in p.split("\n")] for p in pages]
    # linhas que aparecem em muitas paginas = cabecalho/rodape
    cont = Counter()
    for ls in pg_lines:
        for l in set(x.strip() for x in ls if len(x.strip()) >= 6):
            cont[l] += 1
    lim = max(3, int(0.4 * len(pg_lines)))
    repet = {l for l, c in cont.items() if c >= lim}
    saida = []
    for ls in pg_lines:
        for l in ls:
            s = l.strip()
            if s in repet or RE_PAGNUM.match(l):
                continue
            saida.append(l)
        saida.append("")
    txt = "\n".join(saida)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip() + "\n"
    return txt, historico, sorted(repet)


def achar_titulos(linhas):
    """Lista (indice_linha, chave) de linhas que sao titulos de secao."""
    res = []
    pats = [(k, re.compile(r"^(\d{1,2}(?:\.\s*|\s+))?(" + rx + r")\s*:?$")) for k, rx in SECOES]  # aceita "5.ADVERTENCIAS"
    for i, l in enumerate(linhas):
        if not l.strip() or len(l) > 90:
            continue
        if len(l) - len(l.lstrip()) > 15:  # titulos reais nao ficam muito indentados
            continue
        n = norm(l)
        for k, rx in pats:
            if rx.match(n):
                res.append((i, k))
                break
    return res


def achar_ini(linhas):
    for i, l in enumerate(linhas):
        sl = l.strip()
        if 0 < len(sl) <= 90 and re.match(r"^(II\s*[-–.]?\s*)?INFORMACOES TECNICAS", norm(sl)):
            return i
    return 0


def _pats_tolerantes():
    ns = [(k, rx.replace(" ", "")) for k, rx in SECOES]
    ini = [(k, re.compile(r"^(\d{1,2}[.\-)]?)?(" + r + r")")) for k, r in ns]
    fim = [(k, re.compile(r"(?:^|\s{2,})(\d{1,2}[.\-)]?)(" + r + r")\s*:?\s*$")) for k, r in ns]
    return ini, fim


def _separar(linhas, tolerante):
    """Devolve [(indice_linha, chave)]. No modo tolerante aceita '1- INDICACOES', '1) ...', 'INDICACOE S' (espacos
    no meio), titulo com texto na mesma linha e titulo no fim de uma linha de tabela (a linha e partida em duas)."""
    if not tolerante:
        return achar_titulos(linhas), linhas
    ini, fim = _pats_tolerantes()
    novas, res = [], []
    for l in linhas:
        n = re.sub(r"\s+", "", norm(l))
        partida = False
        for _k, rx in fim:  # titulo no fim da linha: separa o texto que vem antes
            m = rx.search(n)
            if m and re.search(r"\S\s{2,}\S", l) and len(l.strip()) < 200:
                # localiza o inicio do titulo no texto original: ultimo bloco apos 2+ espacos
                partes = re.split(r"\s{2,}", l.rstrip())
                if len(partes) >= 2 and re.sub(r"\s+", "", norm(partes[-1])) and rx.search(re.sub(r"\s+", "", norm(partes[-1]))):
                    antes = "  ".join(partes[:-1]).strip()
                    if antes:
                        novas.append(antes)
                    novas.append(partes[-1].strip())
                    partida = True
                    break
        if not partida:
            novas.append(l)
    linhas = novas
    for i, l in enumerate(linhas):
        s = l.strip()
        if not s or len(l) - len(l.lstrip()) > 40:  # modo tolerante: titulos centralizados
            continue
        n = re.sub(r"\s+", "", norm(s))
        for k, rx in ini:
            m = rx.match(n)
            if not m:
                continue
            resto = n[m.end():]
            numerado = bool(m.group(1))
            if (not resto.strip(":") and len(s) <= 100) or (numerado and len(s) <= 220):
                res.append((i, k))
                break
    return res, linhas


RE_NUMERADO = re.compile(r"^\s*\d{1,2}\s*[.\-)]?\s*\S")


def _so_numerados(linhas, tit):
    """Bula com títulos numerados ("6. INTERAÇÕES MEDICAMENTOSAS"): um subtítulo homônimo SEM número (ex.: "Interações
    medicamentosas" dentro da seção 5 das bulas de sinvastatina) não abre seção. Só vale quando a chave também aparece
    numerada e a bula numera ao menos 4 títulos (auditoria pré-publicação, 16/11/2026)."""
    num = [(i, k) for i, k in tit if RE_NUMERADO.match(linhas[i])]
    if len(num) < 4:
        return tit
    chaves_num = {k for _, k in num}
    return [(i, k) for i, k in tit if k not in chaves_num or RE_NUMERADO.match(linhas[i])]


def separar_secoes(txt):
    """Primeiro o modo estrito; se faltarem secoes basicas, tenta o tolerante (grafias e formatos diferentes)."""
    linhas0 = txt.split("\n")
    ini0 = achar_ini(linhas0)
    tit0 = [(i, k) for i, k in achar_titulos(linhas0) if i >= ini0]
    achadas = {k for _, k in tit0}
    todos0 = achar_titulos(linhas0)  # o "II - INFORMACOES TECNICAS" pode vir depois dos titulos (ex.: Palexis LP)
    if len({k for _, k in todos0}) >= len(achadas) + 3:
        ini0, tit0 = 0, list(todos0)
        achadas = {k for _, k in tit0}
    modos = [(False, linhas0, tit0, ini0)]
    if len([k for k in ESPERADAS if k not in achadas]) >= 2 or "caracteristicas_farmacologicas" not in achadas:
        tit1, linhas1 = _separar(linhas0, True)
        ini1 = achar_ini(linhas1)
        tit1 = [(i, k) for i, k in tit1 if i >= ini1]
        # so troca se o modo tolerante achar MAIS secoes distintas
        if len({k for _, k in tit1}) > len(achadas):
            modos.append((True, linhas1, tit1, ini1))
    tol, linhas, tit, ini = modos[-1]
    tit = _so_numerados(linhas, tit)
    secoes, ocorr = {}, Counter()
    for idx, (i, k) in enumerate(tit):
        fim = tit[idx + 1][0] if idx + 1 < len(tit) else len(linhas)
        corpo_linhas = linhas[i + 1:fim]
        if tol and len(linhas[i].strip()) > 40:  # titulo com texto na mesma linha: nao perder o texto
            corpo_linhas = [linhas[i]] + corpo_linhas
        corpo = "\n".join(corpo_linhas).strip()
        ocorr[k] += 1
        if k in secoes:  # titulo repetido (ex.: duas apresentacoes na mesma bula)
            secoes[k] += "\n\n--- (repeticao do titulo) ---\n\n" + corpo
        else:
            secoes[k] = corpo
    return secoes, ocorr, ini


def meta(txt, nome_arquivo):
    linhas = [l.strip() for l in txt.split("\n")]
    nao_vazias = [l for l in linhas if l]
    m = {"arquivo": nome_arquivo}
    m["nome_capa"] = re.sub(r"[®™]", "", nao_vazias[0]).strip() if nao_vazias else ""
    r = re.search(r"Registro\s*(?:MS)?\s*[:\-]?\s*([\d][\d.\s]{6,16}\d)", txt, re.I)
    m["registro"] = re.sub(r"\s+", "", r.group(1)) if r else ""
    r = re.search(r"aprovad[ao]\s+pela\s+anvisa\s+em\s*:?\s*(\d{2}/\d{2}/\d{4})", txt, re.I)
    m["aprovada_anvisa"] = r.group(1) if r else ""
    r = re.search(r"Registrad[oa](?:\s+e\s+produzid[oa])?\s+(?:e\s+importad[oa]\s+)?por\s*:?\s*\n?\s*([^\n]+)", txt, re.I)
    m["empresa"] = r.group(1).strip() if r else ""
    vias = re.findall(r"^\s*USO\s+(?!ADULTO|PEDI|PEDI[ÁA]TRICO)([A-ZÀ-Ú /]+)$", txt, re.M)
    m["via"] = sorted({v.strip() for v in vias})
    # bloco de identificacao: de "IDENTIFICACAO" ate "INFORMACOES TECNICAS"
    ls = txt.split("\n")
    a = next((i for i, l in enumerate(ls) if "IDENTIFICACAO DO MEDICAMENTO" in norm(l)), None)
    b = next((i for i, l in enumerate(ls) if "INFORMACOES TECNICAS" in norm(l)), None)
    m["identificacao"] = "\n".join(ls[a + 1:b]).strip() if a is not None and b else ""
    return m
