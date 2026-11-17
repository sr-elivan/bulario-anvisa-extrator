#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""amostra.py - sorteio da amostra de validação: 1 bula por estrato (estatina × categoria regulatória), semente 2026.

As bulas são ordenadas como no estudo: primeiro as do lote 1 (coleta de 11 a 13/11/2026), depois as do lote 2 (7 registros
incluídos em 14/11/2026, após a correção da lista de registros ativos); dentro de cada lote, pelo nome do arquivo
"PRODUTO - Empresa [MS registro]" (ordem do Python). Numeração: B001…B085 (lote 1) e B086…B092 (lote 2), a mesma do artigo.
A amostra foi sorteada antes da inclusão do lote 2, só entre as bulas do lote 1: em cada estrato (estatina × categoria),
1 bula com pandas.DataFrame.sample(n=1, random_state=2026). Com dados/corpus_bulas.csv o resultado é idêntico a
dados/amostra_validacao.csv."""
import re

import pandas as pd

SEMENTE = 2026


def _limpo(s):
    return re.sub(r'[\\/:*?"<>|®™]', "", s).strip()


def ordenar_corpus(corpus):
    """corpus: DataFrame com registro_ms, estatina, categoria, produto, empresa (apenas no_corpus == Sim)."""
    c = corpus.copy()
    c["arquivo"] = [f"{_limpo(p).upper()} - {_limpo(e).title()[:40]} [MS {r}]"
                    for p, e, r in zip(c["produto"], c["empresa"], c["registro_ms"], strict=True)]
    c["lote"] = c["lote"].fillna("1").replace("", "1") if "lote" in c else "1"
    c = c.sort_values(["lote", "arquivo"], key=lambda s: s.map(str)).reset_index(drop=True)
    c["id_bula"] = ["B" + str(i + 1).zfill(3) for i in range(len(c))]
    return c


def sortear(corpus, semente=SEMENTE):
    c = ordenar_corpus(corpus)
    c = c[c["lote"] == "1"]  # a amostra foi sorteada antes da inclusão do lote 2
    partes = [g.sample(n=1, random_state=semente) for _, g in c.sort_values("id_bula").groupby(["estatina", "categoria"])]
    return pd.concat(partes).sort_values("id_bula")[["id_bula", "registro_ms", "estatina", "categoria", "produto", "empresa"]]


if __name__ == "__main__":
    import os, sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cp = pd.read_csv(os.path.join(raiz, "dados", "corpus_bulas.csv"), sep=";", encoding="utf-8-sig", dtype=str)
    am = sortear(cp[cp["no_corpus"] == "Sim"])
    ref = pd.read_csv(os.path.join(raiz, "dados", "amostra_validacao.csv"), sep=";", encoding="utf-8-sig", dtype=str)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(am.to_string(index=False))
    print("idêntica a dados/amostra_validacao.csv:", am["registro_ms"].tolist() == ref["registro_ms"].tolist()
          and am["id_bula"].tolist() == ref["id_bula"].tolist())
