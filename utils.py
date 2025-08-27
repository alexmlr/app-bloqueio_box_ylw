import re
import os
import unicodedata
import difflib
import pandas as pd

UNIDADES_VALIDAS = {
    'cidade nova': 'Cidade Nova',
    'castelo': 'Castelo',
    'raja': 'Raja',
    'buritis': 'Buritis',
    'nova cachoeirinha': 'Nova Cachoeirinha'
}

# Aceita "7.8", "07.8", "7.08", "27.08" etc.
DATE_PATTERN = re.compile(r"\b(\d{1,2}\.\d{1,2})\b")

COL_DIAS = "Dias Inadimplência"
COL_BOXES = "Boxes"


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm_text(s: str) -> str:
    s = _strip_accents(str(s)).lower()
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _normalize_date(d: str) -> str:
    try:
        dd, mm = d.split(".")
        return f"{int(dd):02d}.{int(mm):02d}"
    except Exception:
        return d

def _fuzzy_unit(unidade_part_norm: str, cutoff: float = 0.8) -> str | None:
    """Faz correspondência tolerante a erro de digitação."""
    keys = list(UNIDADES_VALIDAS.keys())
    match = difflib.get_close_matches(unidade_part_norm, keys, n=1, cutoff=cutoff)
    if match:
        return UNIDADES_VALIDAS[match[0]]
    # tenta por tokens (p.ex. 'nova cachoerinha' ≈ 'nova cachoeirinha')
    tokens = unidade_part_norm.split()
    for k in keys:
        score = difflib.SequenceMatcher(a=" ".join(tokens), b=k).ratio()
        if score >= cutoff:
            return UNIDADES_VALIDAS[k]
    return None

def extract_unit_and_date_from_name(original_name: str):
    """Extrai (UnidadeOficial, 'DD.MM') a partir do NOME ORIGINAL do arquivo."""
    name = os.path.splitext(original_name)[0]

    # Data
    m = DATE_PATTERN.search(name)
    data_str = _normalize_date(m.group(1)) if m else None

    # Unidade (remove a data e normaliza)
    unidade_part = DATE_PATTERN.sub("", name)
    unidade_part_norm = _norm_text(unidade_part)

    # Primeiro tenta match exato por inclusão
    unidade_detectada = None
    for k, v in UNIDADES_VALIDAS.items():
        if k in unidade_part_norm:
            unidade_detectada = v
            break
    # Se não achou, tenta fuzzy
    if not unidade_detectada:
        unidade_detectada = _fuzzy_unit(unidade_part_norm, cutoff=0.75)

    return unidade_detectada, data_str

def split_boxes(value: str):
    """Divide por vírgula, '/', ';', '|', ou quebra de linha."""
    if pd.isna(value):
        return []
    parts = re.split(r"[,/;\|\n\r]", str(value))
    return [p.strip().upper() for p in parts if p.strip()]

def _read_sheet(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine='openpyxl')
    if COL_DIAS not in df.columns or COL_BOXES not in df.columns:
        raise ValueError(f"Planilha sem colunas obrigatórias: {COL_DIAS}, {COL_BOXES}")
    return df[[COL_DIAS, COL_BOXES]].copy()

def load_boxes_ge5(path: str) -> set:
    df = _read_sheet(path)
    df[COL_DIAS] = pd.to_numeric(df[COL_DIAS], errors='coerce')
    df = df[df[COL_DIAS] >= 5]
    boxes = set()
    for _, row in df.iterrows():
        for b in split_boxes(row[COL_BOXES]):
            boxes.add(b)
    return boxes

def load_boxes_anydays(path: str) -> set:
    df = _read_sheet(path)
    boxes = set()
    for _, row in df.iterrows():
        for b in split_boxes(row[COL_BOXES]):
            boxes.add(b)
    return boxes

def group_by_unit_and_date(items):
    """
    items: lista de dicts {"path": <str>, "name": <nome original>}
    Retorna: {unidade: {data: [paths...]}}
    """
    grouped = {}
    for item in items:
        original_name = item["name"]
        path = item["path"]
        unidade, data_str = extract_unit_and_date_from_name(original_name)
        grouped.setdefault(unidade, {}).setdefault(data_str, []).append(path)
    return grouped

def pick_two_dates(all_dates):
    def key_fn(d):
        dd, mm = d.split('.')
        return (int(mm), int(dd))
    ordered = sorted([_normalize_date(d) for d in all_dates if d], key=key_fn)
    if len(ordered) < 2:
        return None, None
    return ordered[-2], ordered[-1]

def process_report_batch(items):
    grouped = group_by_unit_and_date(items)
    resultado = {}
    diag = {"files": []}

    # Coleta datas
    all_dates = set()
    for unidade, dates in grouped.items():
        for d in dates.keys():
            if d:
                all_dates.add(d)
    anterior, atual = pick_two_dates(all_dates)

    # Diagnóstico
    for unidade, dates in grouped.items():
        for d, lst in dates.items():
            diag["files"].append({"unidade": unidade, "data": d, "qtde": len(lst)})

    for unidade in UNIDADES_VALIDAS.values():
        u_bucket = grouped.get(unidade, {})
        prev_paths = u_bucket.get(anterior, []) if anterior else []
        curr_paths = u_bucket.get(atual, []) if atual else []

        # PROTEÇÃO: se faltar uma das datas para a unidade, não sugerimos ação
        if not prev_paths or not curr_paths:
            resultado[unidade] = {
                'bloquear': [],
                'desbloquear': [],
                'datas': {'anterior': anterior, 'atual': atual},
                'alerta': 'Comparação inconclusiva: faltou planilha da data anterior ou atual para esta unidade.'
            }
            continue

        prev_ge5 = set()
        for p in prev_paths:
            prev_ge5 |= load_boxes_ge5(p)

        curr_ge5 = set()
        curr_any = set()
        for p in curr_paths:
            curr_ge5 |= load_boxes_ge5(p)
            curr_any |= load_boxes_anydays(p)

        bloquear = sorted(list(curr_ge5 - prev_ge5))
        desbloquear = sorted(list(prev_ge5 - curr_any))  # só se sumiu totalmente na atual

        resultado[unidade] = {
            'bloquear': bloquear,
            'desbloquear': desbloquear,
            'datas': {'anterior': anterior, 'atual': atual}
        }

    resultado["_diag"] = {"anterior": anterior, "atual": atual, "detalhes": diag}
    return resultado
