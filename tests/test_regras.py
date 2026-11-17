"""Regras de classificação: radicais DCB, classes, manejo e negação."""
import re

import pytest
from identificar import RX_MS
from regras import DCB, rx_farmaco, sa
from regras_v01 import CLASSES, MANEJO, janela, manejo_de, negado


def test_cada_radical_encontra_o_proprio_nome_dcb():
    for en, (pt, rx) in DCB.items():
        assert re.search(sa(rx), sa(pt)), (en, pt, rx)
        assert rx_farmaco(en).search(sa(pt)), (en, pt)


@pytest.mark.parametrize("texto, farm, casa", [
    ("fosamprenavir 700mg/ritonavir 100mg", "amprenavir", False),   # bug encontrado na bula COLEMONO
    ("fosamprenavir 700mg/ritonavir 100mg", "fosamprenavir", True),
    ("uso com amprenavir", "amprenavir", True),
    ("lopinavir/ritonavir", "ritonavir", True),
    ("levocetoconazol", "ketoconazole", False),
    ("cetoconazol 200 mg", "ketoconazole", True),
    ("levanlodipino", "amlodipine", False),
])
def test_nome_so_no_inicio_da_palavra(texto, farm, casa):
    assert bool(rx_farmaco(farm).search(texto)) is casa


def test_nenhum_nome_dcb_casa_dentro_de_outro():
    for en in DCB:
        for en2, (pt2, _) in DCB.items():
            if en2 != en and rx_farmaco(en).search(sa(pt2)):
                # só é aceitável quando o outro nome CONTÉM o primeiro como palavra separada (ex.: "ácido fenofíbrico")
                assert re.search(r"(?<![a-z])" + re.escape(sa(DCB[en][0]).split()[0]), sa(pt2)), (en, en2)


def test_membros_das_classes_existem_no_dicionario_dcb():
    nomes = {pt for pt, _ in DCB.values()}
    for classe, (_, membros) in CLASSES.items():
        for m in membros:
            assert m in nomes, (classe, m)


@pytest.mark.parametrize("texto, classe", [
    ("uso concomitante com inibidores potentes do cyp3a4 (por exemplo", "inibidores potentes do CYP3A4"),
    ("inibidores do cyp3a4 podem aumentar", "inibidores do CYP3A4"),
    ("inibidores da protease do hiv", "inibidores de protease (HIV/HCV)"),
    ("antifungicos azolicos", "antifúngicos azólicos"),
    ("antibioticos macrolideos", "macrolídeos"),
    ("derivados do acido fibrico, incluindo", "fibratos"),
])
def test_regex_de_classe(texto, classe):
    assert re.search(CLASSES[classe][0], texto)


def test_classe_vaga_nao_conta():
    for crx, _ in CLASSES.values():
        assert not re.search(crx, "outros medicamentos metabolizados pelo figado")


@pytest.mark.parametrize("trecho, esperado", [
    ("o uso concomitante e contraindicado", "contraindicar/evitar"),
    ("a administracao concomitante deve ser evitada", "contraindicar/evitar"),
    ("nao exceder 10 mg de sinvastatina", "limite de dose"),
    ("recomenda-se reduzir a dose", "limite de dose"),
    ("monitorar os niveis de ck", "monitorar"),
    ("pode aumentar a concentracao plasmatica", "sem orientacao"),
])
def test_manejo(trecho, esperado):
    assert manejo_de([trecho]) == esperado


def test_manejo_escolhe_o_mais_restritivo():
    assert manejo_de(["monitorar ck", "nao exceder 20 mg", "e contraindicado"]) == "contraindicar/evitar"
    assert [n for n, _ in MANEJO] == ["contraindicar/evitar", "limite de dose", "monitorar"]


@pytest.mark.parametrize("trecho, neg", [
    ("o fluconazol nao teve efeito clinicamente significativo", True),
    ("foi demonstrada a ausencia de uma interacao farmacocinetica", True),
    ("a claritromicina aumenta a exposicao", False),
])
def test_negacao(trecho, neg):
    assert negado(trecho) is neg


def test_janela_limites():
    t = "a" * 1000 + "ALVO" + "b" * 1000
    m = re.search("ALVO", t)
    j = janela(t, m)
    assert j.startswith("a") and "ALVO" in j and len(j) == 200 + 4 + 420


@pytest.mark.parametrize("texto, registro", [
    ("Reg. M.S.: 1.0047. 0543", "100470543"),
    ("MS - 1.0573.0738", "105730738"),
    ("Registro: 1.4107. 0657", "141070657"),
    ("M.S. nº 1.0235.1255", "102351255"),
    ("Registro MS 1.2345.6789", "123456789"),
])
def test_leitura_do_registro_ms(texto, registro):
    m = RX_MS.search(texto)
    assert m and re.sub(r"\D", "", m.group(1))[:9] == registro
