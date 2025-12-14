#!/usr/bin/env python3
"""
EDA script for Production dataset.
Analyzes production volumes, SKU production patterns, plant efficiency.
"""
import argparse
import logging
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def load_and_prepare(path: Path) -> pd.DataFrame:
    """Load production dataset and parse timestamps."""
    logger.info(f"Loading {path}")
    df = pd.read_parquet(path)
    
    # Parse timestamp if exists
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['date'] = df['timestamp'].dt.date
        df['month'] = df['timestamp'].dt.to_period('M')
        df['dayofweek'] = df['timestamp'].dt.day_name()
        df['hour'] = df['timestamp'].dt.hour
    
    return df


def summary_stats(df: pd.DataFrame, out_dir: Path):
    """Generate summary statistics."""
    summary = []
    summary.append("="*70)
    summary.append("PRODUCTION DATASET SUMMARY")
    summary.append("="*70)
    summary.append(f"\nDataset Shape: {df.shape[0]:,} batches × {df.shape[1]} columns")
    summary.append(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}" if 'timestamp' in df.columns else "")
    
    # Production quantity summary
    qty_col = 'quantity_produced' if 'quantity_produced' in df.columns else 'production_qty'
    if qty_col in df.columns:
        summary.append(f"\n{'='*70}")
        summary.append("PRODUCTION VOLUME")
        summary.append(f"{'='*70}")
        summary.append(f"  Total produced: {df[qty_col].sum():,.0f} units")
        summary.append(f"  Mean batch size: {df[qty_col].mean():.2f}")
        summary.append(f"  Median batch size: {df[qty_col].median():.2f}")
        summary.append(f"  Std deviation: {df[qty_col].std():.2f}")
        summary.append(f"  Min: {df[qty_col].min():.0f} | Max: {df[qty_col].max():.0f}")
    
    # Plant/Depot distribution
    if 'plant' in df.columns:
        summary.append(f"\n{'='*70}")
        summary.append("PLANT DISTRIBUTION")
        summary.append(f"{'='*70}")
        summary.append(f"  Unique Plants: {df['plant'].nunique()}")
        for plant, count in df['plant'].value_counts().items():
            pct = count / len(df) * 100
            summary.append(f"  {plant}: {count:,} batches ({pct:.1f}%)")
    
    if 'depot_id' in df.columns:
        summary.append(f"\n  Unique Depots: {df['depot_id'].nunique()}")
    
    # Line performance
    if 'line_id' in df.columns:
        summary.append(f"\n{'='*70}")
        summary.append("PRODUCTION LINE PERFORMANCE")
        summary.append(f"{'='*70}")
        summary.append(f"  Unique Lines: {df['line_id'].nunique()}")
        for line, count in df['line_id'].value_counts().head(10).items():
            summary.append(f"  {line}: {count:,} batches")
    
    # Operator stats
    if 'operator_id' in df.columns:
        summary.append(f"\n  Unique Operators: {df['operator_id'].nunique()}")
        summary.append(f"  Batches per operator (avg): {len(df) / df['operator_id'].nunique():.1f}")
    
    # SKU distribution
    sku_col = 'sku' if 'sku' in df.columns else 'sku_code'
    if sku_col in df.columns:
        summary.append(f"\n{'='*70}")
        summary.append("SKU PRODUCTION")
        summary.append(f"{'='*70}")
        summary.append(f"  Unique SKUs: {df[sku_col].nunique()}")
        summary.append(f"\n  Top 10 SKUs by batch count:")
        for sku, count in df[sku_col].value_counts().head(10).items():
            pct = count / len(df) * 100
            summary.append(f"    {sku}: {count:,} batches ({pct:.1f}%)")
    
    # DEFECT ANALYSIS
    defect_cols = ['stacked_before_robot', 'squashed', 'torn', 'undersized_small', 
                   'valleys', 'loose_packs', 'pale_underbaked']
    available_defects = [col for col in defect_cols if col in df.columns]
    
    if available_defects:
        summary.append(f"\n{'='*70}")
        summary.append("QUALITY DEFECTS")
        summary.append(f"{'='*70}")
        
        total_defects = sum(df[col].sum() for col in available_defects if pd.api.types.is_numeric_dtype(df[col]))
        total_units = df[qty_col].sum() if qty_col in df.columns else len(df)
        defect_rate = (total_defects / total_units * 100) if total_units > 0 else 0
        
        summary.append(f"  Total defective units: {total_defects:,.0f}")
        summary.append(f"  Overall defect rate: {defect_rate:.2f}%")
        summary.append(f"\n  Defects by type:")
        
        for col in available_defects:
            if pd.api.types.is_numeric_dtype(df[col]):
                defect_sum = df[col].sum()
                defect_pct = (defect_sum / total_defects * 100) if total_defects > 0 else 0
                batches_affected = (df[col] > 0).sum()
                summary.append(f"    {col.replace('_', ' ').title()}: {defect_sum:,.0f} ({defect_pct:.1f}% of defects, {batches_affected} batches)")
    
    # Batch traceability
    if 'batch_id' in df.columns:
        summary.append(f"\n{'='*70}")
        summary.append("BATCH TRACEABILITY")
        summary.append(f"{'='*70}")
        summary.append(f"  Unique batch IDs: {df['batch_id'].nunique()}")
        summary.append(f"  Duplicate batch IDs: {df['batch_id'].duplicated().sum()}")
    
    summary.append(f"\n{'='*70}")
    summary.append(f"Missing values:\n{df.isnull().sum()[df.isnull().sum() > 0].to_string()}" if df.isnull().sum().sum() > 0 else "No missing values")
    
    summary_text = '\n'.join(summary)
    summary_file = out_dir / 'production_summary.txt'
    summary_file.write_text(summary_text, encoding='utf-8')
    logger.info(f"Wrote summary to {summary_file}")


