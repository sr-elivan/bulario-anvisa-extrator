"""Integridade dos dados congelados e, se houver PDFs (variável BULARIO_PDFS), reprodução completa do estudo."""
import json
import os
import subprocess
import sys

import pandas as pd
import pytest
from amostra import sortear

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(RAIZ, "dados")


def ler(n):
    return pd.read_csv(os.path.join(D, n), sep=";", encoding="utf-8-sig", dtype=str).fillna("")


def test_corpus_consistente_com_registros():
    reg, cor, exc = ler("registros_estatinas.csv"), ler("corpus_bulas.csv"), ler("exclusoes_sem_bula.csv")
    ativos = set(reg[(reg.situacao == "Ativo") & (reg.associacao != "True")].registro)
    no = set(cor[cor.no_corpus == "Sim"].registro_ms)
    assert len(ativos) == 102 and len(no) == 92 and len(set(exc.registro)) == 10
    sim = cor[cor.no_corpus == "Sim"]
    assert sim.lote.value_counts().to_dict() == {"1": 85, "2": 7}  # lote 2: incluído em 14/11/2026
    assert no | set(exc.registro) == ativos and not (no & set(exc.registro))
    assert cor[cor.no_corpus == "Sim"].sha1.str.fullmatch(r"[0-9a-f]{40}").all()


def test_referencia_consistente_com_drugscom():
    p = os.path.join(D, "drugscom_major_2026-11-13.json")
    if not os.path.exists(p):
        pytest.skip("lista bruta do Drugs.com fora do repositório do GitHub (está no pacote do Zenodo)")
    ref = ler("interacoes_graves_referencia.csv")
    js = json.load(open(os.path.join(D, "drugscom_major_2026-11-13.json"), encoding="utf-8"))["dados"]
    n = {k: len([x for x in v["major"] if x not in ("liver disease", "renal dysfunction")]) for k, v in js.items()}
    assert ref.groupby("estatina").size().to_dict() == {
        "atorvastatina": n["atorvastatin"], "fluvastatina": n["fluvastatin"], "lovastatina": n["lovastatin"],
        "pitavastatina": n["pitavastatin"], "pravastatina": n["pravastatin"], "rosuvastatina": n["rosuvastatin"],
        "sinvastatina": n["simvastatin"]}


def test_amostra_reproduzivel():
    cor = ler("corpus_bulas.csv")
    am = sortear(cor[cor.no_corpus == "Sim"])
    ref = ler("amostra_validacao.csv")
    assert am.registro_ms.tolist() == ref.registro_ms.tolist() and am.id_bula.tolist() == ref.id_bula.tolist()


@pytest.mark.skipif(not os.environ.get("BULARIO_PDFS"), reason="defina BULARIO_PDFS com a pasta das bulas para o teste completo")
@pytest.mark.parametrize("motor", ["v2", "v1"])
def test_reproducao_completa(tmp_path, motor):
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "reproduzir_estudo.py"), "--pdfs", os.environ["BULARIO_PDFS"],
                        "--saida", str(tmp_path), "--motor", motor], capture_output=True, text=True, encoding="utf-8")
    assert "IDÊNTICO" in r.stdout, r.stdout + r.stderr


def test_reproducao_a_partir_da_tabela_de_pares(tmp_path):
    """nível 1 (sem PDFs): as estatísticas recalculadas da tabela de pares congelada são as publicadas"""
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "reproduzir_estudo.py"), "--tabela", os.path.join(D, "preclassificacao_v02.csv"),
                        "--saida", str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert "IDÊNTICO" in r.stdout, r.stdout + r.stderr


def test_tabela_de_pares_consistente_com_corpus():
    pc, cor, ref = ler("preclassificacao_v02.csv"), ler("corpus_bulas.csv"), ler("interacoes_graves_referencia.csv")
    sim = cor[cor.no_corpus == "Sim"]
    assert set(pc.registro_ms) == set(sim.registro_ms) and pc.id_bula.nunique() == len(sim) == 92
    esperado = sum(int((ref.estatina == e).sum()) for e in sim.estatina)
    assert len(pc) == esperado == 4211 and not pc.duplicated(["registro_ms", "farmaco_dcb"]).any()


def test_classificacao_revisada_consistente():
    """a tabela revisada tem os mesmos pares da pré-classificação, todos conferidos, e só as alterações declaradas"""
    pc, rv = ler("preclassificacao_v02.csv"), ler("classificacao_revisada.csv")
    assert list(zip(pc.registro_ms, pc.farmaco_dcb)) == list(zip(rv.registro_ms, rv.farmaco_dcb))
    validos = {"lida", "texto idêntico ao de bula já lida", "ausência verificada no texto"}
    assert set(rv.conferencia) <= validos
    assert all(a == "Não" or a.startswith(("Sim: ", "Superada pela auditoria")) for a in rv.alterado_no_consenso)
    assert all(a == "Não" or a.startswith("Sim: ") for a in rv.alterado_na_auditoria)
    aud = ler(os.path.join("auditoria", "correcoes_auditoria.csv"))
    pontual = set(zip(aud.id_bula, aud.farmaco_dcb))
    for c in ("citacao", "classe_citada", "local", "manejo"):
        mud = pc[c] != rv[c]
        # toda diferença em relação ao motor vem declarada: revisão do avaliador 1, consenso ou correção pontual da auditoria
        assert all(c in a or (c in b and b.startswith("Sim")) or (i, f) in pontual
                   for a, b, i, f in zip(rv.alterado_na_revisao[mud], rv.alterado_no_consenso[mud], rv.id_bula[mud], rv.farmaco_dcb[mud])), c


def test_reproducao_com_classificacao_revisada(tmp_path):
    """nível 1 com a tabela revisada: as estatísticas são as de estatisticas_revisadas.json"""
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "reproduzir_estudo.py"), "--tabela", os.path.join(D, "preclassificacao_v02.csv"),
                        "--classificacao", os.path.join(D, "classificacao_revisada.csv"), "--saida", str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8")
    assert "estatisticas_revisadas.json: IDÊNTICO" in r.stdout, r.stdout + r.stderr
