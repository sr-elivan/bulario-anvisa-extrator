#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrair.py - ferramenta geral: extrai QUALQUER conjunto de bulas profissionais (RDC 47/2009) para JSON + banco SQLite.

  python extrair.py PASTA_COM_PDFS [--saida saida] [--db bulas.db]
  python bulario/buscar.py --db bulas.db --ativo sinvastatina --texto claritromicina
"""
import argparse, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "bulario"))
import banco  # noqa: E402
import completo  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta")
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--db", default="bulas.db")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(os.path.join(a.saida, "json"), exist_ok=True)
    pdfs = sorted(os.path.join(r, f) for r, _, fs in os.walk(a.pasta) for f in fs if f.lower().endswith(".pdf"))
    for i, p in enumerate(pdfs, 1):
        nome = os.path.splitext(os.path.relpath(p, a.pasta))[0].replace(os.sep, "__")
        try:
            r = completo.extrair_bula_completa(p)
        except Exception as e:  # uma bula ruim não derruba o lote
            r = {"arquivo": os.path.basename(p), "expediente": "", "problemas": [f"ERRO: {e}"], "campos": {}, "secoes_completas": {}}
        json.dump(r, open(os.path.join(a.saida, "json", nome + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[{i}/{len(pdfs)}] {os.path.basename(p)}: {len(r.get('secoes_completas', {}))} seções; problemas: {', '.join(r.get('problemas', [])) or '-'}")
    n, tot = banco.montar_banco(os.path.join(a.saida, "json"), a.db)
    print(f"OK: {n} bulas no banco {a.db} {tot}")


if __name__ == "__main__":
    main()
