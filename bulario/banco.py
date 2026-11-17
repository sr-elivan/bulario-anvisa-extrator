#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""banco.py - monta o banco SQLite (tabelas bulas, ingredientes, secoes + busca FTS5)."""
import glob, json, os, sqlite3, unicodedata



def sa(s):
    """minusculo sem acento (para comparar nomes)"""
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


ESQUEMA = """
CREATE TABLE bulas(id INTEGER PRIMARY KEY, arquivo TEXT, expediente TEXT, fonte_link TEXT, nome TEXT, nome_norm TEXT,
  empresa TEXT, registros TEXT, aprovada_anvisa TEXT, via_administracao TEXT, uso_populacao TEXT, forma_farmaceutica TEXT,
  paginas INTEGER, problemas TEXT, categoria_regulatoria TEXT, categoria_codigo TEXT, tipo_bula TEXT);
CREATE INDEX i_cat ON bulas(categoria_regulatoria);
CREATE TABLE apresentacoes(id INTEGER PRIMARY KEY, bula_id INTEGER, texto TEXT, formas TEXT, concentracoes TEXT, embalagem TEXT);
CREATE TABLE ingredientes(id INTEGER PRIMARY KEY, bula_id INTEGER, tipo TEXT, nome TEXT, nome_norm TEXT, quantidade TEXT, bloco TEXT);
CREATE TABLE secoes(id INTEGER PRIMARY KEY, bula_id INTEGER, chave TEXT, secao TEXT, subtitulo TEXT, ordem INTEGER, texto TEXT);
CREATE VIRTUAL TABLE secoes_fts USING fts5(texto, subtitulo, secao, content='secoes', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
CREATE TABLE indice_clinico(id INTEGER PRIMARY KEY, bula_id INTEGER, tema TEXT, secao TEXT, trecho TEXT);
CREATE TABLE alertas(id INTEGER PRIMARY KEY, bula_id INTEGER, grupo TEXT, termo TEXT, contexto TEXT);
CREATE TABLE valores_pk(id INTEGER PRIMARY KEY, bula_id INTEGER, grandeza TEXT, trecho TEXT, valores TEXT);
CREATE INDEX i_ing ON ingredientes(tipo, nome_norm);
CREATE INDEX i_bula_nome ON bulas(nome_norm);
CREATE INDEX i_ic ON indice_clinico(tema);
"""


def montar_banco(pasta_json, db):
    """Junta os JSON de extração num SQLite com busca de texto (FTS5, sem acento)."""
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.executescript(ESQUEMA)
    n = 0
    for f in sorted(glob.glob(os.path.join(pasta_json, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        c = d.get("campos") or {}
        if not c:
            continue
        ap_ = c.get("apresentacoes", {})
        cur = con.execute(
            "INSERT INTO bulas(arquivo,expediente,fonte_link,nome,nome_norm,empresa,registros,aprovada_anvisa,via_administracao,uso_populacao,"
            "forma_farmaceutica,paginas,problemas,categoria_regulatoria,categoria_codigo,tipo_bula) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (d["arquivo"], d.get("expediente", ""), d.get("fonte_link") or " ; ".join(d.get("fontes_candidatas", [])),
             c.get("nome", ""), sa(c.get("nome", "")), c.get("empresa", ""), ",".join(c.get("registro", [])),
             c.get("aprovada_anvisa", ""), " | ".join(c.get("via_administracao", [])), " | ".join(c.get("uso_populacao", [])),
             " | ".join(ap_.get("forma_farmaceutica", [])), d.get("paginas", 0), " | ".join(d.get("problemas", [])),
             d.get("categoria_regulatoria", ""), d.get("categoria_codigo", ""), d.get("tipo_bula", "")))
        bid = cur.lastrowid
        for it in ap_.get("itens", []):
            con.execute("INSERT INTO apresentacoes(bula_id,texto,formas,concentracoes,embalagem) VALUES (?,?,?,?,?)",
                        (bid, it["texto"], " | ".join(it.get("formas", [])), " | ".join(it.get("concentracoes", [])), it.get("embalagem", "")))
        comp = c.get("composicao_estruturada", {})
        for b in comp.get("blocos", []):
            for at in b["ativos"]:
                con.execute("INSERT INTO ingredientes(bula_id,tipo,nome,nome_norm,quantidade,bloco) VALUES (?,?,?,?,?,?)",
                            (bid, "ativo", at["nome"], sa(at["nome"]), at.get("quantidade", ""), b["titulo"]))
            for ex in b["excipientes"]:
                con.execute("INSERT INTO ingredientes(bula_id,tipo,nome,nome_norm,quantidade,bloco) VALUES (?,?,?,?,?,?)",
                            (bid, "excipiente", ex, sa(ex), "", b["titulo"]))
        for chave, sec in (d.get("secoes_completas") or {}).items():
            for k, sub in enumerate(sec["subsecoes"] or [{"titulo": "", "texto": sec["texto"]}]):
                cur2 = con.execute("INSERT INTO secoes(bula_id,chave,secao,subtitulo,ordem,texto) VALUES (?,?,?,?,?,?)",
                                   (bid, chave, sec["titulo"], sub["titulo"], k, sub["texto"]))
                con.execute("INSERT INTO secoes_fts(rowid,texto,subtitulo,secao) VALUES (?,?,?,?)",
                            (cur2.lastrowid, sub["texto"], sub["titulo"], sec["titulo"]))
        for tema, itens in (c.get("indice_clinico") or {}).items():
            for it in itens:
                con.execute("INSERT INTO indice_clinico(bula_id,tema,secao,trecho) VALUES (?,?,?,?)", (bid, tema, it["secao"], it["trecho"]))
        for al in c.get("alertas_composicao", []):
            con.execute("INSERT INTO alertas(bula_id,grupo,termo,contexto) VALUES (?,?,?,?)", (bid, al["grupo"], al["termo"], al["contexto"]))
        for g, itens in (c.get("farmacocinetica", {}).get("valores") or {}).items():
            for it in itens:
                con.execute("INSERT INTO valores_pk(bula_id,grandeza,trecho,valores) VALUES (?,?,?,?)", (bid, g, it["trecho"], " | ".join(it["valores"])))
        n += 1
    con.commit()
    tot = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("bulas", "ingredientes", "secoes", "indice_clinico", "alertas")}
    con.close()
    return n, tot
