"""Separação de seções: erros achados na auditoria pré-publicação (16/11/2026)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bulario"))
import texto as T  # noqa: E402

BULA = """II - INFORMAÇÕES TÉCNICAS AOS PROFISSIONAIS DE SAÚDE
1. INDICAÇÕES
Texto.
3. CARACTERÍSTICAS FARMACOLÓGICAS
Texto.
4. CONTRAINDICAÇÕES
Texto.
{adv}
Miopatia.
Interações medicamentosas
O risco de miopatia é aumentado com fibratos (dose máxima de 10 mg).
Gravidez e lactação.
6. INTERAÇÕES MEDICAMENTOSAS
Múltiplos mecanismos.
8. POSOLOGIA E MODO DE USAR
Texto.
9. REAÇÕES ADVERSAS
Texto.
10. SUPERDOSE
Texto.
7. CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO
Texto.
"""


def test_subtitulo_sem_numero_nao_abre_secao():
    s = T.separar_secoes(BULA.format(adv="5. ADVERTÊNCIAS E PRECAUÇÕES"))[0]
    assert "Gravidez" in s["advertencias_precaucoes"] and "fibratos" in s["advertencias_precaucoes"]
    assert s["interacoes"].startswith("Múltiplos mecanismos") and "Gravidez" not in s["interacoes"]


def test_titulo_sem_espaco_ou_partido():
    for adv in ("5.ADVERTÊNCIAS E PRECAUÇÕES", "5. ADVERTÊNCIAS        E"):
        s = T.separar_secoes(BULA.format(adv=adv))[0]
        assert "advertencias_precaucoes" in s and "Miopatia" in s["advertencias_precaucoes"], adv
        assert "Miopatia" not in s["contraindicacoes"]
