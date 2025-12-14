"""EDA for dispatch dataset.

- Loads `data/processed/dispatch_dataset.parquet`.
- Computes `dispatch_delay_minutes = (actual_arrival - expected_arrival)`.
- Produces summary tables grouped by plant, route, vehicle, sku.
- Saves figures to `reports/figures` and CSV summaries to `reports`.

Usage:
    python src/analysis/eda_dispatch.py --input data/processed/dispatch_dataset.parquet --out_dir reports
"""
from pathlib import Path
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_data(path: Path) -> pd.DataFrame:
    logger.info(f"Loading {path}")
    df = pd.read_parquet(path)
    return df


def compute_delay(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # ensure necessary datetime columns exist
    for c in ['expected_arrival', 'actual_arrival', 'timestamp']:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')
    # compute delay in minutes
    if 'expected_arrival' in df.columns and 'actual_arrival' in df.columns:
        df['dispatch_delay_minutes'] = (df['actual_arrival'] - df['expected_arrival']).dt.total_seconds() / 60.0
    else:
        df['dispatch_delay_minutes'] = np.nan
    # derive time features
    if 'timestamp' in df.columns:
        df['hour'] = df['timestamp'].dt.hour
        df['dayofweek'] = df['timestamp'].dt.day_name()
    return df


def summary_stats(df: pd.DataFrame, groupby_cols, out_path: Path):
    grp = df.groupby(groupby_cols)['dispatch_delay_minutes']
    summary = grp.agg(['count', 'mean', 'median', 'std', lambda x: np.quantile(x.dropna(), 0.95) if x.dropna().size>0 else np.nan])
    summary = summary.rename(columns={'<lambda_0>':'95pct'})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path)
    logger.info(f"Wrote summary {out_path}")
    return summary


def make_plots(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    # histogram of delays
    plt.figure(figsize=(8,4))
    sns.histplot(df['dispatch_delay_minutes'].dropna(), bins=100)
    plt.xlabel('Dispatch delay (minutes)')
    plt.tight_layout()
    p1 = out_dir / 'dispatch_delay_hist.png'
    plt.savefig(p1)
    plt.close()
    logger.info(f"Wrote {p1}")

    # boxplot by route (top 20 busiest routes)
    top_routes = df['route_id'].value_counts().nlargest(20).index
    df_top = df[df['route_id'].isin(top_routes)]
    plt.figure(figsize=(12,6))
    sns.boxplot(x='route_id', y='dispatch_delay_minutes', data=df_top)
    plt.xticks(rotation=45)
    plt.xlabel('Route ID')
    plt.ylabel('Delay (minutes)')
    plt.tight_layout()
    p2 = out_dir / 'dispatch_delay_by_route_box.png'
    plt.savefig(p2)
    plt.close()
    logger.info(f"Wrote {p2}")

    # heatmap of average delay by hour vs dayofweek
    pivot = df.pivot_table(index='dayofweek', columns='hour', values='dispatch_delay_minutes', aggfunc='mean')
    # reorder days
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    pivot = pivot.reindex(days)
    plt.figure(figsize=(12,4))
    sns.heatmap(pivot, cmap='coolwarm', center=0)
    plt.xlabel('Hour of day')
    plt.ylabel('Day of week')
    plt.tight_layout()
    p3 = out_dir / 'delay_hour_day_heatmap.png'
    plt.savefig(p3)
    plt.close()
    logger.info(f"Wrote {p3}")


def main(input_path: str, out_dir: str):
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    df = load_data(input_path)
    df = compute_delay(df)

    # save an augmented sample for inspection
    sample_path = out_dir / 'dispatch_augmented_sample.csv'
    df.sample(min(1000, len(df))).to_csv(sample_path, index=False)
    logger.info(f"Wrote sample to {sample_path}")

    # produce group summaries
    summary_dir = out_dir / 'summaries'
    summary_stats(df, ['plant_id'], summary_dir / 'dispatch_by_plant.csv')
    summary_stats(df, ['route_id'], summary_dir / 'dispatch_by_route.csv')
    summary_stats(df, ['vehicle_id'], summary_dir / 'dispatch_by_vehicle.csv')
    summary_stats(df, ['sku'], summary_dir / 'dispatch_by_sku.csv')

    # save overall delay distribution stats
    overall = df['dispatch_delay_minutes'].describe()
    overall_path = out_dir / 'dispatch_delay_overall.csv'
    overall.to_csv(overall_path)
    logger.info(f"Wrote overall stats to {overall_path}")

    # produce plots
    fig_dir = Path('reports/figures')
    make_plots(df, fig_dir)

    logger.info('EDA complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/processed/dispatch_dataset.parquet')
    parser.add_argument('--out_dir', default='reports')
    args = parser.parse_args()
    main(args.input, args.out_dir)
