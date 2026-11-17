"""Motor v0.2 (classificar.py): cada regra do livro de códigos com um trecho real das bulas."""
import pytest
from classificar import _cues, classificar_bula, frases

REF_SINV = [("fenofibrato", "fenofibrate"), ("ácido fenofíbrico", "fenofibric acid"), ("clofibrato", "clofibrate"), ("genfibrozila", "gemfibrozil"),
            ("lomitapida", "lomitapide"), ("niacina (ácido nicotínico)", "niacin"), ("fluconazol", "fluconazole"), ("teriflunomida", "teriflunomide"),
            ("anlodipino", "amlodipine"), ("levanlodipino", "levamlodipine"), ("colchicina", "colchicine")]


@pytest.mark.parametrize("frase, esperado", [
    ("A coadministração é contraindicada.", "C"),
    ("Deve-se evitar o uso concomitante.", "C"),
    ("A dose de sinvastatina não deve ser maior que 20 mg diários.", "L"),
    ("A dose dos substratos deve ser ajustada conforme necessário.", "L"),
    ("Deve-se ter cautela ao prescrever.", "M"),
    ("Os médicos devem avaliar cuidadosamente os benefícios.", "M"),
    ("O ticagrelor aumenta a ASC da rosuvastatina em 2,3 vezes.", "S"),
    ("Os seguintes medicamentos não tiveram um efeito clinicamente significativo: fenofibrato.", "N"),
    ("Não é necessário ajuste de dose quando coadministrado com indutores.", "N"),
    ("Embora nenhuma interação farmacocinética tenha sido observada, uma interação farmacodinâmica pode ocorrer.", "S"),
    ("A coadministração não é recomendada para pacientes asiáticos.", "M"),                      # subpopulação
    ("Em pacientes com HoFH, a administração concomitante da lomitapida com doses > 40 mg de sinvastatina.", "S"),  # (C forçado só na seção)
    ("O risco é maior (vide Advertências e Precauções).", "S"),                                   # remissão não é orientação
    ("Caso o uso concomitante seja inevitável, monitorar.", "C"),
    ("Foi relatada diminuição, acompanhada de convulsões.", "S"),
    ("Não há dados para avaliar a administração concomitante.", "S"),
])
def test_rotulo_da_frase(frase, esperado):
    assert _cues(frases(frase)[0]) == esperado


def test_frases_nao_quebra_em_referencia_a_item_e_separa_itens_em_minuscula():
    t = "Se for usada com fibratos diferente de genfibrozila (veja o item 4. CONTRAINDICAÇÕES) ou fenofibrato, a dose não deve ser maior do que 10 mg/dia. ticagrelor: aumenta a ASC."
    f = frases(t)
    assert len(f) == 2 and "ou fenofibrato" in f[0] and f[1].startswith("ticagrelor:")


def test_excecao_fenofibrato_e_equivalente():
    secs = {"posologia": "Se a sinvastatina for utilizada concomitantemente com fibratos diferente de genfibrozila (veja o item 4. CONTRAINDICAÇÕES) "
                         "ou fenofibrato, a dose de sinvastatina não deve ser maior do que 10 mg/dia.",
            "interacoes": "Deve-se ter cautela ao prescrever fenofibrato com sinvastatina."}
    r = classificar_bula(secs, REF_SINV)
    assert r["clofibrato"]["manejo"] == "limite de dose"
    assert r["fenofibrato"]["manejo"] == "monitorar"            # exceção: não herda o limite de 10 mg
    assert r["ácido fenofíbrico"]["manejo"] == "monitorar"      # segue o fenofibrato
    assert r["genfibrozila"]["citacao"] == "nominal" and r["genfibrozila"]["manejo"] == "sem orientacao"


def test_contraindicacao_condicionada_a_dose_e_limite():
    secs = {"contraindicacoes": "• Em pacientes com HoFH, a administração concomitante da lomitapida com doses > 40 mg de sinvastatina (veja o item 6."}
    assert classificar_bula(secs, REF_SINV)["lomitapida"]["manejo"] == "limite de dose"


