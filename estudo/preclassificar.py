#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preclassificar.py - pré-classificação automática de cada par bula × interação grave (SUGESTÃO para revisão humana).

citação : nominal (nome DCB em qualquer seção) | classe (classe/mecanismo que inclui o fármaco, só em seções orientadoras:
          interações, advertências, contraindicações, posologia) | nao citada
local   : secao de interacoes | outra secao | ambas
manejo  : o mais restritivo no trecho: contraindicar/evitar > limite de dose > monitorar > sem orientacao
confiança: alta | média (classe, ou nome só em farmacologia) | baixa (a bula AFIRMA ausência de interação)"""
import re, sqlite3

from regras import DCB, rx_farmaco, sa  # noqa: E402
from regras_v01 import CLASSES, ORIENTADORAS, janela, manejo_de, negado


def preclassificar(db, bulas, referencia):
    """bulas: {bula_id: dict(registro_ms, estatina, categoria, produto, empresa)}; referencia: linhas do CSV de referência."""
    en_de = {v[0]: k for k, v in DCB.items()}
    con = sqlite3.connect(db)
    partes = {}
    # junta os subtítulos de cada seção na ordem de inserção (id), de forma determinística (sem depender de group_concat)
    for bid, chave, txt in con.execute("select bula_id, chave, texto from secoes order by bula_id, chave, id"):
        partes.setdefault(bid, {}).setdefault(chave, []).append(txt or "")
    secs = {bid: {k: re.sub(r"\s+", " ", sa(" ".join(v))) for k, v in d.items()} for bid, d in partes.items()}
    linhas = []
    for bid, b in bulas.items():
        S = secs.get(bid, {})
        for r in [x for x in referencia if x["estatina"] == b["estatina"]]:
            farm = r["farmaco_dcb"]
            rx = rx_farmaco(en_de[farm])
            ocorr = {k: list(rx.finditer(t)) for k, t in S.items()}
            ocorr = {k: v for k, v in ocorr.items() if v}
            cit, classe_usada, conf, evid = "nao citada", "", "", ""
            locais, trechos = set(ocorr), []
            contra = []
            if ocorr:
                cit = "nominal"
                orient = [k for k in ocorr if k in ORIENTADORAS]
                conf = "alta" if orient else "média (só em farmacologia/tabela; confira se é orientação)"
                for k in (orient or list(ocorr)):
                    for m in ocorr[k][:3]:
                        trechos.append(janela(S[k], m))
                    if k == "contraindicacoes":
                        contra.append(janela(S[k], m))
            else:
                for nome, (crx, membros) in CLASSES.items():
                    if farm not in membros:
                        continue
                    for k in ORIENTADORAS:
                        t = S.get(k, "")
                        ms = list(re.finditer(crx, t))
                        if ms:
                            cit, classe_usada, conf = "classe", nome, "média"
                            locais.add(k)
                            trechos += [janela(t, m) for m in ms[:3]]
                            if k == "contraindicacoes":
                                contra += [janela(t, m) for m in ms[:3]]
                    if cit == "classe":
                        break
            if cit == "nao citada":
                local, man = "", "nao se aplica"
            else:
                local = ("ambas" if "interacoes" in locais and len(locais) > 1 else
                         "secao de interacoes" if "interacoes" in locais else "outra secao")
                pos = [tr for tr in trechos if not negado(tr)]
                if trechos and not pos:
                    man, conf = "sem orientacao", "baixa: a bula AFIRMA AUSÊNCIA de interação/efeito; decida"
                else:
                    man = manejo_de(pos) if pos else "sem orientacao"
                    if any(not negado(tr) for tr in contra):  # citado na seção Contraindicações = contraindicar
                        man = "contraindicar/evitar"
                    if len(pos) < len(trechos):
                        conf = (conf + "; atenção: um dos trechos nega efeito").strip("; ")
                evid = ((pos or trechos or [""])[0])[:500]
            linhas.append({**b, "farmaco_dcb": farm, "registro_ativo_no_brasil": r["registro_ativo_no_brasil"],
                           "citacao": cit, "classe_citada": classe_usada, "local": local, "manejo": man,
                           "confianca": conf, "secoes": ", ".join(sorted(locais)), "evidencia": evid})
    return linhas
