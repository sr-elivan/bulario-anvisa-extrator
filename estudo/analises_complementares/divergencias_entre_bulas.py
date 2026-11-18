#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""divergencias_entre_bulas.py - consistência entre bulas da MESMA estatina (dados/classificacao_revisada.csv).
Para cada estatina × fármaco grave, verifica se a classificação varia entre as bulas:
  - cobertura (citado × não citado)  -> afeta a completude ampla
  - forma (nominal × classe × não citado) -> afeta a completude estrita
  - manejo (C/L/M/S/X)
Saídas: resultados/divergencias_entre_bulas.json e .csv (uma linha por combinação que varia)."""
import json, os, sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))  # raiz do repositório
SAIDA = os.path.join(AQUI, "resultados"); os.makedirs(SAIDA, exist_ok=True)
g = pd.read_csv(os.path.join(RAIZ, "dados", "classificacao_revisada.csv"), sep=";", encoding="utf-8-sig", dtype=str).fillna("")
g["citado"] = g["citacao"] != "nao citada"

linhas, por_est = [], {}
for e, x in g.groupby("estatina"):
    nb = x["id_bula"].nunique()
    r = {"bulas": nb, "combinacoes": 0, "variam": 0, "variam_cobertura": 0, "variam_forma": 0, "variam_manejo": 0,
         "pares": len(x), "pares_fora_da_moda": 0}
    for farm, y in x.groupby("farmaco_dcb"):
        r["combinacoes"] += 1
        vc, vf, vm = y["citado"].nunique() > 1, y["citacao"].nunique() > 1, y["manejo"].nunique() > 1
        if not (vc or vf or vm):
            continue
        r["variam"] += 1; r["variam_cobertura"] += vc; r["variam_forma"] += vf; r["variam_manejo"] += vm
        chave = y["citacao"] + "|" + y["manejo"]
        # moda; empate (ex.: pravastatina, 2 bulas) -> fica como referência a classificação mais completa (citada, mais restritiva)
        PR = {"contraindicar/evitar": 4, "limite de dose": 3, "monitorar": 2, "sem orientacao": 1, "nao se aplica": 0}
        cont = chave.value_counts()
        moda = max(cont.index, key=lambda k: (cont[k], k.split("|")[0] != "nao citada", PR.get(k.split("|")[1], 0)))
        fora = y[chave != moda]
        r["pares_fora_da_moda"] += len(fora)
        linhas.append({"estatina": e, "farmaco_dcb": farm, "bulas": nb,
                       "citacao": "; ".join(f"{k} {v}" for k, v in y["citacao"].value_counts().items()),
                       "manejo": "; ".join(f"{k} {v}" for k, v in y["manejo"].value_counts().items()),
                       "varia_cobertura": int(vc), "varia_forma": int(vf), "varia_manejo": int(vm),
                       "bulas_divergentes": ", ".join(sorted(fora["id_bula"]))})
    por_est[e] = r

tot = {k: sum(v[k] for v in por_est.values()) for k in next(iter(por_est.values())) if k != "bulas"}
tot["bulas"] = int(g["id_bula"].nunique())
tot["bulas_com_divergencia"] = len({b for l in linhas for b in l["bulas_divergentes"].split(", ") if b})
out = {"total": tot, "por_estatina": por_est}
json.dump(out, open(os.path.join(SAIDA, "divergencias_entre_bulas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.DataFrame(linhas).to_csv(os.path.join(SAIDA, "divergencias_entre_bulas.csv"), sep=";", index=False, encoding="utf-8-sig")
print(json.dumps(out, ensure_ascii=False, indent=1))
for l in linhas:
    print(l["estatina"], l["farmaco_dcb"], "|", l["citacao"], "|", l["manejo"], "|", l["bulas_divergentes"])
