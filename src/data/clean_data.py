"""Cleaning and preprocessing helpers for the bakery datasets.

The functions here attempt to standardize column names, parse common timestamp
fields, unify quantity column names (qty variants), remove duplicate columns,
and write cleaned outputs to `data/processed`.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _standardize_colname(col: str) -> str:
    col = col.strip()
    col = col.replace('\n', '_').replace('\r', '_')
    col = col.replace(' ', '_').replace('-', '_').replace('.', '_')
    col = ''.join(c for c in col if c.isalnum() or c == '_')
    return col.lower()


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_standardize_colname(c) for c in df.columns]
    return df


def make_columns_unique(df: pd.DataFrame) -> pd.DataFrame:
    """Append numeric suffixes to duplicate column names to make them unique.

    This avoids pandas returning a DataFrame when indexing by a duplicate column
    label (which causes `.dtype` attribute errors)."""
    cols = list(df.columns)
    counts = {}
    new_cols = []
    for c in cols:
        if c in counts:
            counts[c] += 1
            new_cols.append(f"{c}_{counts[c]}")
        else:
            counts[c] = 0
            new_cols.append(c)
    df = df.copy()
    df.columns = new_cols
    return df


def parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Try to identify common timestamp-like column names
    time_cols = [c for c in df.columns if 'time' in c or 'timestamp' in c or 'date' in c]
    for c in time_cols:
        try:
            df[c] = pd.to_datetime(df[c], errors='coerce')
        except Exception:
            df[c] = pd.to_datetime(df[c], infer_datetime_format=True, errors='coerce')
    return df


def unify_qty_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Common qty column name patterns
    qty_candidates = [c for c in df.columns if ('qty' in c or 'quantity' in c) and not c.startswith('qty_')]
    # We will not rename every qty column blindly, but create canonical names where appropriate
    # For dispatch and sales tables we commonly want `qty_dispatched`, `quantity_sold`, `qty_waste`, `qty_returned`.
    mapping = {}
    for c in df.columns:
        if c in ['qty_dispatched', 'qty_dispatched']:
            continue
        if 'dispat' in c and 'qty' in c:
            mapping[c] = 'qty_dispatched'
        if 'dispatch' in c and ('qty' in c or 'quantity' in c):
            mapping[c] = 'qty_dispatched'
        if ('quantity_sold' in c) or (c in ['qty_sold', 'quantity_sold', 'quantity_sold']):
            mapping[c] = 'quantity_sold'
        if 'qty_return' in c or 'returned' in c:
            mapping[c] = 'qty_returned'
        if 'qty_waste' in c or 'waste' in c:
            if 'qty_waste' not in df.columns:
                mapping[c] = 'qty_waste'
    df = df.rename(columns=mapping)
    return df


def drop_all_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop columns that are exact duplicates of other columns."""
    df = df.copy()
    cols_to_drop = []
    seen_hashes = {}
    for c in df.columns:
        ser = df[c]
        try:
            h = hash(tuple(ser.fillna('__NA__').astype(str).values[:1000]))
        except Exception:
            h = None
        if h is not None and h in seen_hashes:
            cols_to_drop.append(c)
        elif h is not None:
            seen_hashes[h] = c
    if cols_to_drop:
        logger.info(f"Dropping duplicate columns: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    return df


def clean_file(input_path: Path, output_dir: Path) -> Path:
    logger.info(f"Cleaning file: {input_path.name}")
    df = pd.read_csv(input_path, sep=None, engine='python', on_bad_lines='skip')
    df = standardize_columns(df)
    df = make_columns_unique(df)
    df = parse_timestamps(df)
    df = unify_qty_columns(df)
    df = drop_all_duplicate_columns(df)

    # Convert numeric-like columns
    for c in df.columns:
        ser = df[c]
        # If indexing by label returned a DataFrame (duplicate column names), pick the first column
        if isinstance(ser, pd.DataFrame):
            logger.warning(f"Column label '{c}' refers to multiple columns; using first occurrence for type coercion")
            ser = ser.iloc[:, 0]

        # proceed only if we have a Series-like object
        if hasattr(ser, 'dtype') and ser.dtype == object:
            # try to coerce to numeric where ~90% convertible
            coerced = pd.to_numeric(ser.astype(str).str.replace(',', '').replace('', np.nan), errors='coerce')
            notnull_ratio = coerced.notnull().mean()
            if notnull_ratio > 0.9:
                df[c] = coerced

    # Prepare output path
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / (input_path.stem + '.parquet')
    try:
        df.to_parquet(out_path, index=False)
        logger.info(f"Wrote cleaned parquet to {out_path}")
    except Exception:
        out_csv = output_dir / (input_path.stem + '.cleaned.csv')
        df.to_csv(out_csv, index=False)
        logger.info(f"Parquet write failed; wrote CSV to {out_csv}")
        out_path = out_csv

    return out_path
