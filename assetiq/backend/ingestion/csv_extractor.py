"""
Handles .csv, .xlsx, .xls — equipment logs, maintenance schedules, etc.
Each Excel sheet becomes its own "page" so multi-sheet workbooks (e.g.
one sheet per unit/equipment) stay separable downstream.
"""

from pathlib import Path

import pandas as pd

from schema import make_doc_shell, make_page


def _df_to_text_and_table(df: pd.DataFrame):
    # Replace NaN with empty strings to avoid join errors
    df_filled = df.fillna("")
    rows = [df_filled.columns.tolist()] + df_filled.astype(str).values.tolist()
    text = df_filled.astype(str).apply(lambda r: " ".join(r), axis=1).str.cat(sep="\n")
    return text, [{"rows": rows}]


def process_tabular(path) -> dict:
    ext = Path(path).suffix.lower()
    doc_type = "csv" if ext == ".csv" else "xlsx"
    doc = make_doc_shell(path, doc_type)

    if ext == ".csv":
        df = pd.read_csv(path)
        text, tables = _df_to_text_and_table(df)
        doc["pages"] = [make_page(1, text, tables, ocr_confidence=None, extra_meta={"source_type": doc_type, "rows": int(df.shape[0]), "columns": int(df.shape[1])})]
    else:
        xls = pd.ExcelFile(path)
        pages = []
        for i, sheet_name in enumerate(xls.sheet_names):
            df = xls.parse(sheet_name)
            text, tables = _df_to_text_and_table(df)
            pages.append(make_page(i + 1, text, tables, ocr_confidence=None,
                                    extra_meta={"sheet_name": sheet_name, "source_type": doc_type, "rows": int(df.shape[0]), "columns": int(df.shape[1])}))
        doc["pages"] = pages

    return doc
