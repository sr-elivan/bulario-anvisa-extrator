#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_registros.py - (opcional) recria dados/registros_estatinas.csv a partir dos dados abertos da Anvisa.

  python ferramentas/gerar_registros.py --anvisa PASTA_DADOS_ABERTOS [--saida dados/registros_estatinas.csv]

PASTA_DADOS_ABERTOS deve conter (baixados de https://dados.anvisa.gov.br):
  TA_CONSULTA_MEDICAMENTOS.CSV  (medicamentos registrados)   e   TA_PRECO_MEDICAMENTO.csv  (lista de preços CMED).
Com os mesmos arquivos usados no estudo (atualização de 13/10/2026; CMED baixada em 08/11/2026) o resultado é idêntico.
"""
import argparse, os, sys

import pandas as pd

RX = r"((?:ator|sin|rosu|pra|lo|flu|pita|ceri)vastatina)"
ORDEM = ["atorvastatina", "fluvastatina", "lovastatina", "pitavastatina", "pravastatina", "rosuvastatina", "sinvastatina"]


def num(v):
    try:
        return float(str(v).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def gerar(pasta):
    m = pd.read_csv(os.path.join(pasta, "TA_CONSULTA_MEDICAMENTOS.CSV"), sep=";", encoding="cp1252", dtype=str)
    m = m[m["SUBSTANCIAS_MEDICAMENTOS"].str.contains(RX, case=False, na=False)].copy()
    m["estatina"] = m["SUBSTANCIAS_MEDICAMENTOS"].str.lower().str.extract(RX)[0]
    m["associacao"] = m["SUBSTANCIAS_MEDICAMENTOS"].str.lower().str.contains("ezetim|anlodip|fenofib|ácido acetil|aspirin")
    reg = (m.sort_values("DATA_PUBLICACAO").groupby("NU_REGISTRO_PRODUTO", as_index=False)
           .agg(estatina=("estatina", "first"), associacao=("associacao", "first"), produto=("NO_PRODUTO", "first"),
                substancias=("SUBSTANCIAS_MEDICAMENTOS", "first"), empresa=("NO_RAZAO_SOCIAL_EMPRESA", "first"),
                cnpj=("NU_CNPJ_EMPRESA", "first"), categoria=("DS_TIPO_CATEGORIA_REGULATORIA", "first"),
                referencia_declarada=("DS_REFERENCIA", lambda s: "; ".join(sorted(set(x for x in s.dropna())))[:200]),
                situacao=("VALIDADE_SITUACAO", lambda s: "Ativo" if (s == "Ativo").any() else s.iloc[0]), vencimento=("DT_VENCIMENTO_PRODUTO", "first")))
    # o arquivo tem uma linha por APRESENTAÇÃO: o registro está ativo se qualquer apresentação estiver ativa (corrigido na v0.2.0)
    reg["eh_referencia"] = reg["referencia_declarada"].str.contains(r"REFER[ÊE]NCIA DESDE|MED DE REF", case=False, na=False) & \
        reg["referencia_declarada"].str.upper().str.contains("REFER|REF ")
    p = pd.read_csv(os.path.join(pasta, "TA_PRECO_MEDICAMENTO.csv"), sep=";", encoding="utf-8-sig", dtype=str)
    p = p[p["SUBSTÂNCIA"].str.contains(RX, case=False, na=False)].copy()
    p["registro9"] = p["REGISTRO"].str[:9]
    p["pmc18"] = p["PMC 18 %"].map(num)
    cm = p.groupby("registro9").agg(cmed_apresentacoes=("APRESENTAÇÃO", "count"),
                                    cmed_comercializado_2025=("COMERCIALIZAÇÃO 2025", lambda s: "Sim" if (s == "Sim").any() else "Não"),
                                    cmed_pmc18_min=("pmc18", "min"), cmed_pmc18_max=("pmc18", "max")).reset_index()
    reg = reg.merge(cm, how="left", left_on="NU_REGISTRO_PRODUTO", right_on="registro9").drop(columns=["registro9"])
    reg["cmed_apresentacoes"] = reg["cmed_apresentacoes"].fillna(0).astype(int)
    reg["cmed_comercializado_2025"] = reg["cmed_comercializado_2025"].fillna("sem preço CMED")
    reg["link_bulario"] = reg["NU_REGISTRO_PRODUTO"].map(lambda x: f"https://consultas.anvisa.gov.br/#/bulario/?numeroRegistro={x}")
    reg["estatina"] = pd.Categorical(reg["estatina"], ORDEM, ordered=True)
    reg = reg.sort_values(["estatina", "associacao", "categoria", "produto"]).rename(columns={"NU_REGISTRO_PRODUTO": "registro"})
    return reg[["registro", "estatina", "associacao", "produto", "substancias", "empresa", "cnpj", "categoria", "referencia_declarada",
                "eh_referencia", "situacao", "vencimento", "cmed_apresentacoes", "cmed_comercializado_2025", "cmed_pmc18_min",
                "cmed_pmc18_max", "link_bulario"]]


def main():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anvisa", required=True)
    ap.add_argument("--saida", default=os.path.join(raiz, "dados", "registros_estatinas.csv"))
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    reg = gerar(a.anvisa)
    reg.to_csv(a.saida, sep=";", index=False, encoding="utf-8-sig")
    ativos = reg[(reg["situacao"] == "Ativo") & (~reg["associacao"])]
    print(f"OK: {len(reg)} registros de estatinas; {len(ativos)} ativos em monofármaco -> {a.saida}")


if __name__ == "__main__":
    main()
