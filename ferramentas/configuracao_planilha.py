#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
configuracao_planilha.py - converte a configuração do motor entre a pasta de CSV e uma planilha Excel (.xlsx), e a valida.

  python ferramentas/configuracao_planilha.py --para-xlsx configuracao minha_configuracao.xlsx
  python ferramentas/configuracao_planilha.py --para-csv minha_configuracao.xlsx minha_configuracao/
  python ferramentas/configuracao_planilha.py --validar minha_configuracao.xlsx     (ou uma pasta de CSV)

A planilha tem uma aba por arquivo (alvos, referencia_ignorar, farmacos, classes, expressoes), com os mesmos cabeçalhos.
O motor aceita qualquer uma das duas formas: reproduzir_estudo.py --config PASTA_OU_PLANILHA (ou a variável BULARIO_CONFIG).
"""
import argparse, csv, os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "estudo"))


def _ler(origem):
    from regras import _ler_tabelas
    return _ler_tabelas(origem)


def _cabecalho(origem, nome):
    if origem.lower().endswith(".xlsx"):
        import openpyxl
        return [str(c.value) for c in next(openpyxl.load_workbook(origem, read_only=True)[nome].iter_rows(max_row=1))]
    with open(os.path.join(origem, nome + ".csv"), encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh, delimiter=";"))


def para_xlsx(pasta, saida):
    import openpyxl
    from openpyxl.styles import Font
    from regras import ARQUIVOS
    tabs = _ler(pasta)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nome in ARQUIVOS:
        ws = wb.create_sheet(nome)
        cab = _cabecalho(pasta, nome)
        ws.append(cab)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in tabs[nome]:
            ws.append([r.get(k, "") for k in cab])
        ws.freeze_panes = "A2"
    wb.save(saida)
    print("OK", saida)


def para_csv(planilha, pasta):
    from regras import ARQUIVOS
    tabs = _ler(planilha)
    os.makedirs(pasta, exist_ok=True)
    for nome in ARQUIVOS:
        cab = _cabecalho(planilha, nome)
        with open(os.path.join(pasta, nome + ".csv"), "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";", lineterminator="\n")
            w.writerow(cab)
            w.writerows([[r.get(k, "") for k in cab] for r in tabs[nome]])
    print("OK", pasta)


def validar(origem):
    from regras import carregar
    c = carregar(origem)
    print(f"configuração válida: {origem}")
    print(f"  {len(c['EST'])} fármacos-alvo, {len(c['DCB'])} fármacos interagentes, {len(c['CLASSES_V2'])} classes, "
          f"{len(c['ALIASES'])} grafias alternativas, {len(c['EQUIVALENTE'])} equivalências")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--para-xlsx", nargs=2, metavar=("PASTA_CSV", "PLANILHA.xlsx"))
    g.add_argument("--para-csv", nargs=2, metavar=("PLANILHA.xlsx", "PASTA_CSV"))
    g.add_argument("--validar", metavar="PASTA_OU_PLANILHA")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if a.para_xlsx:
        para_xlsx(*a.para_xlsx)
    elif a.para_csv:
        para_csv(*a.para_csv)
    else:
        validar(a.validar)


if __name__ == "__main__":
    main()
