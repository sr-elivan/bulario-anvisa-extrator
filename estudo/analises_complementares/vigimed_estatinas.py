#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vigimed_estatinas.py - notificações brasileiras (VigiMed/Anvisa, dados abertos) com estatinas e interações graves de referência.
Fonte: https://dados.anvisa.gov.br/dados/ (VigiMed_Notificacoes.csv, VigiMed_Medicamentos.csv, VigiMed_Reacoes.csv).
Perguntas:
  1. Quantas notificações têm estatina como suspeita/em interação (por estatina; graves; eventos musculares)?
  2. Em quantas o notificador codificou interação (medicamento "Interação" ou termo "Interação medicamentosa")?
  3. Em quantas foi relatado, junto, um fármaco da lista de interações graves (Drugs.com) daquela estatina? Quais?
  4. Esses pares eram citados nas bulas brasileiras da estatina (padrão-ouro do estudo)?
Notificações espontâneas: não dão taxa nem risco; duplicatas tratadas por chave heurística (ver dedup()).
Uso: python vigimed_estatinas.py <pasta_com_os_3_csv>   (saídas em resultados/)"""
import json, os, re, sys, unicodedata

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))  # raiz do repositório
SAIDA = os.path.join(AQUI, "resultados"); os.makedirs(SAIDA, exist_ok=True)
PASTA = sys.argv[1]
sa = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()  # noqa: E731
ESTATINAS = ["atorvastatina", "rosuvastatina", "sinvastatina", "pravastatina", "pitavastatina", "fluvastatina", "lovastatina", "cerivastatina"]
MUSC = re.compile(r"rabdomi|miopat|miosit|mialg|creatin\w* (fosfo)?quinase|cpk|creatinofosfoquinase|necrose muscular|fraqueza muscular|"
                  r"dor muscular|lesao muscular|mioglobin")
RABDO = re.compile(r"rabdomi")


def ler(nome, cols=None):
    return pd.read_csv(os.path.join(PASTA, nome), sep=";", encoding="cp1252", dtype=str, usecols=cols, on_bad_lines="skip").fillna("")


med = ler("VigiMed_Medicamentos.csv", ["IDENTIFICACAO_NOTIFICACAO", "RELACAO_MEDICAMENTO_EVENTO", "NOME_MEDICAMENTO_WHODRUG",
                                       "PRINCIPIOS_ATIVOS_WHODRUG", "CODIGO_ATC"])
med.columns = ["id", "papel", "nome", "pa", "atc"]
med["pa_n"] = med["pa"].map(sa) + " | " + med["nome"].map(sa)
# nomes em português e em inglês (WHODrug traz alguns como "atorvastatin calcium", "pravastatin")
_RXE = re.compile(r"(ator|rosu|sin|sim|pra|pita|flu|lo|ceri)vastatin")
def _est(s):
    m_ = _RXE.search(s)
    return "" if not m_ else ("sin" if m_.group(1) in ("sin", "sim") else m_.group(1)) + "vastatina"
med["estatina"] = med["pa_n"].map(_est)
CORPUS = {"atorvastatina", "rosuvastatina", "sinvastatina", "pravastatina", "pitavastatina"}  # só as estatinas do corpus de bulas
med.loc[~med["estatina"].isin(CORPUS) & (med["estatina"] != ""), "estatina"] = "fora_do_corpus"
med = med[~med["id"].isin(set(med.loc[med["estatina"] == "fora_do_corpus", "id"]) - set(med.loc[med["estatina"].isin(CORPUS), "id"]))]
med.loc[med["estatina"] == "fora_do_corpus", "estatina"] = ""
noti = ler("VigiMed_Notificacoes.csv")
noti = noti.rename(columns={noti.columns[0]: noti.columns[0].lstrip("#﻿")})
reac = ler("VigiMed_Reacoes.csv")
reac = reac.rename(columns={reac.columns[0]: "id"})
reac["pt_n"] = reac["PT"].map(sa) + " | " + reac["REACAO_EVTO_ADVERSO_MEDDRA_LLT"].map(sa)

_dt = pd.to_datetime(noti["DATA_INCLUSAO_SISTEMA"].str[:10], format="%m/%d/%Y", errors="coerce")
periodo = (str(_dt.min().date()), str(_dt.max().date()))
total_base = int(noti.loc[noti["IDENTIFICACAO_NOTIFICACAO"].str.startswith("BR-"), "IDENTIFICACAO_NOTIFICACAO"].nunique())  # linhas sem ID = quebras de linha dentro de campos do CSV
papeis = med["papel"].value_counts().to_dict()

# --- notificações com estatina suspeita ou em interação
# A = estatina suspeita/em interação; B = estatina administrada em qualquer papel (inclui concomitante: em interações o notificador
# costuma marcar como suspeito só o fármaco novo, p.ex. daptomicina, e deixar a estatina como concomitante)
est_rows = med[(med["estatina"] != "") & (med["papel"] != "Medicamento não administrado")]
ids_A0 = set(est_rows[est_rows["papel"].isin(["Suspeito", "Interação"])]["id"])
ids_est = set(est_rows["id"])
N = noti[noti["IDENTIFICACAO_NOTIFICACAO"].isin(ids_est)].copy()
N["id"] = N["IDENTIFICACAO_NOTIFICACAO"]

# --- deduplicação heurística: mesmo sexo, idade, data de início, conjunto de princípios ativos e de termos PT
farm_set = med[med["id"].isin(ids_est)].groupby("id")["pa_n"].apply(lambda s: "|".join(sorted(set(s))))
pt_set = reac[reac["id"].isin(ids_est)].groupby("id")["PT"].apply(lambda s: "|".join(sorted(set(s))))
N["k_farm"] = N["id"].map(farm_set).fillna(""); N["k_pt"] = N["id"].map(pt_set).fillna("")
chave = ["SEXO", "IDADE_MOMENTO_REACAO", "DATA_INICIO_HORA", "k_farm", "k_pt"]
N["dup"] = N.duplicated(subset=[c for c in chave if c in N.columns], keep="first")
n_bruto = len(N); N = N[~N["dup"]]
ids = set(N["id"])  # B
idsA = ids & ids_A0

# --- referência (Drugs.com, major) e padrão-ouro das bulas
ref = pd.read_csv(os.path.join(RAIZ, "dados", "interacoes_graves_referencia.csv"), sep=";", encoding="utf-8-sig", dtype=str)
sys.path.insert(0, os.path.join(RAIZ, "estudo"))
from regras import DCB  # noqa: E402
radical = {pt: rad for _, (pt, rad) in DCB.items()}


def rx_de(dcb):
    r = radical.get(dcb) or re.sub(r"[aeo]$", "", sa(dcb))
    return re.compile(r"(?<![a-z])" + re.escape(sa(r)))


ref["rx"] = ref["farmaco_dcb"].map(rx_de)
g = pd.read_csv(os.path.join(RAIZ, "dados", "classificacao_revisada.csv"), sep=";", encoding="utf-8-sig", dtype=str).fillna("")  # 92 bulas
cob = g.assign(cit=g["citacao"] != "nao citada", nom=g["citacao"] == "nominal").groupby(["estatina", "farmaco_dcb"]).agg(
    bulas=("id_bula", "nunique"), citam=("cit", "sum"), nominal=("nom", "sum"),
    manejo=("manejo", lambda s: s[s != "nao se aplica"].mode().iloc[0] if (s != "nao se aplica").any() else "")).reset_index()

# --- por notificação
M = med[med["id"].isin(ids)]
R = reac[reac["id"].isin(ids)]
musc_ids = set(R[R["pt_n"].str.contains(MUSC)]["id"]); rabdo_ids = set(R[R["pt_n"].str.contains(RABDO)]["id"])
inter_ids = set(M[M["papel"] == "Interação"]["id"]) | set(R[R["pt_n"].str.contains(r"interacao (medicamentosa|entre medicamentos|droga)")]["id"])
grave_ids = set(N[N["GRAVE"].map(sa).str.startswith("sim")]["id"])
est_de = est_rows[est_rows["id"].isin(ids)].groupby("id")["estatina"].apply(lambda s: sorted(set(s)))

pares = []
_vazio = M.iloc[0:0]
outros_de = {k: v for k, v in M[M["estatina"] == ""].groupby("id")}
for nid, ests in est_de.items():
    outros = outros_de.get(nid, _vazio)
    for e in ests:
        for _, r in ref[ref["estatina"] == e].iterrows():
            hit = outros[outros["pa_n"].str.contains(r["rx"])]
            if len(hit):
                pares.append({"id": nid, "estatina": e, "farmaco_dcb": r["farmaco_dcb"], "papel_interagente": "|".join(sorted(set(hit["papel"]))),
                              "grave": nid in grave_ids, "muscular": nid in musc_ids, "rabdomiolise": nid in rabdo_ids,
                              "interacao_codificada": nid in inter_ids})
P = pd.DataFrame(pares)
if len(P):
    P = P.merge(cob, on=["estatina", "farmaco_dcb"], how="left")
    P["citado_bulas"] = P.apply(lambda r: "todas" if r["citam"] == r["bulas"] else ("nenhuma" if r["citam"] == 0 else "algumas"), axis=1)
ids_par = set(P["id"]) if len(P) else set()


def pct(a, b):
    return round(100 * a / b, 1) if b else None


por_est = {}
for e in ESTATINAS:
    ie = {i for i, v in est_de.items() if e in v}
    if not ie:
        continue
    por_est[e] = {"notificacoes_qualquer_papel": len(ie), "notificacoes_suspeita": len(ie & idsA), "graves": len(ie & grave_ids), "musculares": len(ie & musc_ids), "rabdomiolise": len(ie & rabdo_ids),
                  "com_par_grave": len(ie & set(P[P["estatina"] == e]["id"])) if len(P) else 0}
def resumo(S):
    return {"notificacoes": len(S), "graves": len(S & grave_ids), "graves_pct": pct(len(S & grave_ids), len(S)),
            "eventos_musculares": len(S & musc_ids), "eventos_musculares_pct": pct(len(S & musc_ids), len(S)),
            "rabdomiolise": len(S & rabdo_ids), "rabdomiolise_pct": pct(len(S & rabdo_ids), len(S)),
            "interacao_codificada": len(S & inter_ids), "interacao_codificada_pct": pct(len(S & inter_ids), len(S)),
            "com_farmaco_de_interacao_grave": len(S & ids_par), "com_farmaco_de_interacao_grave_pct": pct(len(S & ids_par), len(S)),
            "graves_com_par_pct": pct(len(S & ids_par & grave_ids), len(S & grave_ids)),
            "musculares_com_par": len(S & ids_par & musc_ids), "musculares_com_par_pct": pct(len(S & ids_par & musc_ids), len(S & musc_ids)),
            "rabdo_com_par": len(S & ids_par & rabdo_ids), "rabdo_com_par_pct": pct(len(S & ids_par & rabdo_ids), len(S & rabdo_ids))}


out = {"fonte": "Anvisa, dados abertos VigiMed (VigiMed_Notificacoes/Medicamentos/Reacoes.csv)", "periodo_inclusao_no_sistema": periodo, "notificacoes_na_base": total_base,
       "papeis_medicamento_base": papeis, "notificacoes_estatina_bruto": n_bruto, "duplicatas_removidas": int(n_bruto - len(ids)),
       "A_estatina_suspeita_ou_interacao": resumo(idsA), "B_estatina_qualquer_papel": resumo(ids),
       "por_estatina": por_est}
if len(P):
    top = P.groupby(["estatina", "farmaco_dcb"]).agg(notificacoes=("id", "nunique"), graves=("grave", "sum"), musculares=("muscular", "sum"),
                                                     rabdomiolise=("rabdomiolise", "sum"), bulas=("bulas", "first"), citam=("citam", "first"),
                                                     nominal=("nominal", "first"), manejo=("manejo", "first")).reset_index()
    top = top.sort_values("notificacoes", ascending=False)
    top.to_csv(os.path.join(SAIDA, "vigimed_pares_graves.csv"), sep=";", index=False, encoding="utf-8-sig")
    P.to_csv(os.path.join(SAIDA, "vigimed_pares_por_notificacao.csv"), sep=";", index=False, encoding="utf-8-sig")
    n1 = P.drop_duplicates(["id", "estatina", "farmaco_dcb"])
    out["pares_notificados"] = len(n1)
    out["pares_por_citacao_nas_bulas"] = n1["citado_bulas"].value_counts().to_dict()
    out["pares_por_manejo_nas_bulas"] = n1["manejo"].value_counts().to_dict()
json.dump(out, open(os.path.join(SAIDA, "vigimed_resumo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
if len(P):
    print(top.head(30).to_string())
