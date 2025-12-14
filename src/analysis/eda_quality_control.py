"""EDA for Quality Control (QC) Dataset.

Critical supply chain checkpoint: Production → QC → Dispatch/Waste
Every batch must pass QC checks before dispatch. Failed batches drive waste and returns.

Analyzes:
- QC pass/fail rates by parameter, SKU, batch, time
- Parameter value distributions (moisture, weight, temp, color, texture, etc.)
- Failed batch patterns and root causes
- QC-production linkage (line/operator quality performance)
- Time patterns (shift/hour quality trends)
- Anomaly detection targets (QC failures predict waste/returns)

Key Fields:
- qc_id: Unique QC check identifier
- timestamp: When measurement was taken
- batch_id: Links to Production dataset (critical traceability)
- sku: Product being inspected
- parameter: QC metric type (moisture_percent, weight_grams, internal_temp_c, etc.)
- value: Actual measurement recorded
- pass_fail: Whether measurement met quality standards
- notes: Text descriptions of issues

Outputs:
- reports/qc_summary.txt (comprehensive QC performance report)
- reports/summaries/qc_by_*.csv (parameter, SKU, batch, hour summaries)
- reports/figures/qc_*.png (8 visualizations)

Usage:
    python src/analysis/eda_quality_control.py
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)


def load_and_prepare(path: Path) -> pd.DataFrame:
    """Load QC dataset and prepare time features."""
    logger.info(f'Loading {path}')
    df = pd.read_parquet(path)
    
    # Parse timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['dayofweek'] = df['timestamp'].dt.day_name()
    
    # Ensure pass_fail is standardized
    if 'pass_fail' in df.columns:
        df['pass_fail'] = df['pass_fail'].str.strip().str.lower()
        # Create binary pass flag for easy calculations
        df['is_pass'] = (df['pass_fail'] == 'pass').astype(int)
        df['is_fail'] = (df['pass_fail'] == 'fail').astype(int)
    
    logger.info(f'Loaded {len(df):,} QC checks')
    return df


def summary_stats(df: pd.DataFrame, output_dir: Path) -> None:
    """Generate comprehensive QC summary statistics."""
    logger.info('Generating QC summary statistics')
    
    summary_path = output_dir / 'qc_summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('=' * 70 + '\n')
        f.write('QUALITY CONTROL (QC) DATASET SUMMARY\n')
        f.write('=' * 70 + '\n')
        f.write(f'Dataset Shape: {df.shape[0]:,} QC checks × {df.shape[1]} columns\n')
        
        if 'timestamp' in df.columns:
            f.write(f"Date Range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('QC PERFORMANCE OVERVIEW\n')
        f.write('-' * 70 + '\n')
        
        # Overall pass/fail rates
        if 'pass_fail' in df.columns:
            total_checks = len(df)
            pass_count = df['is_pass'].sum()
            fail_count = df['is_fail'].sum()
            pass_rate = (pass_count / total_checks * 100) if total_checks > 0 else 0
            fail_rate = (fail_count / total_checks * 100) if total_checks > 0 else 0
            
            f.write(f'Total QC Checks: {total_checks:,}\n')
            f.write(f'PASSED: {pass_count:,} ({pass_rate:.2f}%)\n')
            f.write(f'FAILED: {fail_count:,} ({fail_rate:.2f}%)\n')
            f.write(f'\n⚠️ QC Fail Rate: {fail_rate:.2f}% (Target: <2%)\n')
        
        # Batch coverage
        if 'batch_id' in df.columns:
            unique_batches = df['batch_id'].nunique()
            checks_per_batch = len(df) / unique_batches if unique_batches > 0 else 0
            f.write(f'\nBatches Inspected: {unique_batches:,}\n')
            f.write(f'Avg QC Checks per Batch: {checks_per_batch:.1f}\n')
            
            # Failed batches
            failed_batches = df[df['is_fail'] == 1]['batch_id'].nunique()
            failed_batch_rate = (failed_batches / unique_batches * 100) if unique_batches > 0 else 0
            f.write(f'Batches with Failures: {failed_batches:,} ({failed_batch_rate:.2f}%)\n')
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('QC PARAMETERS BREAKDOWN\n')
        f.write('-' * 70 + '\n')
        
        if 'parameter' in df.columns:
            unique_params = df['parameter'].nunique()
            f.write(f'Unique QC Parameters: {unique_params}\n\n')
            
            # Pass/fail by parameter
            param_summary = df.groupby('parameter').agg({
                'qc_id': 'count',
                'is_pass': 'sum',
                'is_fail': 'sum',
                'value': ['mean', 'std', 'min', 'max']
            }).round(2)
            
            param_summary.columns = ['total_checks', 'passed', 'failed', 'mean_value', 'std_value', 'min_value', 'max_value']
            param_summary['fail_rate_%'] = (param_summary['failed'] / param_summary['total_checks'] * 100).round(2)
            param_summary = param_summary.sort_values('fail_rate_%', ascending=False)
            
            f.write('QC Parameters (sorted by fail rate):\n')
            for param, row in param_summary.iterrows():
                f.write(f"\n  {param}:\n")
                f.write(f"    Total checks: {int(row['total_checks']):,}\n")
                f.write(f"    Passed: {int(row['passed']):,} | Failed: {int(row['failed']):,}\n")
                f.write(f"    Fail Rate: {row['fail_rate_%']:.2f}%\n")
                f.write(f"    Value range: {row['min_value']:.2f} - {row['max_value']:.2f} (mean: {row['mean_value']:.2f})\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('SKU QUALITY PERFORMANCE\n')
        f.write('-' * 70 + '\n')
        
        if 'sku' in df.columns:
            unique_skus = df['sku'].nunique()
            f.write(f'Unique SKUs Inspected: {unique_skus}\n\n')
            
            sku_summary = df.groupby('sku').agg({
                'qc_id': 'count',
                'is_pass': 'sum',
                'is_fail': 'sum'
            })
            sku_summary.columns = ['total_checks', 'passed', 'failed']
            sku_summary['fail_rate_%'] = (sku_summary['failed'] / sku_summary['total_checks'] * 100).round(2)
            sku_summary = sku_summary.sort_values('fail_rate_%', ascending=False).head(10)
            
            f.write('Top 10 SKUs by Fail Rate:\n')
            for sku, row in sku_summary.iterrows():
                f.write(f"  {sku}: {row['fail_rate_%']:.2f}% fail rate ")
                f.write(f"({int(row['failed'])} fails / {int(row['total_checks'])} checks)\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('TIME PATTERNS\n')
        f.write('-' * 70 + '\n')
        
        if 'hour' in df.columns:
            hourly = df.groupby('hour').agg({
                'qc_id': 'count',
                'is_fail': 'sum'
            })
            hourly['fail_rate_%'] = (hourly['is_fail'] / hourly['qc_id'] * 100).round(2)
            
            peak_fail_hour = hourly['fail_rate_%'].idxmax()
            peak_fail_rate = hourly['fail_rate_%'].max()
            low_fail_hour = hourly['fail_rate_%'].idxmin()
            low_fail_rate = hourly['fail_rate_%'].min()
            
            f.write(f'Peak QC Failure Hour: {peak_fail_hour}:00 ({peak_fail_rate:.2f}% fail rate)\n')
            f.write(f'Best QC Performance Hour: {low_fail_hour}:00 ({low_fail_rate:.2f}% fail rate)\n')
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('CRITICAL INSIGHTS & ACTION ITEMS\n')
        f.write('-' * 70 + '\n')
        
        # Generate actionable insights
        if 'pass_fail' in df.columns:
            overall_fail_rate = (df['is_fail'].sum() / len(df) * 100)
            
            if overall_fail_rate > 5:
                f.write(f'⚠️  CRITICAL: {overall_fail_rate:.2f}% QC fail rate (Target: <2%)\n')
                f.write('    Action: Immediate root cause analysis required\n')
            elif overall_fail_rate > 2:
                f.write(f'⚠️  WARNING: {overall_fail_rate:.2f}% QC fail rate (Target: <2%)\n')
                f.write('    Action: Monitor closely, investigate top failure parameters\n')
            else:
                f.write(f'✅ GOOD: {overall_fail_rate:.2f}% QC fail rate (within target <2%)\n')
        
        # Parameter-specific insights
        if 'parameter' in df.columns:
            f.write('\nParameter-Specific Actions:\n')
            param_fails = df[df['is_fail'] == 1].groupby('parameter').size().sort_values(ascending=False).head(3)
            
            for i, (param, count) in enumerate(param_fails.items(), 1):
                f.write(f'  {i}. {param}: {count:,} failures - Investigate tolerance limits\n')
        
        f.write('\n' + '=' * 70 + '\n')
    
    logger.info(f'Wrote {summary_path}')


def grouped_summaries(df: pd.DataFrame, summaries_dir: Path) -> None:
    """Generate grouped summary CSVs for QC analysis."""
    logger.info('Generating grouped summaries')
    
    summaries_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. QC by Parameter
    if 'parameter' in df.columns:
        by_param = df.groupby('parameter').agg({
            'qc_id': 'count',
            'is_pass': 'sum',
            'is_fail': 'sum',
            'value': ['mean', 'std', 'min', 'max'],
            'batch_id': 'nunique'
        }).round(2)
        by_param.columns = ['total_checks', 'passed', 'failed', 'mean_value', 'std_value', 'min_value', 'max_value', 'unique_batches']
        by_param['fail_rate_%'] = (by_param['failed'] / by_param['total_checks'] * 100).round(2)
        by_param = by_param.sort_values('fail_rate_%', ascending=False).reset_index()
        by_param.to_csv(summaries_dir / 'qc_by_parameter.csv', index=False)
        logger.info('Wrote qc_by_parameter.csv')
    
    # 2. QC by SKU
    if 'sku' in df.columns:
        by_sku = df.groupby('sku').agg({
            'qc_id': 'count',
            'is_pass': 'sum',
            'is_fail': 'sum',
            'batch_id': 'nunique'
        }).reset_index()
        by_sku.columns = ['sku', 'total_checks', 'passed', 'failed', 'unique_batches']
        by_sku['fail_rate_%'] = (by_sku['failed'] / by_sku['total_checks'] * 100).round(2)
        by_sku = by_sku.sort_values('fail_rate_%', ascending=False)
        by_sku.to_csv(summaries_dir / 'qc_by_sku.csv', index=False)
        logger.info('Wrote qc_by_sku.csv')
    
    # 3. QC by Batch (batch-level summary)
    if 'batch_id' in df.columns:
        by_batch = df.groupby('batch_id').agg({
            'qc_id': 'count',
            'is_pass': 'sum',
            'is_fail': 'sum',
            'sku': 'first',
            'timestamp': 'first'
        }).reset_index()
        by_batch.columns = ['batch_id', 'total_checks', 'passed', 'failed', 'sku', 'timestamp']
        by_batch['batch_status'] = by_batch['failed'].apply(lambda x: 'FAILED' if x > 0 else 'PASSED')
        by_batch['fail_rate_%'] = (by_batch['failed'] / by_batch['total_checks'] * 100).round(2)
        by_batch = by_batch.sort_values('failed', ascending=False)
        by_batch.to_csv(summaries_dir / 'qc_by_batch.csv', index=False)
        logger.info('Wrote qc_by_batch.csv')
    
    # 4. Failed Batches Detail (for waste/returns linkage)
    failed_batches = df[df['is_fail'] == 1].copy()
    if len(failed_batches) > 0:
        failed_detail = failed_batches.groupby(['batch_id', 'sku', 'parameter']).agg({
            'qc_id': 'count',
            'value': ['mean', 'min', 'max'],
            'notes': lambda x: ' | '.join(x.dropna().astype(str).unique()[:3])
        }).reset_index()
        failed_detail.columns = ['batch_id', 'sku', 'parameter', 'fail_count', 'mean_value', 'min_value', 'max_value', 'notes_sample']
        failed_detail = failed_detail.sort_values('fail_count', ascending=False)
        failed_detail.to_csv(summaries_dir / 'qc_failed_batches_detail.csv', index=False)
        logger.info('Wrote qc_failed_batches_detail.csv')
    
    # 5. QC by Hour (shift pattern analysis)
    if 'hour' in df.columns:
        by_hour = df.groupby('hour').agg({
            'qc_id': 'count',
            'is_pass': 'sum',
            'is_fail': 'sum'
        }).reset_index()
        by_hour.columns = ['hour', 'total_checks', 'passed', 'failed']
        by_hour['fail_rate_%'] = (by_hour['failed'] / by_hour['total_checks'] * 100).round(2)
        by_hour.to_csv(summaries_dir / 'qc_by_hour.csv', index=False)
        logger.info('Wrote qc_by_hour.csv')
    
    # 6. QC by Date (daily quality trends)
    if 'date' in df.columns:
        by_date = df.groupby('date').agg({
            'qc_id': 'count',
            'is_pass': 'sum',
            'is_fail': 'sum',
            'batch_id': 'nunique'
        }).reset_index()
        by_date.columns = ['date', 'total_checks', 'passed', 'failed', 'batches_inspected']
        by_date['fail_rate_%'] = (by_date['failed'] / by_date['total_checks'] * 100).round(2)
        by_date.to_csv(summaries_dir / 'qc_by_date.csv', index=False)
        logger.info('Wrote qc_by_date.csv')


def visualizations(df: pd.DataFrame, figures_dir: Path) -> None:
    """Generate QC visualizations."""
    logger.info('Generating visualizations')
    
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. QC Pass/Fail Rate by Parameter (Bar Chart)
    if 'parameter' in df.columns and 'pass_fail' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 7))
        
        param_summary = df.groupby('parameter').agg({
            'is_pass': 'sum',
            'is_fail': 'sum'
        })
        param_summary['total'] = param_summary['is_pass'] + param_summary['is_fail']
        param_summary['fail_rate_%'] = (param_summary['is_fail'] / param_summary['total'] * 100)
        param_summary = param_summary.sort_values('fail_rate_%', ascending=False)
        
        bars = ax.bar(range(len(param_summary)), param_summary['fail_rate_%'], 
                      color=['red' if x > 5 else 'orange' if x > 2 else 'green' 
                             for x in param_summary['fail_rate_%']])
        ax.set_xticks(range(len(param_summary)))
        ax.set_xticklabels(param_summary.index, rotation=45, ha='right')
        ax.set_ylabel('QC Fail Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('QC Fail Rate by Parameter (Red >5%, Orange >2%, Green ≤2%)', 
                     fontsize=14, fontweight='bold')
        ax.axhline(y=2, color='blue', linestyle='--', linewidth=2, label='Target: 2%')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for i, (idx, row) in enumerate(param_summary.iterrows()):
            ax.text(i, row['fail_rate_%'] + 0.3, f"{row['fail_rate_%']:.1f}%", 
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'qc_fail_rate_by_parameter.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved qc_fail_rate_by_parameter.png')
    
    # 2. QC Value Distribution by Parameter (Box Plot)
    if 'parameter' in df.columns and 'value' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Filter numeric values
        df_numeric = df[pd.to_numeric(df['value'], errors='coerce').notna()].copy()
        df_numeric['value'] = pd.to_numeric(df_numeric['value'])
        
        if len(df_numeric) > 0:
            param_order = df_numeric.groupby('parameter')['value'].median().sort_values().index
            
            sns.boxplot(data=df_numeric, y='parameter', x='value', order=param_order, 
                       palette='Set2', ax=ax)
            ax.set_xlabel('Measurement Value', fontsize=12, fontweight='bold')
            ax.set_ylabel('QC Parameter', fontsize=12, fontweight='bold')
            ax.set_title('QC Parameter Value Distributions (Box Plot)', 
                        fontsize=14, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(figures_dir / 'qc_value_distribution_by_parameter.png', dpi=300, bbox_inches='tight')
            plt.close()
            logger.info('Saved qc_value_distribution_by_parameter.png')
    
    # 3. QC Pass/Fail Over Time (Line Chart)
    if 'date' in df.columns and 'pass_fail' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        daily_qc = df.groupby('date').agg({
            'is_fail': 'sum',
            'qc_id': 'count'
        }).reset_index()
        daily_qc['fail_rate_%'] = (daily_qc['is_fail'] / daily_qc['qc_id'] * 100)
        
        ax.plot(daily_qc['date'], daily_qc['fail_rate_%'], marker='o', 
               linewidth=2, markersize=4, color='red', label='Daily Fail Rate')
        ax.axhline(y=daily_qc['fail_rate_%'].mean(), color='blue', linestyle='--', 
                  linewidth=2, label=f"Average: {daily_qc['fail_rate_%'].mean():.2f}%")
        ax.axhline(y=2, color='green', linestyle='--', linewidth=2, label='Target: 2%')
        
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('QC Fail Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('QC Fail Rate Trend Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'qc_fail_rate_timeseries.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved qc_fail_rate_timeseries.png')
    
    # 4. QC Fail Rate by SKU (Horizontal Bar - Top 10)
    if 'sku' in df.columns and 'pass_fail' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        sku_summary = df.groupby('sku').agg({
            'is_fail': 'sum',
            'qc_id': 'count'
        })
        sku_summary['fail_rate_%'] = (sku_summary['is_fail'] / sku_summary['qc_id'] * 100)
        sku_summary = sku_summary.sort_values('fail_rate_%', ascending=True).tail(10)
        
        bars = ax.barh(range(len(sku_summary)), sku_summary['fail_rate_%'], 
                       color=['red' if x > 5 else 'orange' if x > 2 else 'yellow' 
                              for x in sku_summary['fail_rate_%']])
        ax.set_yticks(range(len(sku_summary)))
        ax.set_yticklabels(sku_summary.index)
        ax.set_xlabel('QC Fail Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('Top 10 SKUs by QC Fail Rate', fontsize=14, fontweight='bold')
        ax.axvline(x=2, color='green', linestyle='--', linewidth=2, label='Target: 2%')
        ax.legend()
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, (idx, val) in enumerate(sku_summary['fail_rate_%'].items()):
            ax.text(val + 0.2, i, f"{val:.1f}%", va='center', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'qc_fail_rate_by_sku.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved qc_fail_rate_by_sku.png')
    
    # 5. QC Hourly Pattern (Shift Analysis)
    if 'hour' in df.columns and 'pass_fail' in df.columns:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        hourly = df.groupby('hour').agg({
            'qc_id': 'count',
            'is_fail': 'sum'
        }).reset_index()
        hourly['fail_rate_%'] = (hourly['is_fail'] / hourly['qc_id'] * 100)
        
        # Top: Fail rate by hour
        ax1.plot(hourly['hour'], hourly['fail_rate_%'], marker='o', 
                linewidth=2, markersize=6, color='red')
        ax1.axhline(y=2, color='green', linestyle='--', linewidth=2, label='Target: 2%')
        ax1.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Fail Rate (%)', fontsize=12, fontweight='bold')
        ax1.set_title('QC Fail Rate by Hour (Shift Pattern Analysis)', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(alpha=0.3)
        ax1.set_xticks(range(0, 24))
        
        # Bottom: Check volume by hour
        ax2.bar(hourly['hour'], hourly['qc_id'], color='steelblue', alpha=0.7)
        ax2.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Number of QC Checks', fontsize=12, fontweight='bold')
        ax2.set_title('QC Check Volume by Hour', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        ax2.set_xticks(range(0, 24))
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'qc_hourly_pattern.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved qc_hourly_pattern.png')
    
    # 6. Pass vs Fail Count Comparison (Pie Chart)
    if 'pass_fail' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        pass_fail_counts = df['pass_fail'].value_counts()
        colors = ['green' if x.lower() == 'pass' else 'red' for x in pass_fail_counts.index]
        
        wedges, texts, autotexts = ax.pie(pass_fail_counts, labels=pass_fail_counts.index, 
                                           autopct='%1.1f%%', colors=colors, startangle=90,
                                           textprops={'fontsize': 12, 'fontweight': 'bold'})
        
        # Make percentage text bold and white
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(14)
        
        ax.set_title(f'QC Pass vs Fail Distribution\nTotal Checks: {len(df):,}', 
                    fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'qc_pass_fail_pie.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved qc_pass_fail_pie.png')
    
    # 7. Failed Batches by Parameter (Stacked Bar)
    if 'parameter' in df.columns and 'batch_id' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 7))
        
        failed_only = df[df['is_fail'] == 1]
        if len(failed_only) > 0:
            param_batch_fails = failed_only.groupby('parameter')['batch_id'].nunique().sort_values(ascending=False).head(10)
            
            bars = ax.bar(range(len(param_batch_fails)), param_batch_fails.values, color='darkred')
            ax.set_xticks(range(len(param_batch_fails)))
            ax.set_xticklabels(param_batch_fails.index, rotation=45, ha='right')
            ax.set_ylabel('Number of Failed Batches', fontsize=12, fontweight='bold')
            ax.set_title('Failed Batches by QC Parameter (Top 10 Problem Parameters)', 
                        fontsize=14, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            
            # Add value labels
            for i, val in enumerate(param_batch_fails.values):
                ax.text(i, val + 5, str(int(val)), ha='center', va='bottom', 
                       fontsize=10, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(figures_dir / 'qc_failed_batches_by_parameter.png', dpi=300, bbox_inches='tight')
            plt.close()
            logger.info('Saved qc_failed_batches_by_parameter.png')
    
    # 8. QC Check Volume Distribution (Histogram)
    if 'batch_id' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        checks_per_batch = df.groupby('batch_id').size()
        
        ax.hist(checks_per_batch, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
        ax.axvline(checks_per_batch.mean(), color='red', linestyle='--', linewidth=2, 
                  label=f'Mean: {checks_per_batch.mean():.1f}')
        ax.axvline(checks_per_batch.median(), color='green', linestyle='--', linewidth=2, 
                  label=f'Median: {checks_per_batch.median():.1f}')
        
        ax.set_xlabel('QC Checks per Batch', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency (Number of Batches)', fontsize=12, fontweight='bold')
        ax.set_title('Distribution of QC Check Intensity per Batch', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'qc_checks_per_batch_hist.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved qc_checks_per_batch_hist.png')


def main():
    """Main execution function."""
    # Paths
    data_path = Path('data/processed/quality_control_dataset.parquet')
    reports_dir = Path('reports')
    summaries_dir = reports_dir / 'summaries'
    figures_dir = reports_dir / 'figures'
    
    # Load and prepare data
    df = load_and_prepare(data_path)
    
    # Generate outputs
    summary_stats(df, reports_dir)
    grouped_summaries(df, summaries_dir)
    visualizations(df, figures_dir)
    
    logger.info('✅ Quality Control EDA complete!')


if __name__ == '__main__':
    main()
