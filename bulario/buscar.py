#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar.py - consulta o banco clinico de bulas (bulas_unificado.db). Sem acento e sem diferenciar maiusculas.

Exemplos:
  python buscar.py --excipiente lactose                 # bulas que tem lactose na composicao
  python buscar.py --ativo tramadol                     # bulas com esse principio ativo (e a composicao de cada uma)
  python buscar.py --ativo tramadol --sem-excipiente lactose   # alternativas SEM lactose
  python buscar.py --texto "toranja"                    # busca no texto inteiro das bulas (com a secao e o trecho)
  python buscar.py --texto "insuficiencia hepatica" --secao posologia
  python buscar.py --tema gravidez --bula AVODART       # trechos sobre gravidez numa bula
  python buscar.py --bula XTANDI                        # ficha da bula: composicao, formas, apresentacoes, link
Cada resultado mostra o LINK do Bulario. Confira SEMPRE no texto oficial antes de decidir conduta.
"""
import argparse, os, sqlite3, sys, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))


def sa(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="bulas.db")
    ap.add_argument("--categoria", help="Categoria Regulatória Anvisa (ex.: novo, biologico, similar, dinamizado, especifico)")
    ap.add_argument("--excipiente")
    ap.add_argument("--sem-excipiente", dest="sem_exc")
    ap.add_argument("--ativo")
    ap.add_argument("--texto")
    ap.add_argument("--secao", help="parte do nome da secao (ex.: posologia, advertencias, reacoes)")
    ap.add_argument("--tema")
    ap.add_argument("--bula", help="parte do nome da bula")
    ap.add_argument("--max", type=int, default=15)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(a.db)
    con.row_factory = sqlite3.Row
    con.create_function('sa', 1, sa)

    def ficha(b):
        print(f"\n■ {b['nome']}  ({b['empresa']})\n  categoria: {b['categoria_regulatoria']} | expediente {b['expediente']} | registros {b['registros']} | via: {b['via_administracao']} | formas: {b['forma_farmaceutica']}")
        print(f"  fonte: {b['fonte_link']}")

    def bulas_where(cond, params):
        return con.execute(f"SELECT * FROM bulas b WHERE {cond}", params).fetchall()

    cond, par = ["1=1"], []
    if a.bula:
        cond.append("b.nome_norm LIKE ?")
        par.append(f"%{sa(a.bula)}%")
    if a.categoria:
        cond.append("sa(b.categoria_regulatoria) LIKE ?")
        par.append(f"%{sa(a.categoria)}%")
    if a.ativo:
        cond.append("EXISTS(SELECT 1 FROM ingredientes i WHERE i.bula_id=b.id AND i.tipo='ativo' AND i.nome_norm LIKE ?)")
        par.append(f"%{sa(a.ativo)}%")
    if a.excipiente:
        cond.append("EXISTS(SELECT 1 FROM ingredientes i WHERE i.bula_id=b.id AND i.tipo='excipiente' AND i.nome_norm LIKE ?)")
        par.append(f"%{sa(a.excipiente)}%")
    if a.sem_exc:
        cond.append("NOT EXISTS(SELECT 1 FROM ingredientes i WHERE i.bula_id=b.id AND i.tipo='excipiente' AND i.nome_norm LIKE ?)")
        par.append(f"%{sa(a.sem_exc)}%")

    if a.texto:
        q = " ".join('"' + t.replace('"', "") + '"' for t in a.texto.split())
        sql = ("SELECT s.secao, s.subtitulo, b.nome, b.expediente, b.fonte_link, snippet(secoes_fts, 0, '«', '»', ' … ', 28) AS trecho "
               "FROM secoes_fts JOIN secoes s ON s.id=secoes_fts.rowid JOIN bulas b ON b.id=s.bula_id "
               f"WHERE secoes_fts MATCH ? AND {' AND '.join(cond)}")
        params = [q] + par
        if a.secao:
            sql += " AND lower(s.secao) LIKE ?"
            params.append(f"%{sa(a.secao)}%")
        sql += " ORDER BY rank LIMIT ?"
        params.append(a.max)
        rows = con.execute(sql, params).fetchall()
        print(f"{len(rows)} trecho(s) (máx {a.max}) para: {a.texto}")
        for r in rows:
            print(f"\n■ {r['nome']} — {r['secao']}" + (f" › {r['subtitulo']}" if r["subtitulo"] else "") + f"\n  {r['trecho']}\n  {r['fonte_link']}")
        return

    if a.tema:
        rows = con.execute(f"SELECT b.nome,b.fonte_link,ic.secao,ic.trecho FROM indice_clinico ic JOIN bulas b ON b.id=ic.bula_id "
                           f"WHERE ic.tema LIKE ? AND {' AND '.join(cond)} LIMIT ?", [f"%{sa(a.tema)}%"] + par + [a.max]).fetchall()
        print(f"{len(rows)} trecho(s) sobre '{a.tema}':")
        for r in rows:
            print(f"\n■ {r['nome']} — {r['secao']}\n  {r['trecho']}\n  {r['fonte_link']}")
        return

    bs = bulas_where(" AND ".join(cond), par)
    print(f"{len(bs)} bula(s)")
    for b in bs[: a.max]:
        ficha(b)
        ings = con.execute("SELECT tipo,nome,quantidade,bloco FROM ingredientes WHERE bula_id=? ORDER BY id", (b["id"],)).fetchall()
        ativos = [f"{i['nome']} {i['quantidade']}".strip() for i in ings if i["tipo"] == "ativo"]
        exc = list(dict.fromkeys(i["nome"] for i in ings if i["tipo"] == "excipiente"))
        print("  ativos:", "; ".join(dict.fromkeys(ativos)))
        print("  excipientes:", "; ".join(exc) if exc else "(não identificados — ver texto original)")
        grupos = [r["grupo"] for r in con.execute("SELECT DISTINCT grupo FROM alertas WHERE bula_id=?", (b["id"],)).fetchall()]
        if grupos:
            print("  atenção (palavras-chave na composição):", ", ".join(grupos))
        if a.bula:
            for ap_ in con.execute("SELECT * FROM apresentacoes WHERE bula_id=?", (b["id"],)).fetchall():
                print(f"  apresentação: {ap_['texto'][:160]}")


if __name__ == "__main__":
    main()
