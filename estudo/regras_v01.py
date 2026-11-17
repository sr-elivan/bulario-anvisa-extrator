#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""regras_v01.py - regras CONGELADAS do motor v1 (preclassificar.py, versão 0.1.0), mantidas só para reproduzir aquela versão.
O motor v2 (classificar.py) lê as regras dos arquivos de configuração (pasta configuracao/) por meio de regras.py."""
import re

from regras import DCB, rx_farmaco, sa  # noqa: F401  (nomes dos fármacos vêm da configuração; iguais aos da versão 0.1.0)

ORIENTADORAS = ("interacoes", "advertencias_precaucoes", "contraindicacoes", "posologia")


PI = ["atazanavir", "darunavir", "indinavir", "nelfinavir", "saquinavir", "tipranavir", "amprenavir", "fosamprenavir", "ritonavir"]
CYP3A4_POT = ["itraconazol", "cetoconazol", "posaconazol", "voriconazol", "levocetoconazol", "claritromicina", "telitromicina",
              "troleandomicina", "nefazodona", "cobicistate", "conivaptana", "idelalisibe", "boceprevir", "telaprevir", "mibefradil",
              "adagrasibe", "ceritinibe", "tucatinibe", "lonafarnibe", "ensitrelvir", "delavirdina"] + PI
CYP3A4_MOD = ["fluconazol", "eritromicina", "diltiazem", "verapamil", "dronedarona", "letermovir", "danazol", "amiodarona",
              "ranolazina", "mifepristona", "relacorilanto"]
# classe -> (regex no texto normalizado, membros DCB)
CLASSES = {
    "inibidores potentes do CYP3A4": (r"inibidor\w*\s+(?:potente|forte)s?\s+(?:da|do|de)?\s*(?:isoenzima\s+|enzima\s+)?(?:citocromo\s+)?(?:p450\s+)?(?:cyp\s?3a4|3a4)", CYP3A4_POT),
    "inibidores do CYP3A4": (r"inibidor\w*\s+(?:da|do|de)\s*(?:isoenzima\s+|enzima\s+)?(?:citocromo\s+)?(?:p450\s+)?(?:cyp\s?3a4|3a4)", CYP3A4_POT + CYP3A4_MOD),
    "indutores do CYP3A4": (r"indutor\w*\s+(?:\w+\s+){0,2}(?:cyp\s?3a4|3a4)", ["rifampicina"]),
    "inibidores de protease (HIV/HCV)": (r"inibidor\w* d[ae]s? protease", PI + ["boceprevir", "telaprevir", "simeprevir"]),
    "antifúngicos azólicos": (r"antifung\w*\s+(?:do grupo\s+)?azo\w*|derivad\w* azol\w*|\bazois\b|\bazolicos\b", ["itraconazol", "cetoconazol", "fluconazol", "posaconazol", "voriconazol", "levocetoconazol", "oteseconazol"]),
    "macrolídeos": (r"macrolid\w*", ["claritromicina", "eritromicina", "telitromicina", "troleandomicina"]),
    "fibratos": (r"fibratos?\b|derivad\w* do acido fibrico", ["fenofibrato", "genfibrozila", "clofibrato", "ácido fenofíbrico"]),
    "bloqueadores dos canais de cálcio": (r"bloqueador\w* d\w* canai?s? de calcio", ["diltiazem", "verapamil", "anlodipino", "levanlodipino", "mibefradil"]),
    "inibidores da BCRP": (r"inibidor\w*\s+(?:da\s+|do\s+)?(?:proteina\s+)?(?:\w+\s+){0,2}bcrp", ["capmatinibe", "darolutamida", "febuxostate", "fostamatinibe", "regorafenibe", "enasidenibe", "tafamidis", "momelotinibe", "asciminibe", "ticagrelor", "ciclosporina"]),
    "inibidores do OATP1B1": (r"inibidor\w*\s+(?:da\s+|do\s+|dos\s+)?(?:transportador\w*\s+)?(?:\w+\s+){0,2}oatp\s?1b", ["ciclosporina", "clopidogrel", "rifampicina", "atazanavir", "darunavir", "ritonavir", "saquinavir", "letermovir", "eritromicina", "claritromicina"]),
    "niacina (doses hipolipemiantes)": (r"acido nicotinico|niacina", ["niacina (ácido nicotínico)"]),
}
MANEJO = [  # do mais restritivo para o menos
    ("contraindicar/evitar", r"contraindicad|contra-indicad|nao deve(?:m)? ser (?:usad|administrad|utilizad|prescrit|coadministrad|associad)|deve(?:m)? ser evitad|evitar|evite|nao (?:e|sao) recomendad|nao se recomenda|nao recomendad|suspend|interromp|descontinu"),
    ("limite de dose", r"nao (?:deve )?exceder|nao ultrapass|dose (?:maxima|diaria maxima)|nao deve(?:m)? ser superior|limit(?:ar|e|ad)\w* (?:a|de|da)? ?(?:dose)?|ajuste (?:de|da) dose|reduz\w* (?:a )?dose|dose (?:mais baixa|menor|inicial)|menor dose|iniciar com|nao mais que \d"),
    ("monitorar", r"monitor|acompanh|observ\w* (?:cuidadosamente|atentamente|quanto)|sinais (?:e|ou) sintomas|creatin\w*[ -]?(?:fosfo)?quinase|\bck\b|\bcpk\b|cautela|cuidado|precau|avaliar cuidadosamente|vigil"),
]


NEGA = r"ausencia de (?:uma )?interac|nao (?:tiveram|teve|houve|apresentou|apresentaram) (?:um |uma |nenhum |nenhuma )?(?:efeito|interac|alterac)|nao foi observad|nao foram observad|nao ha interac|sem interac|nao (?:altera|alterou|afeta|afetou)|nenhuma interac|nao interage"


def rx_farmaco(farm_en):
    """Regex do nome DCB do fármaco no texto normalizado. Só casa no INÍCIO de palavra: evita que
    'amprenavir' case dentro de 'fosamprenavir' (ou 'cetoconazol' em 'levocetoconazol')."""
    return re.compile(r"(?<![a-z])(?:" + sa(DCB[farm_en][1]) + ")")


def negado(tr):
    return bool(re.search(NEGA, tr))


def janela(t, m, antes=200, depois=420):
    return t[max(0, m.start() - antes):m.end() + depois]


def manejo_de(trechos):
    achados = [nome for nome, rx in MANEJO for tr in trechos if re.search(rx, tr)]
    for nome, _ in MANEJO:
        if nome in achados:
            return nome
    return "sem orientacao"
