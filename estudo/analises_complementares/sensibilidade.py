#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sensibilidade.py - análise de sensibilidade da completude às decisões de pertinência a classe.
Fonte: dados/classificacao_revisada.csv (classificação final); completude = mediana por bula (Tabela 4 do artigo).
Cenários:
  estrita                      só citação nominal
  ampla (principal)            nominal + classe (livro de códigos: inclui inibidores de transportadores BCRP/OATP1B1)
  ampla sem transportadores    a citação apenas por "inibidores de transportadores/BCRP/OATP1B1" passa a não citada
  ampla com imunossupressores  "medicamentos imunossupressores" (advertência das bulas de atorvastatina) passa a cobrir
                               os fármacos do grupo L04 da ATC na lista de referência: leflunomida, teriflunomida, lenalidomida
Saída: resultados/sensibilidade.json"""
import json, os, sys

import pandas as pd
from scipy.stats import kruskal

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))  # raiz do repositório
SAIDA = os.path.join(AQUI, "resultados"); os.makedirs(SAIDA, exist_ok=True)
# desde 16/11/2026: classificação final (revisão humana + consenso + auditoria pré-publicação)
d = pd.read_csv(os.path.join(RAIZ, "dados", "classificacao_revisada.csv"), sep=";", encoding="utf-8-sig",
                dtype=str).fillna("").rename(columns={"citacao": "sug_citacao", "classe_citada": "sug_classe", "id_bula": "bula_id"})
TRANSP = d["sug_classe"].str.contains("transportador|BCRP|OATP1B1", regex=True)
PI_ROSU = (d["estatina"] == "rosuvastatina") & d["sug_classe"].str.contains("protease")  # "certos inibidores de protease"
L04 = {"leflunomida", "teriflunomida", "lenalidomida"}
TR_ATORVA = {"resmetirom", "teriflunomida", "leflunomida", "vadadustate"}  # auditoria das não citadas (classe duvidosa)
nominal = d["sug_citacao"] == "nominal"
classe = d["sug_citacao"] == "classe"
cen = {
    "estrita": nominal,
    "ampla (principal)": nominal | classe,
    "ampla sem transportadores": nominal | (classe & ~TRANSP),
    "ampla com imunossupressores (L04)": nominal | classe | ((d["estatina"] == "atorvastatina") & d["farmaco_dcb"].isin(L04)),
    # "inibidores do CYP3A4/transportadores" (atorvastatina) sem dizer QUAL transportador: inibidores de OATP1B/BCRP pela FDA
    "ampla sem \"certos inibidores de protease\" (rosuvastatina)": nominal | (classe & ~PI_ROSU),
    "ampla com transportadores não especificados (atorvastatina)": nominal | classe | ((d["estatina"] == "atorvastatina") & d["farmaco_dcb"].isin(TR_ATORVA)),
}
out = {"fonte": "dados/classificacao_revisada.csv (classificação final)", "pares_transportadores": int((classe & TRANSP).sum()),
       "pares_pi_rosuvastatina": int((classe & PI_ROSU).sum()),
       "pares_L04_atorvastatina": int(((d["estatina"] == "atorvastatina") & d["farmaco_dcb"].isin(L04) & ~(nominal | classe)).sum()),
       "pares_transp_atorvastatina": int(((d["estatina"] == "atorvastatina") & d["farmaco_dcb"].isin(TR_ATORVA) & ~(nominal | classe)).sum()),
       "cenarios": {}}
for nome, m in cen.items():
    x = d.assign(c=m.astype(int))
    pb = x.groupby(["bula_id", "estatina", "categoria"])["c"].mean().mul(100).reset_index()
    r = {"mediana": round(pb["c"].median(), 1), "iiq": f"{pb['c'].quantile(.25):.1f}–{pb['c'].quantile(.75):.1f}",
         "kruskal_categorias": round(float(kruskal(*[g["c"].values for _, g in pb.groupby("categoria")]).pvalue), 3),
         "por_estatina": {e: round(g["c"].median(), 1) for e, g in pb.groupby("estatina")}}
    out["cenarios"][nome] = r
    print(f"{nome:38s} {r['mediana']:5.1f}%  IIQ {r['iiq']:12s} KW p={r['kruskal_categorias']}  {r['por_estatina']}")
pb = d.assign(c=(nominal | classe).astype(int)).groupby(["bula_id", "estatina"])["c"].mean().mul(100).reset_index()
out["peso_igual_por_estatina"] = round(pb.groupby("estatina")["c"].median().mean(), 1)
out["citacoes_so_por_classe_pct"] = round(100 * classe.sum() / (nominal | classe).sum(), 1)
_br = d["registro_ativo_no_brasil"].str.lower().str.startswith("s")
out["citacoes_so_por_classe_pct_registrados_br"] = round(100 * (classe & _br).sum() / ((nominal | classe) & _br).sum(), 1)
_ac = (nominal | classe) & ~d["manejo"].isin(["sem orientacao", "nao se aplica"])
out["completude_com_orientacao_de_manejo"] = round(d.assign(c=_ac.astype(int)).groupby("bula_id")["c"].mean().mul(100).median(), 1)
print("peso igual por estatina:", out["peso_igual_por_estatina"], "| só por classe:", out["citacoes_so_por_classe_pct"],
      "% (registrados no Brasil:", out["citacoes_so_por_classe_pct_registrados_br"], "%) | com orientação de manejo:",
      out["completude_com_orientacao_de_manejo"])
json.dump(out, open(os.path.join(SAIDA, "sensibilidade.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("pares afetados: transportadores", out["pares_transportadores"], "| L04", out["pares_L04_atorvastatina"])
