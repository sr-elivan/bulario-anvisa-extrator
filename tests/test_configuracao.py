"""Configuração do motor v2 (pasta configuracao/): carrega exatamente as regras do estudo, aceita planilha .xlsx,
recusa configurações inválidas com mensagem clara e muda o comportamento do motor quando alterada."""
import csv
import json
import os
import shutil
import subprocess
import sys

import pytest
import regras
from regras import ErroConfiguracao, carregar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RAIZ, "configuracao")
FERR = os.path.join(RAIZ, "ferramentas", "configuracao_planilha.py")
V2 = ["ALIASES", "ANAFORA_V2", "BCRP_V2", "CLASSES_V2", "DCB", "DOSE_CONDICIONAL_V2", "EQUIVALENTE", "EST", "EXCECAO_V2", "MANEJO_V2",
      "NAO_FARMACO", "NEGA_PARCIAL_V2", "NEGA_V2", "OATP_V2", "ORIENT_TRANSP_V2", "PARAGRAFO_TRANSP_V2", "SEM_AJUSTE_V2",
      "SUBPOPULACAO_V2", "TABELA_FIM_V2", "TABELA_INICIO_V2", "TABELA_REGRA_V2"]


def _json(v):
    if isinstance(v, dict):
        return {str(k): _json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json(x) for x in v]
    if isinstance(v, set):
        return sorted(v)
    return v


def test_configuracao_reproduz_as_regras_do_estudo():
    """as regras lidas dos CSV são as do estudo (fotografia após a auditoria pré-publicação de 16/11/2026; a anterior está em
    fixtures/regras_v02_referencia_antes_auditoria.json)"""
    ref = json.load(open(os.path.join(RAIZ, "tests", "fixtures", "regras_v02_referencia.json"), encoding="utf-8"))
    c = carregar(CONFIG)
    for k in V2:
        assert _json(c[k]) == ref[k], k


def test_planilha_xlsx_equivale_aos_csv(tmp_path):
    x = tmp_path / "config.xlsx"
    subprocess.run([sys.executable, FERR, "--para-xlsx", CONFIG, str(x)], check=True, capture_output=True)
    a, b = carregar(CONFIG), carregar(str(x))
    assert all(_json(a[k]) == _json(b[k]) for k in V2)
    volta = tmp_path / "volta"
    subprocess.run([sys.executable, FERR, "--para-csv", str(x), str(volta)], check=True, capture_output=True)
    c = carregar(str(volta))
    assert all(_json(a[k]) == _json(c[k]) for k in V2)


def _copia(tmp_path):
    d = tmp_path / "cfg"
    shutil.copytree(CONFIG, d)
    return d


def _editar(arquivo, f):
    with open(arquivo, encoding="utf-8-sig", newline="") as fh:
        linhas = list(csv.reader(fh, delimiter=";"))
    linhas = f(linhas)
    with open(arquivo, "w", encoding="utf-8-sig", newline="") as fh:
        csv.writer(fh, delimiter=";", lineterminator="\n").writerows(linhas)


def test_membro_inexistente_e_recusado(tmp_path):
    d = _copia(tmp_path)
    _editar(d / "classes.csv", lambda L: [L[0], [L[1][0], L[1][1], L[1][2], L[1][3], L[1][4] + " | farmacoinexistente", L[1][5]], *L[2:]])
    with pytest.raises(ErroConfiguracao, match="farmacoinexistente"):
        carregar(str(d))


def test_expressao_invalida_e_recusada(tmp_path):
    d = _copia(tmp_path)
    _editar(d / "expressoes.csv", lambda L: [L[0], [L[1][0], L[1][1], "contraindicad(", L[1][3]], *L[2:]])
    with pytest.raises(ErroConfiguracao, match="expressoes, linha 2"):
        carregar(str(d))


def test_regra_obrigatoria_faltando_e_recusada(tmp_path):
    d = _copia(tmp_path)
    _editar(d / "expressoes.csv", lambda L: [r for r in L if r[0] != "anafora"])
    with pytest.raises(ErroConfiguracao, match="anafora"):
        carregar(str(d))


def test_arquivo_faltando_e_recusado(tmp_path):
    d = _copia(tmp_path)
    os.remove(d / "farmacos.csv")
    with pytest.raises(ErroConfiguracao, match="farmacos.csv"):
        carregar(str(d))


def test_configuracao_alterada_muda_o_motor(tmp_path):
    """sem a classe 'macrolídeos', uma frase que só cita a classe deixa de citar a eritromicina (BULARIO_CONFIG)"""
    d = _copia(tmp_path)
    _editar(d / "classes.csv", lambda L: [r for r in L if r[1] != "macrolídeos"])
    prog = ("from classificar import classificar_bula; "
            "r = classificar_bula({'interacoes': 'Evitar o uso com macrolideos.'}, [('eritromicina', 'erythromycin')]); "
            "print(r['eritromicina']['citacao'])")
    env = {**os.environ, "PYTHONPATH": os.path.join(RAIZ, "estudo")}
    padrao = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, env=env, check=True).stdout.strip()
    env["BULARIO_CONFIG"] = str(d)
    alterado = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, env=env, check=True).stdout.strip()
    assert padrao == "classe" and alterado == "nao citada"


def test_modulo_usa_a_configuracao_padrao():
    assert os.path.normpath(regras.ORIGEM) == os.path.normpath(CONFIG) or os.environ.get("BULARIO_CONFIG")
