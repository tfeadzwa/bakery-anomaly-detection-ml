"""EDA for Returns dataset.

Analyzes:
- Return frequency by route, retailer, SKU, reason
- Return quantities and patterns over time
- Correlation between returns and dispatch/delivery
- Peak return periods

Outputs:
- reports/summaries/returns_by_{route,retailer,sku,reason}.csv
- reports/figures/returns_*.png
- reports/returns_summary.txt
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sns.set_style('whitegrid')


def load_and_prepare(path: Path) -> pd.DataFrame:
    logger.info(f'Loading {path}')
    df = pd.read_parquet(path)
    # parse timestamps
    for col in ['timestamp', 'return_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # derive time features if timestamp present
    if 'timestamp' in df.columns:
        df['hour'] = df['timestamp'].dt.hour
        df['dayofweek'] = df['timestamp'].dt.day_name()
        df['date'] = df['timestamp'].dt.date
        df['is_weekend'] = df['timestamp'].dt.weekday >= 5
    
    return df


def summary_stats(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    summary.append(f"Returns Dataset Summary")
    summary.append(f"="*60)
    summary.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    summary.append(f"\nColumns: {', '.join(df.columns.tolist())}")
    summary.append(f"\nData types:\n{df.dtypes.value_counts()}")
    summary.append(f"\nMissing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
    
    if 'qty_returned' in df.columns:
        summary.append(f"\nReturn Quantity Stats:")
        summary.append(f"  Total returned: {df['qty_returned'].sum():,.0f}")
        summary.append(f"  Mean: {df['qty_returned'].mean():.2f}")
        summary.append(f"  Median: {df['qty_returned'].median():.2f}")
        summary.append(f"  Max: {df['qty_returned'].max():.0f}")
    
    if 'return_reason' in df.columns:
        summary.append(f"\nTop Return Reasons:")
        top_reasons = df['return_reason'].value_counts().head(10)
        for reason, count in top_reasons.items():
            summary.append(f"  {reason}: {count:,} ({count/len(df)*100:.1f}%)")
    
    text = '\n'.join(summary)
    (out_dir / 'returns_summary.txt').write_text(text, encoding='utf-8')
    logger.info(f'Wrote summary to {out_dir / "returns_summary.txt"}')
    return text


def grouped_summaries(df: pd.DataFrame, out_dir: Path):
    summaries_dir = out_dir / 'summaries'
    summaries_dir.mkdir(parents=True, exist_ok=True)
    
    qty_col = 'qty_returned' if 'qty_returned' in df.columns else None
    
    # by route
    if 'route_id' in df.columns and qty_col:
        by_route = df.groupby('route_id')[qty_col].agg(['count', 'sum', 'mean', 'median']).reset_index()
        by_route.columns = ['route_id', 'return_count', 'total_qty_returned', 'mean_qty', 'median_qty']
        by_route = by_route.sort_values('total_qty_returned', ascending=False)
        by_route.to_csv(summaries_dir / 'returns_by_route.csv', index=False)
        logger.info(f'Wrote returns_by_route.csv')
    
    # by retailer
    if 'retailer_id' in df.columns and qty_col:
        by_retailer = df.groupby('retailer_id')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_retailer.columns = ['retailer_id', 'return_count', 'total_qty_returned', 'mean_qty']
        by_retailer = by_retailer.sort_values('total_qty_returned', ascending=False)
        by_retailer.to_csv(summaries_dir / 'returns_by_retailer.csv', index=False)
        logger.info(f'Wrote returns_by_retailer.csv')
    
    # by SKU
    if 'sku_code' in df.columns and qty_col:
        by_sku = df.groupby('sku_code')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_sku.columns = ['sku_code', 'return_count', 'total_qty_returned', 'mean_qty']
        by_sku = by_sku.sort_values('total_qty_returned', ascending=False)
        by_sku.to_csv(summaries_dir / 'returns_by_sku.csv', index=False)
        logger.info(f'Wrote returns_by_sku.csv')
    
    # by reason
    if 'return_reason' in df.columns and qty_col:
        by_reason = df.groupby('return_reason')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_reason.columns = ['return_reason', 'return_count', 'total_qty_returned', 'mean_qty']
        by_reason = by_reason.sort_values('total_qty_returned', ascending=False)
        by_reason.to_csv(summaries_dir / 'returns_by_reason.csv', index=False)
        logger.info(f'Wrote returns_by_reason.csv')


def visualizations(df: pd.DataFrame, out_dir: Path):
    figs_dir = out_dir / 'figures'
    figs_dir.mkdir(parents=True, exist_ok=True)
    
    qty_col = 'qty_returned' if 'qty_returned' in df.columns else None
    
    # 1. Return quantity distribution
    if qty_col:
        fig, ax = plt.subplots(figsize=(10, 5))
        df[qty_col].hist(bins=50, ax=ax, edgecolor='black')
        ax.set_xlabel('Quantity Returned')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of Return Quantities')
        plt.tight_layout()
        plt.savefig(figs_dir / 'returns_qty_hist.png', dpi=150)
        plt.close()
        logger.info('Saved returns_qty_hist.png')
    
    # 2. Returns by reason (bar chart)
    if 'return_reason' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        top_reasons = df['return_reason'].value_counts().head(15)
        top_reasons.plot(kind='barh', ax=ax)
        ax.set_xlabel('Count')
        ax.set_title('Top 15 Return Reasons')
        plt.tight_layout()
        plt.savefig(figs_dir / 'returns_by_reason_bar.png', dpi=150)
        plt.close()
        logger.info('Saved returns_by_reason_bar.png')
    
    # 3. Returns over time
    if 'timestamp' in df.columns and qty_col:
        daily = df.groupby('date')[qty_col].sum().reset_index()
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(daily['date'], daily[qty_col], marker='o', markersize=2)
        ax.set_xlabel('Date')
        ax.set_ylabel('Total Quantity Returned')
        ax.set_title('Returns Over Time (Daily)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figs_dir / 'returns_timeseries.png', dpi=150)
        plt.close()
        logger.info('Saved returns_timeseries.png')
    
    # 4. Returns by day of week
    if 'dayofweek' in df.columns and qty_col:
        fig, ax = plt.subplots(figsize=(10, 5))
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        by_day = df.groupby('dayofweek')[qty_col].sum().reindex(day_order)
        by_day.plot(kind='bar', ax=ax, color='steelblue')
        ax.set_xlabel('Day of Week')
        ax.set_ylabel('Total Quantity Returned')
        ax.set_title('Returns by Day of Week')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figs_dir / 'returns_by_dayofweek.png', dpi=150)
        plt.close()
        logger.info('Saved returns_by_dayofweek.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/processed/returns_dataset.parquet')
    parser.add_argument('--out_dir', default='reports')
    args = parser.parse_args()
    
    p = Path(args.input)
    if not p.exists():
        logger.error(f'Input not found: {p}')
        return
    
    df = load_and_prepare(p)
    out = Path(args.out_dir)
    
    summary_stats(df, out)
    grouped_summaries(df, out)
    visualizations(df, out)
    
    logger.info('Returns EDA complete')


if __name__ == '__main__':
    main()
