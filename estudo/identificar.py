#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""identificar.py - identifica as bulas de estatinas pelo CONTEÚDO (nunca pelo nome do arquivo).

Para cada PDF (busca recursiva): lê o texto, decide a estatina principal (citada >= 5 vezes) e lê o número de registro
no Ministério da Saúde (9 dígitos) escrito na bula. Casa o registro com dados/registros_estatinas.csv:
entra no corpus o registro ATIVO, em monofármaco. Cópias idênticas (mesmo SHA-1) contam uma vez.
Também informa se o PDF é a MESMA versão usada no estudo (SHA-1 em dados/corpus_bulas.csv)."""
import csv, hashlib, os, re, unicodedata

import pymupdf

ESTATINAS = ["atorvastatina", "pitavastatina", "pravastatina", "rosuvastatina", "sinvastatina"]
RX_MS = re.compile(r"(?:M\.?\s?S\.?|Registro|Reg\.)\s*(?:n[o.º°]*)?\s*[:\-]?\s*(1\s?[.,]?\s?\d{4}\s?[.,]?\s?\d{4})", re.I)


def sa(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def ler_csv(caminho):
    return list(csv.DictReader(open(caminho, encoding="utf-8-sig"), delimiter=";"))


def identificar(pasta_pdfs, pasta_dados):
    registros = {r["registro"]: r for r in ler_csv(os.path.join(pasta_dados, "registros_estatinas.csv"))}
    hashes_estudo = {r["registro_ms"]: r["sha1"] for r in ler_csv(os.path.join(pasta_dados, "corpus_bulas.csv")) if r["no_corpus"] == "Sim"}
    pdfs = sorted(os.path.join(r, f) for r, _, fs in os.walk(pasta_pdfs) for f in fs if f.lower().endswith(".pdf"))
    vistos, linhas = set(), []
    for p in pdfs:
        h = hashlib.sha1(open(p, "rb").read()).hexdigest()
        if h in vistos:
            continue
        vistos.add(h)
        try:
            texto = sa(" ".join(pg.get_text() for pg in pymupdf.open(p)))
        except Exception:  # PDF corrompido
            continue
        low = texto.lower()
        cont = {e: low.count(e) for e in ESTATINAS}
        if max(cont.values()) < 5:
            continue  # não é bula de estatina
        lidos = []
        for m in RX_MS.finditer(texto):
            n = re.sub(r"\D", "", m.group(1))[:9]
            if n not in lidos:
                lidos.append(n)
        rg = next((x for x in lidos if x in registros), "")
        info = registros.get(rg, {})
        no_corpus = bool(rg) and info.get("situacao") == "Ativo" and info.get("associacao") != "True"
        motivo = "" if no_corpus else ("registro MS não lido" if not rg else
                                        "associação" if info.get("associacao") == "True" else "registro inativo")
        linhas.append({
            "registro_ms": rg, "estatina": info.get("estatina", max(cont, key=cont.get)), "produto": info.get("produto", ""),
            "empresa": info.get("empresa", ""), "categoria": info.get("categoria", ""), "no_corpus": "Sim" if no_corpus else "Não",
            "motivo_fora": motivo, "arquivo": os.path.relpath(p, pasta_pdfs), "sha1": h,
            "mesma_versao_do_estudo": ("Sim" if hashes_estudo.get(rg) == h else "Não (versão diferente da usada no estudo)")
            if rg in hashes_estudo else "", "registros_lidos": ",".join(lidos), "caminho": p})
    # um registro = uma bula: se houver duas versões, fica a do estudo (ou a primeira)
    por_reg = {}
    for l in linhas:
        if l["no_corpus"] != "Sim":
            continue
        atual = por_reg.get(l["registro_ms"])
        if atual is None or (l["mesma_versao_do_estudo"] == "Sim" and atual["mesma_versao_do_estudo"] != "Sim"):
            if atual is not None:
                atual["no_corpus"], atual["motivo_fora"] = "Não", "outra versão do mesmo registro"
            por_reg[l["registro_ms"]] = l
        else:
            l["no_corpus"], l["motivo_fora"] = "Não", "outra versão do mesmo registro"
    return linhas