def grouped_summaries(df: pd.DataFrame, out_dir: Path):
    """Generate grouped summaries by plant, SKU, line, operator, defects."""
    summaries_dir = out_dir / 'summaries'
    summaries_dir.mkdir(exist_ok=True)
    
    qty_col = 'quantity_produced' if 'quantity_produced' in df.columns else 'production_qty'
    sku_col = 'sku' if 'sku' in df.columns else 'sku_code'
    plant_col = 'plant' if 'plant' in df.columns else 'plant_id'
    
    # Defect columns
    defect_cols = ['stacked_before_robot', 'squashed', 'torn', 'undersized_small', 
                   'valleys', 'loose_packs', 'pale_underbaked']
    available_defects = [col for col in defect_cols if col in df.columns]
    
    # By plant
    if plant_col in df.columns:
        agg_dict = {}
        if qty_col in df.columns:
            agg_dict[qty_col] = ['count', 'sum', 'mean', 'std']
        for defect in available_defects:
            if pd.api.types.is_numeric_dtype(df[defect]):
                agg_dict[defect] = 'sum'
        
        if agg_dict:
            by_plant = df.groupby(plant_col).agg(agg_dict).reset_index()
            by_plant.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in by_plant.columns]
            # Calculate defect rate
            if qty_col + '_sum' in by_plant.columns:
                total_defects = sum(by_plant[d] for d in available_defects if d in by_plant.columns)
                by_plant['total_defects'] = total_defects
                by_plant['defect_rate_%'] = (total_defects / by_plant[qty_col + '_sum'] * 100).round(2)
            out_file = summaries_dir / 'production_by_plant.csv'
            by_plant.to_csv(out_file, index=False)
            logger.info(f"Wrote production_by_plant.csv")
    
    # By production line
    if 'line_id' in df.columns:
        agg_dict = {}
        if qty_col in df.columns:
            agg_dict[qty_col] = ['count', 'sum', 'mean']
        for defect in available_defects:
            if pd.api.types.is_numeric_dtype(df[defect]):
                agg_dict[defect] = 'sum'
        
        if agg_dict:
            by_line = df.groupby('line_id').agg(agg_dict).reset_index()
            by_line.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in by_line.columns]
            by_line = by_line.sort_values(by_line.columns[1], ascending=False)
            out_file = summaries_dir / 'production_by_line.csv'
            by_line.to_csv(out_file, index=False)
            logger.info(f"Wrote production_by_line.csv")
    
    # By operator
    if 'operator_id' in df.columns:
        agg_dict = {}
        if qty_col in df.columns:
            agg_dict[qty_col] = ['count', 'sum', 'mean']
        for defect in available_defects:
            if pd.api.types.is_numeric_dtype(df[defect]):
                agg_dict[defect] = 'sum'
        
        if agg_dict:
            by_operator = df.groupby('operator_id').agg(agg_dict).reset_index()
            by_operator.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in by_operator.columns]
            by_operator = by_operator.sort_values(by_operator.columns[1], ascending=False).head(50)
            out_file = summaries_dir / 'production_by_operator.csv'
            by_operator.to_csv(out_file, index=False)
            logger.info(f"Wrote production_by_operator.csv (top 50)")
    
    # By SKU
    if sku_col in df.columns:
        agg_dict = {}
        if qty_col in df.columns:
            agg_dict[qty_col] = ['count', 'sum', 'mean']
        for defect in available_defects:
            if pd.api.types.is_numeric_dtype(df[defect]):
                agg_dict[defect] = 'sum'
        
        if agg_dict:
            by_sku = df.groupby(sku_col).agg(agg_dict).reset_index()
            by_sku.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in by_sku.columns]
            by_sku = by_sku.sort_values(by_sku.columns[2], ascending=False)
            out_file = summaries_dir / 'production_by_sku.csv'
            by_sku.to_csv(out_file, index=False)
            logger.info(f"Wrote production_by_sku.csv")
    
    # By hour
    if 'hour' in df.columns:
        agg_dict = {}
        if qty_col in df.columns:
            agg_dict[qty_col] = ['count', 'mean', 'sum']
        
        if agg_dict:
            by_hour = df.groupby('hour').agg(agg_dict).reset_index()
            by_hour.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in by_hour.columns]
            out_file = summaries_dir / 'production_by_hour.csv'
            by_hour.to_csv(out_file, index=False)
            logger.info(f"Wrote production_by_hour.csv")
    
    # Defect summary
    if available_defects:
        defect_summary = []
        for defect in available_defects:
            if pd.api.types.is_numeric_dtype(df[defect]):
                defect_summary.append({
                    'defect_type': defect,
                    'total_count': df[defect].sum(),
                    'batches_affected': (df[defect] > 0).sum(),
                    'mean_per_batch': df[defect].mean(),
                    'max_per_batch': df[defect].max()
                })
        
        if defect_summary:
            defect_df = pd.DataFrame(defect_summary).sort_values('total_count', ascending=False)
            out_file = summaries_dir / 'production_defects_summary.csv'
            defect_df.to_csv(out_file, index=False)
            logger.info(f"Wrote production_defects_summary.csv")


