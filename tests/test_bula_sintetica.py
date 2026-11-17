"""Fluxo completo numa bula SINTÉTICA (gerada no teste, sem PDF real): extração -> banco -> identificação -> pré-classificação."""
import csv
import os
import shutil
import sqlite3

import pymupdf
import pytest

import banco
import completo
from identificar import identificar
from preclassificar import preclassificar

ENCHIMENTO = " ".join(["Texto de preenchimento sem relação com interações."] * 12)
BULA = f"""SINVASTATESTE
sinvastatina
Laboratório Exemplo Ltda.
Comprimidos revestidos 20 mg
I - IDENTIFICAÇÃO DO MEDICAMENTO
SINVASTATESTE
sinvastatina
APRESENTAÇÕES
Comprimidos revestidos de 20 mg em embalagem com 30 comprimidos.
USO ORAL
USO ADULTO
COMPOSIÇÃO
Cada comprimido revestido contém:
sinvastatina ................................ 20 mg
Excipientes: lactose monoidratada, amido e estearato de magnésio.
II - INFORMAÇÕES TÉCNICAS AOS PROFISSIONAIS DE SAÚDE
1. INDICAÇÕES
A sinvastatina é indicada para o tratamento da hipercolesterolemia. A sinvastatina reduz o LDL.
2. RESULTADOS DE EFICÁCIA
Estudos com sinvastatina demonstraram redução de eventos.
3. CARACTERÍSTICAS FARMACOLÓGICAS
A sinvastatina é metabolizada pelo CYP3A4. Farmacocinética: meia-vida de 2 horas.
4. CONTRAINDICAÇÕES
Uso concomitante com inibidores potentes do CYP3A4.
5. ADVERTÊNCIAS E PRECAUÇÕES
Risco de miopatia. {ENCHIMENTO}
6. INTERAÇÕES MEDICAMENTOSAS
A coadministração com claritromicina é contraindicada. {ENCHIMENTO}
Monitorar CK quando usada com colchicina. {ENCHIMENTO}
O fluconazol não teve efeito clinicamente significativo na exposição à sinvastatina. {ENCHIMENTO}
7. CUIDADOS DE ARMAZENAMENTO DO MEDICAMENTO
Conservar em temperatura ambiente (15 a 30 °C).
8. POSOLOGIA E MODO DE USAR
20 mg uma vez ao dia.
9. REAÇÕES ADVERSAS
Mialgia.
10. SUPERDOSE
Medidas de suporte.
III - DIZERES LEGAIS
Registro MS 1.2345.6789
Registrado por: Laboratório Exemplo Ltda."""


def _pdf(caminho):
    doc = pymupdf.open()
    linhas = BULA.split("\n")
    pagina, y = doc.new_page(), 50
    for linha in linhas:
        partes = [linha[i:i + 95] for i in range(0, len(linha), 95)] or [""]
        for p in partes:
            if y > 800:
                pagina, y = doc.new_page(), 50
            pagina.insert_text((40, y), p, fontsize=9)
            y += 12
    doc.save(caminho)


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    d = tmp_path_factory.mktemp("bula")
    os.makedirs(d / "pdfs" / "sub")
    _pdf(str(d / "pdfs" / "sub" / "nome_qualquer.pdf"))
    shutil.copy(d / "pdfs" / "sub" / "nome_qualquer.pdf", d / "pdfs" / "copia_identica.pdf")
    dados = d / "dados"
    os.makedirs(dados)
    with open(dados / "registros_estatinas.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["registro", "estatina", "associacao", "produto", "empresa", "categoria", "situacao"])
        w.writerow(["123456789", "sinvastatina", "False", "SINVASTATESTE", "LABORATÓRIO EXEMPLO LTDA", "Similar", "Ativo"])
    with open(dados / "corpus_bulas.csv", "w", encoding="utf-8-sig", newline="") as fh:
        fh.write("registro_ms;no_corpus;sha1\n")
    return d


def test_extracao(ambiente):
    r = completo.extrair_bula_completa(str(ambiente / "pdfs" / "sub" / "nome_qualquer.pdf"))
    secoes = r["secoes_completas"]
    for k in ("indicacoes", "contraindicacoes", "advertencias_precaucoes", "interacoes", "posologia", "reacoes_adversas", "superdose"):
        assert k in secoes, k
    assert "claritromicina" in secoes["interacoes"]["texto"]
    assert r["campos"]["registro"] == ["123456789"]
    comp = r["campos"]["composicao_estruturada"]
    assert any("sinvastatina" in a.lower() for a in comp["ativos_todos"])
    assert any("lactose" in e.lower() for e in comp["excipientes_todos"])


def test_identificacao_ignora_nome_e_copias(ambiente):
    ident = identificar(str(ambiente / "pdfs"), str(ambiente / "dados"))
    assert len(ident) == 1  # a cópia idêntica conta uma vez
    assert ident[0]["registro_ms"] == "123456789" and ident[0]["no_corpus"] == "Sim"


def test_preclassificacao(ambiente):
    os.makedirs(ambiente / "json", exist_ok=True)
    import json
    r = completo.extrair_bula_completa(str(ambiente / "pdfs" / "sub" / "nome_qualquer.pdf"))
    r["arquivo"] = "123456789 - nome_qualquer.pdf"
    json.dump(r, open(ambiente / "json" / "123456789.json", "w", encoding="utf-8"), ensure_ascii=False)
    db = str(ambiente / "b.db")
    banco.montar_banco(str(ambiente / "json"), db)
    bid = sqlite3.connect(db).execute("select id from bulas").fetchone()[0]
    bulas = {bid: {"registro_ms": "123456789", "estatina": "sinvastatina", "categoria": "Similar", "produto": "SINVASTATESTE", "empresa": "X"}}
    ref = [{"estatina": "sinvastatina", "farmaco_dcb": f, "registro_ativo_no_brasil": "Sim"}
           for f in ("claritromicina", "colchicina", "fluconazol", "posaconazol", "daptomicina")]
    res = {r["farmaco_dcb"]: r for r in preclassificar(db, bulas, ref)}
    assert (res["claritromicina"]["citacao"], res["claritromicina"]["manejo"]) == ("nominal", "contraindicar/evitar")
    assert (res["colchicina"]["citacao"], res["colchicina"]["manejo"]) == ("nominal", "monitorar")
    assert res["fluconazol"]["citacao"] == "nominal" and res["fluconazol"]["confianca"].startswith("baixa")
    # citada só por classe, na seção Contraindicações -> contraindicar
    assert (res["posaconazol"]["citacao"], res["posaconazol"]["manejo"]) == ("classe", "contraindicar/evitar")
    assert (res["daptomicina"]["citacao"], res["daptomicina"]["manejo"]) == ("nao citada", "nao se aplica")
