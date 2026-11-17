#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""estatisticas.py - completude (ampla, estrita, só fármacos registrados no Brasil), comparação entre categorias,
manejo, local e interações mais omitidas. Entrada: tabela com colunas registro_ms, estatina, categoria, farmaco_dcb,
registro_ativo_no_brasil, citacao, manejo, local (pré-classificação OU classificação revisada)."""
from scipy.stats import kruskal, mannwhitneyu


def _iiq(s):
    return f"{s.quantile(.25):.1f}–{s.quantile(.75):.1f}"


def estatisticas(d, fonte):
    d = d.copy()
    d["ampla"] = d["citacao"].isin(["nominal", "classe"]).astype(int)
    d["estrita"] = (d["citacao"] == "nominal").astype(int)
    d["br"] = d["registro_ativo_no_brasil"] == "Sim"
    pb = d.groupby(["registro_ms", "estatina", "categoria"]).agg(ampla=("ampla", "mean"), estrita=("estrita", "mean")).reset_index()
    pb = pb.merge(d[d["br"]].groupby("registro_ms").agg(ampla_br=("ampla", "mean")).reset_index(), on="registro_ms")
    for c in ("ampla", "estrita", "ampla_br"):
        pb[c] *= 100
    out = {"fonte": fonte, "n_bulas": int(pb["registro_ms"].nunique()), "n_pares": int(len(d))}
    out["geral"] = {c: {"mediana": round(pb[c].median(), 1), "iiq": _iiq(pb[c])} for c in ("ampla", "estrita", "ampla_br")}
    out["por_estatina"] = {}
    for e, g in pb.groupby("estatina"):
        out["por_estatina"][e] = {"bulas": len(g), **{c: {"mediana": round(g[c].median(), 1), "iiq": _iiq(g[c]),
                                                          "min": round(g[c].min(), 1), "max": round(g[c].max(), 1)}
                                                      for c in ("ampla", "estrita", "ampla_br")},
                                  "por_categoria": {cat: round(gg["ampla"].median(), 1) for cat, gg in g.groupby("categoria")}}
    out["por_categoria"] = {cat: {"bulas": len(g), "ampla": round(g["ampla"].median(), 1), "iiq": _iiq(g["ampla"])}
                            for cat, g in pb.groupby("categoria")}
    out["kruskal_categorias_geral"] = round(float(kruskal(*[g["ampla"].values for _, g in pb.groupby("categoria")]).pvalue), 3)
    out["generico_vs_similar_por_estatina"] = {}
    for e, g in pb.groupby("estatina"):
        a, b = g[g.categoria == "Genérico"]["ampla"], g[g.categoria == "Similar"]["ampla"]
        if len(a) and len(b):
            iguais = a.nunique() == 1 and b.nunique() == 1 and a.iloc[0] == b.iloc[0]
            out["generico_vs_similar_por_estatina"][e] = "valores idênticos" if iguais else round(float(mannwhitneyu(a, b).pvalue), 3)
    cit = d[d["ampla"] == 1]
    out["manejo_entre_citadas"] = {k: int(v) for k, v in cit["manejo"].value_counts().items()}
    out["local_entre_citadas"] = {k: int(v) for k, v in cit["local"].value_counts().items()}
    om = d[d["br"]].groupby(["estatina", "farmaco_dcb"]).agg(omite=("ampla", lambda s: round(100 * (1 - s.mean()), 1))).reset_index()
    out["mais_omitidas_registro_br"] = om[om["omite"] >= 50].sort_values(["omite", "estatina"], ascending=[False, True]).to_dict("records")
    return out, pb
