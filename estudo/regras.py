#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""regras.py - carrega as regras do motor v2 a partir dos ARQUIVOS DE CONFIGURAÇÃO (nada de vocabulário escrito no código).

Origem da configuração, nesta ordem:
  1. variável de ambiente BULARIO_CONFIG (pasta com os .csv ou uma planilha .xlsx com as mesmas abas);
  2. a pasta configuracao/ do pacote (configuração usada no estudo das estatinas).

Arquivos (CSV com ";" e UTF-8; ver configuracao/LEIA-ME.md):
  alvos.csv               fármacos-alvo (no estudo, as estatinas): nome_en; dcb
  referencia_ignorar.csv  termos da base de referência que não são fármacos (ex.: interação com doença)
  farmacos.csv            fármacos interagentes: nome_en; dcb; busca_no_texto; grafias_alternativas; equivalente_a; fonte
  classes.csv             classes/mecanismos: ordem; classe; alternativa; expressao_no_texto; membros_dcb; fonte
  expressoes.csv          expressões de manejo, negação, exceção, anáfora e tabelas: regra; alternativa; expressao; descricao
Expressões com várias alternativas ocupam uma linha cada; o motor as junta com "|" (expressão regular), na ordem da coluna
"alternativa". O texto da bula é comparado em minúsculas e sem acentos."""
import csv, os, re, unicodedata

PADRAO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configuracao")
ARQUIVOS = ("alvos", "referencia_ignorar", "farmacos", "classes", "expressoes")
REGRAS_OBRIGATORIAS = ("manejo_contraindicar", "manejo_limite_dose", "manejo_monitorar", "sem_ajuste", "nega_interacao", "nega_parcial",
                       "dose_condicional", "subpopulacao", "excecao", "anafora", "paragrafo_transportadores",
                       "orientacao_transportadores", "tabela_regra", "tabela_inicio", "tabela_fim")
# classes a que o código se refere pelo nome (a expressão "inibidores destas proteínas transportadoras" usa as duas listas)
CLASSE_OATP, CLASSE_BCRP = "inibidores do OATP1B1", "inibidores da BCRP"


class ErroConfiguracao(ValueError):
    pass


def sa(s):
    """minúsculo e sem acento (forma em que o texto da bula é comparado)"""
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def _ler_tabelas(origem):
    if origem.lower().endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(origem, read_only=True, data_only=True)
        tabs = {}
        for nome in ARQUIVOS:
            if nome not in wb.sheetnames:
                raise ErroConfiguracao(f"{origem}: falta a aba '{nome}'")
            cab, *linhas = [["" if v is None else str(v).strip() for v in r] for r in wb[nome].iter_rows(values_only=True)]
            tabs[nome] = [dict(zip(cab, r)) for r in linhas if any(r)]
        return tabs
    tabs = {}
    for nome in ARQUIVOS:
        p = os.path.join(origem, nome + ".csv")
        if not os.path.exists(p):
            raise ErroConfiguracao(f"arquivo de configuração não encontrado: {p}")
        with open(p, encoding="utf-8-sig", newline="") as fh:
            tabs[nome] = [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(fh, delimiter=";") if any((v or "").strip() for v in r.values())]
    return tabs


def _regex(texto, onde):
    try:
        re.compile(texto)
    except re.error as e:
        raise ErroConfiguracao(f"{onde}: expressão inválida '{texto}': {e}") from None
    return texto


def _juntar(linhas, chave, onde):
    """agrupa as alternativas de cada regra/classe (na ordem da coluna 'alternativa') e as une com '|'"""
    grupos = {}
    for i, r in enumerate(linhas, 2):
        try:
            alt = int(r.get("alternativa") or 1)
        except ValueError:
            raise ErroConfiguracao(f"{onde}, linha {i}: 'alternativa' deve ser um número") from None
        if not r.get(chave):
            raise ErroConfiguracao(f"{onde}, linha {i}: coluna '{chave}' vazia")
        grupos.setdefault(r[chave], []).append((alt, i, r))
    return {k: sorted(v, key=lambda x: x[0]) for k, v in grupos.items()}


def carregar(origem=None):
    """lê e valida a configuração; devolve um dicionário com as regras prontas para o motor"""
    origem = origem or os.environ.get("BULARIO_CONFIG") or PADRAO
    t = _ler_tabelas(origem)
    c = {"ORIGEM": origem}
    c["EST"] = {r["nome_en"].lower(): r["dcb"] for r in t["alvos"]}
    if not c["EST"]:
        raise ErroConfiguracao("alvos: nenhum fármaco-alvo")
    c["NAO_FARMACO"] = {r["termo_en"].lower() for r in t["referencia_ignorar"]}

    dcb, alias, equi = {}, {}, {}
    for i, r in enumerate(t["farmacos"], 2):
        onde = f"farmacos, linha {i}"
        if not (r.get("nome_en") and r.get("dcb") and r.get("busca_no_texto")):
            raise ErroConfiguracao(f"{onde}: nome_en, dcb e busca_no_texto são obrigatórios")
        if r["nome_en"] in dcb:
            raise ErroConfiguracao(f"{onde}: nome_en repetido ({r['nome_en']})")
        dcb[r["nome_en"]] = (r["dcb"], r["busca_no_texto"])
        _regex(sa(r["busca_no_texto"]), onde)
        if r.get("grafias_alternativas"):
            alias[r["dcb"]] = _regex(r["grafias_alternativas"], onde)
        if r.get("equivalente_a"):
            equi[r["dcb"]] = r["equivalente_a"]
    nomes = {v[0] for v in dcb.values()}
    if len(nomes) != len(dcb):
        raise ErroConfiguracao("farmacos: há DCB repetida")
    for d, e in equi.items():
        if e not in nomes:
            raise ErroConfiguracao(f"farmacos: '{d}' é equivalente a '{e}', que não está na lista")
    c.update(DCB=dcb, ALIASES=alias, EQUIVALENTE=equi)

    classes = []
    for nome, alts in _juntar(t["classes"], "classe", "classes").items():
        ordem = alts[0][2].get("ordem") or "0"
        membros = [m.strip() for m in alts[0][2].get("membros_dcb", "").split("|") if m.strip()]
        if not membros:
            raise ErroConfiguracao(f"classes, linha {alts[0][1]}: a classe '{nome}' não tem membros (coluna membros_dcb da 1ª alternativa)")
        fora = [m for m in membros if m not in nomes]
        if fora:
            raise ErroConfiguracao(f"classes, classe '{nome}': membros que não estão em farmacos.csv: {', '.join(fora)}")
        rx = "|".join(_regex(r["expressao_no_texto"], f"classes, linha {i}") for _, i, r in alts)
        classes.append((float(ordem), nome, (rx, membros)))
    c["CLASSES_V2"] = {n: v for _, n, v in sorted(classes, key=lambda x: x[0])}
    c["OATP_V2"] = c["CLASSES_V2"].get(CLASSE_OATP, ("", []))[1]
    c["BCRP_V2"] = c["CLASSES_V2"].get(CLASSE_BCRP, ("", []))[1]

    exp = {k: "|".join(_regex(r["expressao"], f"expressoes, linha {i}") for _, i, r in v)
           for k, v in _juntar(t["expressoes"], "regra", "expressoes").items()}
    falta = [k for k in REGRAS_OBRIGATORIAS if k not in exp]
    if falta:
        raise ErroConfiguracao(f"expressoes: faltam as regras {', '.join(falta)}")
    c["MANEJO_V2"] = [("C", exp["manejo_contraindicar"]), ("L", exp["manejo_limite_dose"]), ("M", exp["manejo_monitorar"])]
    for nome, k in (("SEM_AJUSTE_V2", "sem_ajuste"), ("NEGA_V2", "nega_interacao"), ("NEGA_PARCIAL_V2", "nega_parcial"),
                    ("DOSE_CONDICIONAL_V2", "dose_condicional"), ("SUBPOPULACAO_V2", "subpopulacao"), ("EXCECAO_V2", "excecao"),
                    ("ANAFORA_V2", "anafora"), ("PARAGRAFO_TRANSP_V2", "paragrafo_transportadores"),
                    ("ORIENT_TRANSP_V2", "orientacao_transportadores"), ("TABELA_REGRA_V2", "tabela_regra"),
                    ("TABELA_INICIO_V2", "tabela_inicio"), ("TABELA_FIM_V2", "tabela_fim")):
        c[nome] = exp[k]
    return c


_C = carregar()
globals().update({k: v for k, v in _C.items() if k.isupper()})


def rx_farmaco(farm_en):
    """Regex do nome DCB do fármaco no texto normalizado. Só casa no INÍCIO de palavra: evita que
    'amprenavir' case dentro de 'fosamprenavir' (ou 'cetoconazol' em 'levocetoconazol')."""
    return re.compile(r"(?<![a-z])(?:" + sa(DCB[farm_en][1]) + ")")  # noqa: F821  (DCB vem da configuração)