def visualizations(df: pd.DataFrame, out_dir: Path):
    """Generate visualizations."""
    figures_dir = out_dir / 'figures'
    figures_dir.mkdir(exist_ok=True)
    
    qty_col = 'quantity_produced' if 'quantity_produced' in df.columns else 'production_qty'
    sku_col = 'sku' if 'sku' in df.columns else 'sku_code'
    plant_col = 'plant' if 'plant' in df.columns else 'plant_id'
    
    defect_cols = ['stacked_before_robot', 'squashed', 'torn', 'undersized_small', 
                   'valleys', 'loose_packs', 'pale_underbaked']
    available_defects = [col for col in defect_cols if col in df.columns]
    
    # 1. Production quantity histogram (batch size distribution)
    if qty_col in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.hist(df[qty_col].dropna(), bins=50, color='steelblue', edgecolor='black', alpha=0.7)
        ax.axvline(df[qty_col].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {df[qty_col].mean():.0f}')
        ax.axvline(df[qty_col].median(), color='orange', linestyle='--', linewidth=2, label=f'Median: {df[qty_col].median():.0f}')
        ax.set_xlabel('Batch Size (Units Produced)', fontsize=12)
        ax.set_ylabel('Frequency (Number of Batches)', fontsize=12)
        ax.set_title('Distribution of Production Batch Sizes', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        out_file = figures_dir / 'production_qty_hist.png'
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved production_qty_hist.png")
    
    # 2. Production by plant with defect rates
    if plant_col in df.columns and qty_col in df.columns:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Total production
        plant_prod = df.groupby(plant_col)[qty_col].sum().sort_values(ascending=False)
        ax1.bar(range(len(plant_prod)), plant_prod.values, color='green', edgecolor='black', alpha=0.7)
        ax1.set_xticks(range(len(plant_prod)))
        ax1.set_xticklabels(plant_prod.index, rotation=45, ha='right')
        ax1.set_xlabel('Plant', fontsize=12)
        ax1.set_ylabel('Total Production Volume', fontsize=12)
        ax1.set_title('Total Production by Plant', fontsize=13, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # Defect rates by plant
        if available_defects:
            plant_defects = df.groupby(plant_col)[available_defects].sum().sum(axis=1)
            plant_qty = df.groupby(plant_col)[qty_col].sum()
            defect_rates = (plant_defects / plant_qty * 100).sort_values(ascending=False)
            
            ax2.bar(range(len(defect_rates)), defect_rates.values, color='red', edgecolor='black', alpha=0.7)
            ax2.set_xticks(range(len(defect_rates)))
            ax2.set_xticklabels(defect_rates.index, rotation=45, ha='right')
            ax2.set_xlabel('Plant', fontsize=12)
            ax2.set_ylabel('Defect Rate (%)', fontsize=12)
            ax2.set_title('Defect Rate by Plant', fontsize=13, fontweight='bold')
            ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        out_file = figures_dir / 'production_by_plant_bar.png'
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved production_by_plant_bar.png")
    
    # 3. Timeseries of production volume
    if 'timestamp' in df.columns and qty_col in df.columns:
        df_ts = df[df['timestamp'].notna()].copy()
        if len(df_ts) > 0:
            df_ts = df_ts.sort_values('timestamp')
            daily_prod = df_ts.groupby(df_ts['timestamp'].dt.date)[qty_col].sum()
            
            fig, ax = plt.subplots(figsize=(14, 6))
            ax.plot(daily_prod.index, daily_prod.values, linewidth=2, color='darkgreen', marker='o', markersize=3)
            ax.axhline(daily_prod.mean(), color='red', linestyle='--', alpha=0.7, label=f'Average: {daily_prod.mean():.0f}')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Daily Production Volume', fontsize=12)
            ax.set_title('Production Volume Over Time (Daily)', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            out_file = figures_dir / 'production_timeseries.png'
            plt.savefig(out_file, dpi=150, bbox_inches='tight')
            plt.close()
            logger.info(f"Saved production_timeseries.png")
    
    # 4. Production by hour (shift analysis)
    if 'hour' in df.columns and qty_col in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        hourly_data = df.groupby('hour')[qty_col].agg(['mean', 'count'])
        
        ax.bar(hourly_data.index, hourly_data['mean'], color='teal', edgecolor='black', alpha=0.7)
        ax.set_xlabel('Hour of Day (0-23)', fontsize=12)
        ax.set_ylabel('Average Production Quantity', fontsize=12)
        ax.set_title('Production by Hour of Day (Shift Pattern Analysis)', fontsize=14, fontweight='bold')
        ax.set_xticks(range(0, 24))
        ax.grid(axis='y', alpha=0.3)
        
        # Add count as text
        for i, (idx, row) in enumerate(hourly_data.iterrows()):
            if row['count'] > 0:
                ax.text(idx, row['mean'], f"{row['count']:.0f}", ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        out_file = figures_dir / 'production_by_hour.png'
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved production_by_hour.png")
    
    # 5. Defects breakdown
    if available_defects and any(pd.api.types.is_numeric_dtype(df[col]) for col in available_defects):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Defect counts
        defect_counts = {col.replace('_', ' ').title(): df[col].sum() 
                        for col in available_defects if pd.api.types.is_numeric_dtype(df[col])}
        defect_counts = dict(sorted(defect_counts.items(), key=lambda x: x[1], reverse=True))
        
        ax1.barh(list(defect_counts.keys()), list(defect_counts.values()), color='coral', edgecolor='black', alpha=0.8)
        ax1.set_xlabel('Total Defect Count', fontsize=12)
        ax1.set_title('Total Defects by Type', fontsize=13, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        # Defect rate pie chart
        total_defects = sum(defect_counts.values())
        if total_defects > 0:
            ax2.pie(defect_counts.values(), labels=defect_counts.keys(), autopct='%1.1f%%', startangle=90)
            ax2.set_title('Defect Composition (%)', fontsize=13, fontweight='bold')
        
        plt.tight_layout()
        out_file = figures_dir / 'production_defects_breakdown.png'
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved production_defects_breakdown.png")
    
    # 6. Line performance comparison
    if 'line_id' in df.columns and qty_col in df.columns:
        line_data = df.groupby('line_id').agg({
            qty_col: ['count', 'sum', 'mean']
        })
        line_data.columns = ['batch_count', 'total_prod', 'avg_batch_size']
        line_data = line_data.sort_values('total_prod', ascending=False).head(10)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        x = range(len(line_data))
        ax.bar(x, line_data['total_prod'], color='purple', alpha=0.7, edgecolor='black')
        ax.set_xticks(x)
        ax.set_xticklabels(line_data.index, rotation=45, ha='right')
        ax.set_xlabel('Production Line', fontsize=12)
        ax.set_ylabel('Total Production Volume', fontsize=12)
        ax.set_title('Top 10 Production Lines by Volume', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        out_file = figures_dir / 'production_by_line.png'
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved production_by_line.png")
    
    # 7. SKU production mix
    if sku_col in df.columns and qty_col in df.columns:
        sku_prod = df.groupby(sku_col)[qty_col].sum().sort_values(ascending=False).head(10)
        
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.barh(range(len(sku_prod)), sku_prod.values, color='gold', edgecolor='black', alpha=0.8)
        ax.set_yticks(range(len(sku_prod)))
        ax.set_yticklabels(sku_prod.index)
        ax.set_xlabel('Total Production Volume', fontsize=12)
        ax.set_ylabel('SKU', fontsize=12)
        ax.set_title('Top 10 SKUs by Production Volume', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        out_file = figures_dir / 'production_by_sku.png'
        plt.savefig(out_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved production_by_sku.png")


def main():
    parser = argparse.ArgumentParser(description="Run EDA on Production dataset")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/production_dataset.parquet"),
        help="Input parquet file"
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=Path("reports"),
        help="Output directory for reports"
    )
    args = parser.parse_args()
    
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    df = load_and_prepare(args.input)
    summary_stats(df, args.out_dir)
    grouped_summaries(df, args.out_dir)
    visualizations(df, args.out_dir)
    
    logger.info("Production EDA complete")


if __name__ == '__main__':
    main()
