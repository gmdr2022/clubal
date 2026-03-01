from __future__ import annotations

from typing import List, Optional

from openpyxl import load_workbook

from core.models import ClassItem


DEFAULT_SHEET_NAME = "CLUBAL"
EXPECTED_HEADERS = ["DIA", "INICIO", "FIM", "MODALIDADE", "PROFESSOR", "TAG"]


def _normalize_header(v: object) -> str:
    return str(v or "").strip().upper()


def load_classes_from_excel(path: str, sheet_name: str = DEFAULT_SHEET_NAME) -> List[ClassItem]:
    wb = load_workbook(path, data_only=True)

    if sheet_name not in wb.sheetnames:
        raise RuntimeError(f"Aba '{sheet_name}' não encontrada.")

    ws = wb[sheet_name]

    header_row = None
    headers: List[str] = []

    for r in range(1, 6):
        vals = [_normalize_header(ws.cell(row=r, column=c).value) for c in range(1, 30)]
        if "DIA" in vals and "INICIO" in vals and "FIM" in vals:
            header_row = r
            headers = vals
            break

    if header_row is None:
        header_row = 1
        headers = [_normalize_header(ws.cell(row=1, column=c).value) for c in range(1, 30)]

    def col_idx(name: str) -> Optional[int]:
        name = name.upper()
        if name in headers:
            return headers.index(name) + 1
        return None

    c_dia = col_idx("DIA")
    c_ini = col_idx("INICIO")
    c_fim = col_idx("FIM")
    c_mod = col_idx("MODALIDADE")
    c_prof = col_idx("PROFESSOR")
    c_tag = col_idx("TAG")

    if not (c_dia and c_ini and c_fim and c_mod):
        raise RuntimeError("Cabeçalhos necessários não encontrados na aba CLUBAL.")

    items: List[ClassItem] = []

    for r in range(header_row + 1, ws.max_row + 1):
        dia = str(ws.cell(row=r, column=c_dia).value or "").strip().upper()
        ini = str(ws.cell(row=r, column=c_ini).value or "").strip()
        fim = str(ws.cell(row=r, column=c_fim).value or "").strip()
        modalidade = str(ws.cell(row=r, column=c_mod).value or "").strip()

        if not dia or not ini or not fim or not modalidade:
            continue

        professor = str(ws.cell(row=r, column=c_prof).value or "").strip() if c_prof else ""
        tag = str(ws.cell(row=r, column=c_tag).value or "").strip().upper() if c_tag else ""

        items.append(ClassItem(dia, ini, fim, modalidade, professor, tag))

    return items