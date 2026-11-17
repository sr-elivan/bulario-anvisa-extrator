# -*- coding: utf-8 -*-
"""concordancia_avaliadores.py - concordância entre o avaliador 1 e a avaliadora 2 (às cegas) na amostra de 12 bulas (477 pares).

Entrada: dados/avaliacao_dupla/amostra_dupla_avaliacao.csv (classificação do avaliador 1 ANTES do consenso e da avaliadora 2;
o formulário da avaliadora 2 tinha só citação e manejo).
Medidas: concordância observada, kappa de Cohen com IC95% (variância assintótica de Fleiss, Cohen e Everitt, 1969),
PABAK = (k·Po − 1)/(k − 1) (Byrt, Bishop e Carlin, 1993) e interpretação de Landis e Koch (1977).
Uso: python ferramentas/concordancia_avaliadores.py"""
import json, os
import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = {"citacao": ["nominal", "classe", "nao citada"],
        "manejo": ["contraindicar/evitar", "limite de dose", "monitorar", "sem orientacao", "nao se aplica"]}
d = pd.read_csv(os.path.join(RAIZ, "dados", "avaliacao_dupla", "amostra_dupla_avaliacao.csv"), sep=";", encoding="utf-8-sig", dtype=str)


def landis_koch(k):
    return ("pior que o acaso" if k < 0 else "leve" if k <= .20 else "razoável" if k <= .40 else "moderada" if k <= .60
            else "substancial" if k <= .80 else "quase perfeita")


res = {"bulas": int(d.id_bula.nunique()), "pares": len(d)}
for g, cats in CATS.items():
    a, b = d[g + "_avaliador1"], d[g + "_avaliadora2"]
    q, n, ix = len(cats), len(d), {c: i for i, c in enumerate(cats)}
    m = np.zeros((q, q))
    for x, y in zip(a, b):
        m[ix[x], ix[y]] += 1
    p = m / n; pr, pc = p.sum(1), p.sum(0); po, pe = np.trace(p), float(pr @ pc); k = (po - pe) / (1 - pe)
    t1 = sum(p[i, i] * (1 - (pr[i] + pc[i]) * (1 - k)) ** 2 for i in range(q))
    t2 = (1 - k) ** 2 * sum(p[i, j] * (pc[i] + pr[j]) ** 2 for i in range(q) for j in range(q) if i != j)
    se = np.sqrt((t1 + t2 - (k - pe * (1 - k)) ** 2) / (n * (1 - pe) ** 2))
    res[g] = {"concordancia_observada_%": round(100 * po, 1), "kappa": round(k, 3),
              "ic95": [round(k - 1.96 * se, 3), round(min(1.0, k + 1.96 * se), 3)], "pabak": round((q * po - 1) / (q - 1), 3),
              "landis_koch": landis_koch(k)}
print(json.dumps(res, ensure_ascii=False, indent=1))
