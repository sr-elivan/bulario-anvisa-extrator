#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_referencia.py - (opcional) recria dados/interacoes_graves_referencia.csv: interações graves do Drugs.com por estatina,
com o nome em DCB e a situação de registro no Brasil.

  python ferramentas/gerar_referencia.py --anvisa PASTA_DADOS_ABERTOS [--drugscom dados/drugscom_major_2026-11-13.json]

Para uma lista nova do Drugs.com, monte um JSON no mesmo formato ({"dados": {"atorvastatin": {"major": [...]}, ...}}) a partir
das páginas https://www.drugs.com/drug-interactions/<estatina>-index.html?filter=3 (consulta manual).
"""
import argparse, json, os, sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "estudo"))
from regras import DCB, EST, NAO_FARMACO  # noqa: E402


def gerar(json_drugs, pasta_anvisa):
    d = json.load(open(json_drugs, encoding="utf-8"))["dados"]
    m = pd.read_csv(os.path.join(pasta_anvisa, "TA_CONSULTA_MEDICAMENTOS.CSV"), sep=";", encoding="cp1252", dtype=str,
                    usecols=["NU_REGISTRO_PRODUTO", "SUBSTANCIAS_MEDICAMENTOS", "VALIDADE_SITUACAO", "TIPO_AUTORIZACAO"])
    m = m[m["TIPO_AUTORIZACAO"] == "REGISTRADO"]
    subs = m["SUBSTANCIAS_MEDICAMENTOS"].fillna("").str.lower()
    reg = {}
    for en, (pt, rx) in DCB.items():
        msk = subs.str.contains(rx, regex=True)
        reg[en] = (pt, m[msk & (m["VALIDADE_SITUACAO"] == "Ativo")]["NU_REGISTRO_PRODUTO"].nunique(), m[msk]["NU_REGISTRO_PRODUTO"].nunique())
    linhas = []
    for en_est, v in d.items():
        for f in v["major"]:
            if f in NAO_FARMACO:
                continue
            pt, at, tot = reg[f]
            linhas.append({"estatina": EST[en_est], "farmaco_drugscom": f, "farmaco_dcb": pt, "registros_ativos_brasil": at,
                           "registros_total_brasil": tot, "registro_ativo_no_brasil": "Sim" if at else "Não"})
    return pd.DataFrame(linhas).sort_values(["estatina", "farmaco_dcb"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anvisa", required=True)
    ap.add_argument("--drugscom", default=os.path.join(RAIZ, "dados", "drugscom_major_2026-11-13.json"))
    ap.add_argument("--saida", default=os.path.join(RAIZ, "dados", "interacoes_graves_referencia.csv"))
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    df = gerar(a.drugscom, a.anvisa)
    df.to_csv(a.saida, index=False, encoding="utf-8-sig", sep=";")
    print(f"OK: {len(df)} pares estatina × fármaco -> {a.saida}")
    print(df.groupby("estatina").agg(graves=("farmaco_dcb", "count"),
                                     com_registro_ativo=("registro_ativo_no_brasil", lambda s: int((s == "Sim").sum()))).to_string())


if __name__ == "__main__":
    main()
