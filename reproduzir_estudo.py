#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproduzir_estudo.py - reproduz o estudo "Interações graves nas bulas brasileiras de estatinas" de ponta a ponta.

  python reproduzir_estudo.py --pdfs PASTA_COM_AS_BULAS [--saida resultados] [--motor v2|v1] [--config PASTA_OU_PLANILHA]
                               [--classificacao dados/classificacao_revisada.csv]

1. identifica cada PDF pelo registro MS escrito na bula (nomes de arquivo são ignorados) e confere a versão (SHA-1);
2. extrai as seções de cada bula e monta o banco SQLite;
3. pré-classifica cada par bula × interação grave (Drugs.com, 13/11/2026) — motor v2 (padrão: por frase, livro de códigos)
   ou v1 (versão 0.1.0, por janela de caracteres; mantido para reproduzir a versão anterior);
4. calcula a completude e compara com os números publicados (dados/estatisticas_*.json).
Com --classificacao (classificação revisada por humanos), os números finais usam essa tabela no lugar da pré-classificação.
Com --config, o motor v2 usa outra configuração (pasta com os .csv ou planilha .xlsx; padrão: configuracao/ do pacote).
"""
import argparse, csv, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(AQUI, "bulario"), os.path.join(AQUI, "estudo")]
import pandas as pd  # noqa: E402

import banco  # noqa: E402
import completo  # noqa: E402
from estatisticas import estatisticas  # noqa: E402
from identificar import identificar, ler_csv  # noqa: E402
from amostra import ordenar_corpus  # noqa: E402

DADOS = os.path.join(AQUI, "dados")


def salvar_csv(linhas, caminho):
    if not linhas:
        return
    with open(caminho, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()), delimiter=";")
        w.writeheader(); w.writerows(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdfs", help="pasta com as bulas em PDF (qualquer nome, subpastas incluídas)")
    ap.add_argument("--tabela", help="sem PDFs: recalcula as estatísticas a partir da tabela de pares (ex.: dados/preclassificacao_v02.csv)")
    ap.add_argument("--saida", default="resultados")
    ap.add_argument("--motor", choices=["v2", "v1"], default="v2", help="v2 = motor por frase (padrão); v1 = versão 0.1.0")
    ap.add_argument("--classificacao", help="CSV revisado (registro_ms;farmaco_dcb;citacao;local;manejo)")
    ap.add_argument("--config", help="configuração do motor v2: pasta com os .csv ou planilha .xlsx (padrão: configuracao/)")
    a = ap.parse_args()
    if not (a.pdfs or a.tabela):
        ap.error("informe --pdfs PASTA_DAS_BULAS (reprodução completa) ou --tabela dados/preclassificacao_v02.csv (só as estatísticas)")
    if a.config:
        os.environ["BULARIO_CONFIG"] = os.path.abspath(a.config)
    from classificar import classificar  # depois de --config: as regras são lidas ao importar
    from preclassificar import preclassificar
    import regras
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(os.path.join(a.saida, "json"), exist_ok=True)
    if a.tabela:  # nível 1 de reprodução: estatísticas a partir da tabela de pares congelada (não precisa dos PDFs)
        d = pd.read_csv(a.tabela, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        print(f"Tabela de pares: {a.tabela} ({len(d)} pares, {d['registro_ms'].nunique()} bulas)")
        _estatisticas(a, d, "pré-classificação automática", "v1" if "confianca" in d.columns else "v2")
        return

    # 1. identificação
    ident = identificar(a.pdfs, DADOS)
    salvar_csv([{k: v for k, v in l.items() if k != "caminho"} for l in ident], os.path.join(a.saida, "identificacao.csv"))
    corpus = [l for l in ident if l["no_corpus"] == "Sim"]
    esperados = {r["registro"] for r in ler_csv(os.path.join(DADOS, "registros_estatinas.csv"))
                 if r["situacao"] == "Ativo" and r["associacao"] != "True"}
    sem_bula = {r["registro"] for r in ler_csv(os.path.join(DADOS, "exclusoes_sem_bula.csv"))}
    faltam = sorted(esperados - sem_bula - {l["registro_ms"] for l in corpus})
    print(f"1) Identificação: {len(ident)} PDFs de estatina; {len(corpus)} no corpus "
          f"(esperado: {len(esperados - sem_bula)} = {len(esperados)} registros ativos − {len(sem_bula)} sem bula no Bulário)")
    print(f"   mesma versão do estudo: {sum(l['mesma_versao_do_estudo'] == 'Sim' for l in corpus)} de {len(corpus)}")
    if faltam:
        print(f"   ATENÇÃO: faltam {len(faltam)} registros (baixe as bulas): {', '.join(faltam)}")

    # 2. extração + banco
    for i, l in enumerate(corpus, 1):
        r = completo.extrair_bula_completa(l["caminho"])
        r["arquivo"] = f"{l['registro_ms']} - {os.path.basename(l['caminho'])}"
        json.dump(r, open(os.path.join(a.saida, "json", l["registro_ms"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\r2) Extração: {i}/{len(corpus)}", end="")
    db = os.path.join(a.saida, "bulas_estatinas.db")
    n, tot = banco.montar_banco(os.path.join(a.saida, "json"), db)
    print(f"\n   banco: {db} ({tot})")

    # 3. pré-classificação
    import sqlite3
    info = {l["registro_ms"]: l for l in corpus}
    bulas = {}
    for bid, arq in sqlite3.connect(db).execute("select id, arquivo from bulas"):
        l = info[arq[:9]]
        bulas[bid] = {k: l[k] for k in ("registro_ms", "estatina", "categoria", "produto", "empresa")}
    ref = ler_csv(os.path.join(DADOS, "interacoes_graves_referencia.csv"))
    pc = classificar(db, bulas, ref) if a.motor == "v2" else preclassificar(db, bulas, ref)
    # código da bula no artigo (B001…B092): ordem do estudo, dados/corpus_bulas.csv
    cod = dict(zip(*ordenar_corpus(pd.DataFrame([r for r in ler_csv(os.path.join(DADOS, "corpus_bulas.csv")) if r["no_corpus"] == "Sim"]))[["registro_ms", "id_bula"]].T.values))
    pc = [{"id_bula": cod.get(l["registro_ms"], ""), **l} for l in sorted(pc, key=lambda l: (cod.get(l["registro_ms"], "B999"), l["farmaco_dcb"]))]
    salvar_csv(pc, os.path.join(a.saida, "preclassificacao.csv"))
    print(f"3) Pré-classificação (motor {a.motor}): {len(pc)} pares bula × interação -> {a.saida}/preclassificacao.csv")
    if a.motor == "v2":
        print(f"   configuração do motor: {regras.ORIGEM}")

    # 4. estatísticas
    d = pd.DataFrame(pc)
    _estatisticas(a, d, "pré-classificação automática", a.motor)


def _estatisticas(a, d, fonte, motor):
    if a.classificacao:
        rev = pd.read_csv(a.classificacao, sep=";", encoding="utf-8-sig", dtype={"registro_ms": str})
        d = d.drop(columns=["citacao", "local", "manejo"]).merge(rev[["registro_ms", "farmaco_dcb", "citacao", "local", "manejo"]],
                                                                 on=["registro_ms", "farmaco_dcb"], how="left")
        fonte = "classificação revisada"
    out, pb = estatisticas(d, fonte)
    json.dump(out, open(os.path.join(a.saida, "estatisticas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pb.to_csv(os.path.join(a.saida, "completude_por_bula.csv"), sep=";", index=False, encoding="utf-8-sig")
    g = out["geral"]
    print(f"4) Completude mediana: ampla {g['ampla']['mediana']}% | estrita {g['estrita']['mediana']}% | "
          f"só fármacos registrados no Brasil {g['ampla_br']['mediana']}% | Kruskal-Wallis p = {out['kruskal_categorias_geral']}")
    ref_json = os.path.join(DADOS, "estatisticas_revisadas.json" if a.classificacao else
                            "estatisticas_preclassificacao_v02.json" if motor == "v2" else "estatisticas_preclassificacao.json")
    if os.path.exists(ref_json):
        pub = json.load(open(ref_json, encoding="utf-8"))
        chaves = ("geral", "por_estatina", "por_categoria", "kruskal_categorias_geral", "manejo_entre_citadas", "local_entre_citadas")
        iguais = all(out[k] == pub[k] for k in chaves)
        print(f"   comparação com {os.path.basename(ref_json)}: {'IDÊNTICO ✓' if iguais else 'DIFERENTE (veja estatisticas.json)'}")


if __name__ == "__main__":
    main()