def test_classe_moderada_bcpr_e_titulo():
    secs = {"interacoes": "Quando for coadministrado sinvastatina com um inibidor moderado de CYP3A4, um ajuste da dose de sinvastatina pode ser necessário. "
                          "Quando a sinvastatina e um inibidor da BCPR forem coadministrados, um ajuste da dose de sinvastatina poderá ser necessário. "
                          "- Bloqueadores do canal de cálcio - Verapamil ou diltiazem: A dose de sinvastatina não deve ser maior que 20 mg diários."}
    r = classificar_bula(secs, REF_SINV)
    assert (r["fluconazol"]["citacao"], r["fluconazol"]["manejo"]) == ("classe", "limite de dose")
    assert (r["teriflunomida"]["citacao"], r["teriflunomida"]["manejo"]) == ("classe", "limite de dose")   # "BCPR" = grafia da bula
    assert (r["levanlodipino"]["citacao"], r["levanlodipino"]["manejo"]) == ("classe", "sem orientacao")   # classe como título


def test_anafora_na_frase_seguinte():
    secs = {"interacoes": "Colchicina: houve relatos de miopatia com a administração concomitante de colchicina e sinvastatina. "
                          "Aconselha-se o monitoramento de pacientes que tomam esta combinação."}
    assert classificar_bula(secs, REF_SINV)["colchicina"]["manejo"] == "monitorar"



def test_anafora_inicio_de_frase():
    """frase seguinte que começa retomando a anterior ("Por isso, ...") herda a orientação (regra anafora, 1ª alternativa)"""
    secs = {"interacoes": "O diltiazem aumentou a exposição à sinvastatina. Por isso, a dose de sinvastatina não deve exceder 10 mg."}
    assert classificar_bula(secs, [("diltiazem", "diltiazem")])["diltiazem"]["manejo"] == "limite de dose"

def test_combinacao_nao_transfere_restricao():
    ref = [("letermovir", "letermovir"), ("ciclosporina", "cyclosporine")]
    secs = {"interacoes": "O uso de atorvastatina não é recomendado em pacientes que tomam letermovir coadministrado com ciclosporina."}
    r = classificar_bula(secs, ref)
    assert r["letermovir"]["manejo"] == r["ciclosporina"]["manejo"] == "sem orientacao"


def test_tabela_com_regra_de_ajuste_e_negacao_especifica():
    ref = [("regorafenibe", "regorafenib"), ("clopidogrel", "clopidogrel"), ("fenofibrato", "fenofibrate")]
    secs = {"interacoes": "Se for observado que o medicamento aumenta a ASC da rosuvastatina em aproximadamente 2 vezes ou mais, a dose inicial de "
                          "rosuvastatina não deve exceder 5 mg uma vez ao dia. Tabela 4. Efeito da coadministração de medicamentos sobre a exposição. "
                          "Esquema posológico regorafenibe 160 mg 3,8 vezes clopidogrel 300 mg 2 vezes. "
                          "Os seguintes medicamentos não tiveram um efeito clinicamente significativo: fenofibrato 67 mg. "
                          "A modelagem (PBPK) prevê que não há interação medicamentosa clinicamente relevante entre o clopidogrel e a rosuvastatina."}
    r = classificar_bula(secs, ref)
    assert r["regorafenibe"]["manejo"] == "limite de dose"
    assert r["clopidogrel"]["manejo"] == "sem orientacao"       # a bula nega a relevância para ESTE fármaco
    assert r["fenofibrato"]["manejo"] == "sem orientacao"


def test_grafia_errada_bocepravir_conta_como_nominal():
    secs = {"posologia": "... inibidores de protease da hepatite C (HCV) (bocepravir), claritromicina e itraconazol. "
                         "Deve-se ter precaução na coadministração de atorvastatina e estes medicamentos, e é recomendada avaliação clínica "
                         "apropriada para garantir que a menor dose necessária de atorvastatina seja empregada."}
    r = classificar_bula(secs, [("boceprevir", "boceprevir")])
    assert (r["boceprevir"]["citacao"], r["boceprevir"]["manejo"]) == ("nominal", "limite de dose")
