"""EDA for Waste dataset.

Analyzes:
- Waste quantities by plant, location, SKU, reason
- Temporal patterns (peak waste times)
- Cost implications if available
- Correlation with other factors

Outputs:
- reports/summaries/waste_by_{plant,sku,reason,location}.csv
- reports/figures/waste_*.png
- reports/waste_summary.txt
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
    for col in ['timestamp', 'waste_date', 'expiry_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    if 'timestamp' in df.columns:
        df['hour'] = df['timestamp'].dt.hour
        df['dayofweek'] = df['timestamp'].dt.day_name()
        df['date'] = df['timestamp'].dt.date
        df['is_weekend'] = df['timestamp'].dt.weekday >= 5
    
    return df


def summary_stats(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    summary.append(f"Waste Dataset Summary")
    summary.append(f"="*60)
    summary.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    summary.append(f"\nColumns: {', '.join(df.columns.tolist())}")
    summary.append(f"\nData types:\n{df.dtypes.value_counts()}")
    summary.append(f"\nMissing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
    
    if 'waste_qty' in df.columns:
        summary.append(f"\nWaste Quantity Stats:")
        summary.append(f"  Total waste: {df['waste_qty'].sum():,.0f} units")
        summary.append(f"  Mean: {df['waste_qty'].mean():.2f}")
        summary.append(f"  Median: {df['waste_qty'].median():.2f}")
        summary.append(f"  Max: {df['waste_qty'].max():.0f}")
    
    if 'waste_reason' in df.columns:
        summary.append(f"\nTop Waste Reasons:")
        top_reasons = df['waste_reason'].value_counts().head(10)
        for reason, count in top_reasons.items():
            summary.append(f"  {reason}: {count:,} ({count/len(df)*100:.1f}%)")
    
    text = '\n'.join(summary)
    (out_dir / 'waste_summary.txt').write_text(text, encoding='utf-8')
    logger.info(f'Wrote summary to {out_dir / "waste_summary.txt"}')
    return text


def grouped_summaries(df: pd.DataFrame, out_dir: Path):
    summaries_dir = out_dir / 'summaries'
    summaries_dir.mkdir(parents=True, exist_ok=True)
    
    qty_col = 'waste_qty' if 'waste_qty' in df.columns else None
    
    if 'plant_id' in df.columns and qty_col:
        by_plant = df.groupby('plant_id')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_plant.columns = ['plant_id', 'waste_count', 'total_waste_qty', 'mean_qty']
        by_plant = by_plant.sort_values('total_waste_qty', ascending=False)
        by_plant.to_csv(summaries_dir / 'waste_by_plant.csv', index=False)
        logger.info('Wrote waste_by_plant.csv')
    
    if 'sku_code' in df.columns and qty_col:
        by_sku = df.groupby('sku_code')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_sku.columns = ['sku_code', 'waste_count', 'total_waste_qty', 'mean_qty']
        by_sku = by_sku.sort_values('total_waste_qty', ascending=False)
        by_sku.to_csv(summaries_dir / 'waste_by_sku.csv', index=False)
        logger.info('Wrote waste_by_sku.csv')
    
    if 'waste_reason' in df.columns and qty_col:
        by_reason = df.groupby('waste_reason')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_reason.columns = ['waste_reason', 'waste_count', 'total_waste_qty', 'mean_qty']
        by_reason = by_reason.sort_values('total_waste_qty', ascending=False)
        by_reason.to_csv(summaries_dir / 'waste_by_reason.csv', index=False)
        logger.info('Wrote waste_by_reason.csv')
    
    if 'location' in df.columns and qty_col:
        by_loc = df.groupby('location')[qty_col].agg(['count', 'sum', 'mean']).reset_index()
        by_loc.columns = ['location', 'waste_count', 'total_waste_qty', 'mean_qty']
        by_loc = by_loc.sort_values('total_waste_qty', ascending=False)
        by_loc.to_csv(summaries_dir / 'waste_by_location.csv', index=False)
        logger.info('Wrote waste_by_location.csv')


def visualizations(df: pd.DataFrame, out_dir: Path):
    figs_dir = out_dir / 'figures'
    figs_dir.mkdir(parents=True, exist_ok=True)
    
    qty_col = 'waste_qty' if 'waste_qty' in df.columns else None
    
    if qty_col:
        fig, ax = plt.subplots(figsize=(10, 5))
        df[qty_col].hist(bins=50, ax=ax, edgecolor='black')
        ax.set_xlabel('Waste Quantity')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of Waste Quantities')
        plt.tight_layout()
        plt.savefig(figs_dir / 'waste_qty_hist.png', dpi=150)
        plt.close()
        logger.info('Saved waste_qty_hist.png')
    
    if 'waste_reason' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        top_reasons = df['waste_reason'].value_counts().head(15)
        top_reasons.plot(kind='barh', ax=ax)
        ax.set_xlabel('Count')
        ax.set_title('Top 15 Waste Reasons')
        plt.tight_layout()
        plt.savefig(figs_dir / 'waste_by_reason_bar.png', dpi=150)
        plt.close()
        logger.info('Saved waste_by_reason_bar.png')
    
    if 'timestamp' in df.columns and qty_col:
        daily = df.groupby('date')[qty_col].sum().reset_index()
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(daily['date'], daily[qty_col], marker='o', markersize=2)
        ax.set_xlabel('Date')
        ax.set_ylabel('Total Waste Quantity')
        ax.set_title('Waste Over Time (Daily)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figs_dir / 'waste_timeseries.png', dpi=150)
        plt.close()
        logger.info('Saved waste_timeseries.png')
    
    if 'location' in df.columns and qty_col:
        fig, ax = plt.subplots(figsize=(12, 6))
        by_loc = df.groupby('location')[qty_col].sum().sort_values(ascending=False).head(20)
        by_loc.plot(kind='barh', ax=ax, color='salmon')
        ax.set_xlabel('Total Waste Quantity')
        ax.set_title('Top 20 Locations by Waste')
        plt.tight_layout()
        plt.savefig(figs_dir / 'waste_by_location.png', dpi=150)
        plt.close()
        logger.info('Saved waste_by_location.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/processed/waste_dataset.parquet')
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
    
    logger.info('Waste EDA complete')


if __name__ == '__main__':
    main()
