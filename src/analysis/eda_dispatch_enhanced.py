"""Enhanced EDA for Dispatch Dataset.

Critical supply chain link: Production → QC → DISPATCH → Retailer → Sales
Controls product freshness, delivery efficiency, and service levels.

Analyzes:
- On-time delivery performance (expected vs actual arrival)
- Dispatch delays by route, vehicle, plant, SKU
- Route efficiency and bottlenecks
- Vehicle and driver performance patterns
- Retailer service levels
- SKU freshness windows
- Time patterns (hour, day of week)
- Volume vs delay correlation

Key Fields:
- dispatch_id: Unique dispatch event identifier
- timestamp: When truck leaves bakery/depot
- plant_id: Origin plant
- route_id: Delivery route (links to route metadata)
- vehicle_id: Truck used for delivery
- retailer_id: Destination store
- sku: Product being dispatched
- qty_dispatched: Units sent
- expected_arrival: Planned arrival time
- actual_arrival: Real arrival time
- dispatch_delay_minutes: (actual - expected) in minutes

Outputs:
- reports/dispatch_summary.txt (comprehensive dispatch performance report)
- reports/summaries/dispatch_*.csv (route, vehicle, SKU, retailer summaries)
- reports/figures/dispatch_*.png (8+ visualizations)

Usage:
    python src/analysis/eda_dispatch.py
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
    """Load dispatch dataset and compute delays."""
    logger.info(f'Loading {path}')
    df = pd.read_parquet(path)
    
    # Parse datetime columns
    for col in ['timestamp', 'expected_arrival', 'actual_arrival']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Compute dispatch delay in minutes
    if 'expected_arrival' in df.columns and 'actual_arrival' in df.columns:
        df['dispatch_delay_minutes'] = (
            (df['actual_arrival'] - df['expected_arrival']).dt.total_seconds() / 60.0
        )
        # Create delay categories
        df['delay_category'] = pd.cut(
            df['dispatch_delay_minutes'],
            bins=[-np.inf, -30, 0, 30, 60, np.inf],
            labels=['Very Early (>30min)', 'Early (<30min)', 'On-Time (±30min)', 'Late (30-60min)', 'Very Late (>60min)']
        )
        # On-time flag (within ±30 minutes)
        df['on_time'] = df['dispatch_delay_minutes'].between(-30, 30).astype(int)
    
    # Derive time features
    if 'timestamp' in df.columns:
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['dayofweek'] = df['timestamp'].dt.day_name()
    
    logger.info(f'Loaded {len(df):,} dispatch events')
    return df


def summary_stats(df: pd.DataFrame, output_dir: Path) -> None:
    """Generate comprehensive dispatch summary statistics."""
    logger.info('Generating dispatch summary statistics')
    
    summary_path = output_dir / 'dispatch_summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('=' * 70 + '\n')
        f.write('DISPATCH DATASET SUMMARY\n')
        f.write('=' * 70 + '\n')
        f.write(f'Dataset Shape: {df.shape[0]:,} dispatch events × {df.shape[1]} columns\n')
        
        if 'timestamp' in df.columns:
            f.write(f"Date Range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('DISPATCH VOLUME OVERVIEW\n')
        f.write('-' * 70 + '\n')
        
        if 'qty_dispatched' in df.columns:
            total_qty = df['qty_dispatched'].sum()
            mean_qty = df['qty_dispatched'].mean()
            f.write(f'Total Units Dispatched: {total_qty:,.0f}\n')
            f.write(f'Mean Dispatch Quantity: {mean_qty:,.1f} units per trip\n')
            f.write(f'Total Dispatch Events: {len(df):,}\n')
        
        # Plant distribution
        if 'plant_id' in df.columns:
            f.write(f"\nPlants Dispatching: {df['plant_id'].nunique()}\n")
            plant_counts = df['plant_id'].value_counts()
            for plant, count in plant_counts.items():
                pct = count / len(df) * 100
                f.write(f"  {plant}: {count:,} dispatches ({pct:.1f}%)\n")
        
        # Route distribution
        if 'route_id' in df.columns:
            unique_routes = df['route_id'].nunique()
            f.write(f'\nUnique Routes: {unique_routes}\n')
            f.write(f'Avg Dispatches per Route: {len(df) / unique_routes:.1f}\n')
        
        # Vehicle distribution
        if 'vehicle_id' in df.columns:
            unique_vehicles = df['vehicle_id'].nunique()
            f.write(f'\nUnique Vehicles: {unique_vehicles}\n')
            f.write(f'Avg Dispatches per Vehicle: {len(df) / unique_vehicles:.1f}\n')
        
        # Retailer distribution
        if 'retailer_id' in df.columns:
            unique_retailers = df['retailer_id'].nunique()
            f.write(f'\nUnique Retailers Served: {unique_retailers}\n')
            f.write(f'Avg Deliveries per Retailer: {len(df) / unique_retailers:.1f}\n')
        
        # SKU distribution
        if 'sku' in df.columns:
            unique_skus = df['sku'].nunique()
            f.write(f'\nUnique SKUs Dispatched: {unique_skus}\n')
            top_skus = df['sku'].value_counts().head(5)
            f.write('\nTop 5 SKUs by Dispatch Count:\n')
            for sku, count in top_skus.items():
                pct = count / len(df) * 100
                f.write(f"  {sku}: {count:,} dispatches ({pct:.1f}%)\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('ON-TIME DELIVERY PERFORMANCE\n')
        f.write('-' * 70 + '\n')
        
        if 'dispatch_delay_minutes' in df.columns:
            mean_delay = df['dispatch_delay_minutes'].mean()
            median_delay = df['dispatch_delay_minutes'].median()
            p95_delay = df['dispatch_delay_minutes'].quantile(0.95)
            
            f.write(f'Mean Delay: {mean_delay:.1f} minutes\n')
            f.write(f'Median Delay: {median_delay:.1f} minutes\n')
            f.write(f'95th Percentile Delay: {p95_delay:.1f} minutes\n')
            
            # On-time percentage
            if 'on_time' in df.columns:
                on_time_pct = df['on_time'].mean() * 100
                f.write(f'\n✅ On-Time Delivery Rate: {on_time_pct:.2f}%')
                f.write(' (within ±30 minutes)\n')
                
                if on_time_pct < 80:
                    f.write('⚠️  WARNING: On-time rate below 80% target\n')
                elif on_time_pct < 90:
                    f.write('⚠️  ALERT: On-time rate below 90% target\n')
                else:
                    f.write('✅ Good: On-time rate above 90%\n')
            
            # Delay categories
            if 'delay_category' in df.columns:
                f.write('\nDelay Category Breakdown:\n')
                delay_dist = df['delay_category'].value_counts()
                for cat, count in delay_dist.items():
                    pct = count / len(df) * 100
                    f.write(f"  {cat}: {count:,} ({pct:.1f}%)\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('ROUTE PERFORMANCE\n')
        f.write('-' * 70 + '\n')
        
        if 'route_id' in df.columns and 'dispatch_delay_minutes' in df.columns:
            route_perf = df.groupby('route_id').agg({
                'dispatch_delay_minutes': ['count', 'mean', 'median'],
                'on_time': 'mean'
            })
            route_perf.columns = ['trips', 'mean_delay', 'median_delay', 'on_time_rate']
            route_perf['on_time_pct'] = route_perf['on_time_rate'] * 100
            route_perf = route_perf.sort_values('mean_delay', ascending=False).head(10)
            
            f.write('Top 10 Routes with Longest Delays:\n')
            for route, row in route_perf.iterrows():
                f.write(f"  {route}: {row['mean_delay']:.1f} min avg delay ")
                f.write(f"({row['on_time_pct']:.1f}% on-time, {int(row['trips'])} trips)\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('VEHICLE PERFORMANCE\n')
        f.write('-' * 70 + '\n')
        
        if 'vehicle_id' in df.columns and 'dispatch_delay_minutes' in df.columns:
            vehicle_perf = df.groupby('vehicle_id').agg({
                'dispatch_delay_minutes': ['count', 'mean'],
                'on_time': 'mean'
            })
            vehicle_perf.columns = ['trips', 'mean_delay', 'on_time_rate']
            vehicle_perf['on_time_pct'] = vehicle_perf['on_time_rate'] * 100
            vehicle_perf = vehicle_perf[vehicle_perf['trips'] >= 10]  # Min 10 trips
            worst_vehicles = vehicle_perf.sort_values('mean_delay', ascending=False).head(5)
            
            f.write('Top 5 Vehicles with Longest Delays (min 10 trips):\n')
            for vehicle, row in worst_vehicles.iterrows():
                f.write(f"  {vehicle}: {row['mean_delay']:.1f} min avg delay ")
                f.write(f"({row['on_time_pct']:.1f}% on-time, {int(row['trips'])} trips)\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('TIME PATTERNS\n')
        f.write('-' * 70 + '\n')
        
        if 'hour' in df.columns and 'dispatch_delay_minutes' in df.columns:
            hourly = df.groupby('hour').agg({
                'dispatch_delay_minutes': 'mean',
                'dispatch_id': 'count'
            })
            peak_hour = hourly['dispatch_delay_minutes'].idxmax()
            peak_delay = hourly['dispatch_delay_minutes'].max()
            best_hour = hourly['dispatch_delay_minutes'].idxmin()
            best_delay = hourly['dispatch_delay_minutes'].min()
            
            f.write(f'Peak Delay Hour: {peak_hour}:00 ({peak_delay:.1f} min avg delay)\n')
            f.write(f'Best Performance Hour: {best_hour}:00 ({best_delay:.1f} min avg delay)\n')
        
        if 'dayofweek' in df.columns and 'dispatch_delay_minutes' in df.columns:
            daily = df.groupby('dayofweek')['dispatch_delay_minutes'].mean()
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            daily = daily.reindex([d for d in days_order if d in daily.index])
            
            f.write('\nAverage Delay by Day of Week:\n')
            for day, delay in daily.items():
                f.write(f"  {day}: {delay:.1f} minutes\n")
        
        f.write('\n' + '-' * 70 + '\n')
        f.write('CRITICAL INSIGHTS & ACTION ITEMS\n')
        f.write('-' * 70 + '\n')
        
        if 'on_time' in df.columns:
            on_time_rate = df['on_time'].mean() * 100
            if on_time_rate < 80:
                f.write(f'⚠️  CRITICAL: {on_time_rate:.1f}% on-time rate (Target: >90%)\n')
                f.write('    Action: Immediate route optimization and vehicle review\n')
            elif on_time_rate < 90:
                f.write(f'⚠️  WARNING: {on_time_rate:.1f}% on-time rate (Target: >90%)\n')
                f.write('    Action: Review worst-performing routes and vehicles\n')
            else:
                f.write(f'✅ GOOD: {on_time_rate:.1f}% on-time rate (above 90% target)\n')
        
        f.write('\n' + '=' * 70 + '\n')
    
    logger.info(f'Wrote {summary_path}')


def grouped_summaries(df: pd.DataFrame, summaries_dir: Path) -> None:
    """Generate grouped summary CSVs for dispatch analysis."""
    logger.info('Generating grouped summaries')
    
    summaries_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Dispatch by Plant
    if 'plant_id' in df.columns:
        by_plant = df.groupby('plant_id').agg({
            'dispatch_id': 'count',
            'qty_dispatched': ['sum', 'mean'],
            'dispatch_delay_minutes': ['mean', 'median'],
            'on_time': 'mean',
            'route_id': 'nunique',
            'vehicle_id': 'nunique',
            'retailer_id': 'nunique'
        }).round(2)
        by_plant.columns = ['total_dispatches', 'total_qty', 'mean_qty_per_dispatch', 
                            'mean_delay_min', 'median_delay_min', 'on_time_rate',
                            'unique_routes', 'unique_vehicles', 'unique_retailers']
        by_plant['on_time_pct'] = (by_plant['on_time_rate'] * 100).round(2)
        by_plant.to_csv(summaries_dir / 'dispatch_by_plant.csv')
        logger.info('Wrote dispatch_by_plant.csv')
    
    # 2. Dispatch by Route
    if 'route_id' in df.columns:
        by_route = df.groupby('route_id').agg({
            'dispatch_id': 'count',
            'qty_dispatched': ['sum', 'mean'],
            'dispatch_delay_minutes': ['mean', 'median', 'std'],
            'on_time': 'mean',
            'retailer_id': 'nunique'
        }).round(2)
        by_route.columns = ['total_dispatches', 'total_qty', 'mean_qty', 
                           'mean_delay_min', 'median_delay_min', 'std_delay_min',
                           'on_time_rate', 'unique_retailers']
        by_route['on_time_pct'] = (by_route['on_time_rate'] * 100).round(2)
        by_route = by_route.sort_values('mean_delay_min', ascending=False)
        by_route.to_csv(summaries_dir / 'dispatch_by_route.csv')
        logger.info('Wrote dispatch_by_route.csv')
    
    # 3. Dispatch by Vehicle
    if 'vehicle_id' in df.columns:
        by_vehicle = df.groupby('vehicle_id').agg({
            'dispatch_id': 'count',
            'qty_dispatched': 'sum',
            'dispatch_delay_minutes': ['mean', 'median'],
            'on_time': 'mean',
            'route_id': 'nunique'
        }).round(2)
        by_vehicle.columns = ['total_trips', 'total_qty', 'mean_delay_min', 
                             'median_delay_min', 'on_time_rate', 'unique_routes']
        by_vehicle['on_time_pct'] = (by_vehicle['on_time_rate'] * 100).round(2)
        by_vehicle = by_vehicle.sort_values('mean_delay_min', ascending=False)
        by_vehicle.to_csv(summaries_dir / 'dispatch_by_vehicle.csv')
        logger.info('Wrote dispatch_by_vehicle.csv')
    
    # 4. Dispatch by SKU
    if 'sku' in df.columns:
        by_sku = df.groupby('sku').agg({
            'dispatch_id': 'count',
            'qty_dispatched': ['sum', 'mean'],
            'dispatch_delay_minutes': ['mean', 'median'],
            'on_time': 'mean'
        }).round(2)
        by_sku.columns = ['total_dispatches', 'total_qty', 'mean_qty', 
                         'mean_delay_min', 'median_delay_min', 'on_time_rate']
        by_sku['on_time_pct'] = (by_sku['on_time_rate'] * 100).round(2)
        by_sku = by_sku.sort_values('total_qty', ascending=False)
        by_sku.to_csv(summaries_dir / 'dispatch_by_sku.csv')
        logger.info('Wrote dispatch_by_sku.csv')
    
    # 5. Dispatch by Retailer
    if 'retailer_id' in df.columns:
        by_retailer = df.groupby('retailer_id').agg({
            'dispatch_id': 'count',
            'qty_dispatched': 'sum',
            'dispatch_delay_minutes': 'mean',
            'on_time': 'mean'
        }).round(2)
        by_retailer.columns = ['total_deliveries', 'total_qty', 'mean_delay_min', 'on_time_rate']
        by_retailer['on_time_pct'] = (by_retailer['on_time_rate'] * 100).round(2)
        by_retailer = by_retailer.sort_values('total_qty', ascending=False).head(50)  # Top 50
        by_retailer.to_csv(summaries_dir / 'dispatch_by_retailer_top50.csv')
        logger.info('Wrote dispatch_by_retailer_top50.csv')
    
    # 6. Dispatch by Hour
    if 'hour' in df.columns:
        by_hour = df.groupby('hour').agg({
            'dispatch_id': 'count',
            'dispatch_delay_minutes': 'mean',
            'on_time': 'mean'
        }).round(2)
        by_hour.columns = ['dispatch_count', 'mean_delay_min', 'on_time_rate']
        by_hour['on_time_pct'] = (by_hour['on_time_rate'] * 100).round(2)
        by_hour.to_csv(summaries_dir / 'dispatch_by_hour.csv')
        logger.info('Wrote dispatch_by_hour.csv')


def visualizations(df: pd.DataFrame, figures_dir: Path) -> None:
    """Generate dispatch visualizations."""
    logger.info('Generating visualizations')
    
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Dispatch Delay Distribution (Histogram)
    if 'dispatch_delay_minutes' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        delays = df['dispatch_delay_minutes'].dropna()
        ax.hist(delays, bins=100, color='steelblue', alpha=0.7, edgecolor='black')
        ax.axvline(delays.mean(), color='red', linestyle='--', linewidth=2, 
                  label=f'Mean: {delays.mean():.1f} min')
        ax.axvline(delays.median(), color='green', linestyle='--', linewidth=2, 
                  label=f'Median: {delays.median():.1f} min')
        ax.axvline(0, color='blue', linestyle='-', linewidth=2, label='On-Time (0 min)')
        
        ax.set_xlabel('Dispatch Delay (minutes)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title('Distribution of Dispatch Delays', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_delay_hist.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_delay_hist.png')
    
    # 2. Delay by Route (Box Plot - Top 20 busiest routes)
    if 'route_id' in df.columns and 'dispatch_delay_minutes' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 7))
        
        top_routes = df['route_id'].value_counts().nlargest(20).index
        df_top = df[df['route_id'].isin(top_routes)]
        
        route_order = df_top.groupby('route_id')['dispatch_delay_minutes'].median().sort_values().index
        
        sns.boxplot(data=df_top, x='route_id', y='dispatch_delay_minutes', 
                   order=route_order, palette='Set2', ax=ax)
        ax.axhline(y=0, color='blue', linestyle='--', linewidth=2, label='On-Time')
        ax.set_xlabel('Route ID', fontsize=12, fontweight='bold')
        ax.set_ylabel('Dispatch Delay (minutes)', fontsize=12, fontweight='bold')
        ax.set_title('Dispatch Delay by Route (Top 20 Busiest Routes)', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_delay_by_route_box.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_delay_by_route_box.png')
    
    # 3. Delay Heatmap (Hour vs Day of Week)
    if 'hour' in df.columns and 'dayofweek' in df.columns and 'dispatch_delay_minutes' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        pivot = df.pivot_table(index='dayofweek', columns='hour', 
                              values='dispatch_delay_minutes', aggfunc='mean')
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        pivot = pivot.reindex([d for d in days_order if d in pivot.index])
        
        sns.heatmap(pivot, cmap='RdYlGn_r', center=0, annot=False, 
                   fmt='.1f', cbar_kws={'label': 'Mean Delay (minutes)'}, ax=ax)
        ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
        ax.set_ylabel('Day of Week', fontsize=12, fontweight='bold')
        ax.set_title('Dispatch Delay Pattern: Hour × Day of Week', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'delay_hour_day_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved delay_hour_day_heatmap.png')
    
    # 4. On-Time Delivery Rate by Route (Top 20)
    if 'route_id' in df.columns and 'on_time' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        route_ontime = df.groupby('route_id').agg({
            'on_time': 'mean',
            'dispatch_id': 'count'
        })
        route_ontime = route_ontime[route_ontime['dispatch_id'] >= 10]  # Min 10 trips
        route_ontime['on_time_pct'] = route_ontime['on_time'] * 100
        route_ontime = route_ontime.sort_values('on_time_pct', ascending=True).tail(20)
        
        colors = ['red' if x < 80 else 'orange' if x < 90 else 'green' 
                 for x in route_ontime['on_time_pct']]
        
        bars = ax.barh(range(len(route_ontime)), route_ontime['on_time_pct'], color=colors)
        ax.set_yticks(range(len(route_ontime)))
        ax.set_yticklabels(route_ontime.index)
        ax.set_xlabel('On-Time Delivery Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('On-Time Delivery Rate by Route (Top 20, min 10 trips)', 
                    fontsize=14, fontweight='bold')
        ax.axvline(x=90, color='blue', linestyle='--', linewidth=2, label='Target: 90%')
        ax.legend()
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, val in enumerate(route_ontime['on_time_pct']):
            ax.text(val + 1, i, f'{val:.1f}%', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_ontime_by_route.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_ontime_by_route.png')
    
    # 5. Dispatch Volume by SKU (Horizontal Bar)
    if 'sku' in df.columns and 'qty_dispatched' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        sku_qty = df.groupby('sku')['qty_dispatched'].sum().sort_values(ascending=True).tail(10)
        
        bars = ax.barh(range(len(sku_qty)), sku_qty.values, color='steelblue')
        ax.set_yticks(range(len(sku_qty)))
        ax.set_yticklabels(sku_qty.index)
        ax.set_xlabel('Total Quantity Dispatched', fontsize=12, fontweight='bold')
        ax.set_title('Top 10 SKUs by Dispatch Volume', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, val in enumerate(sku_qty.values):
            ax.text(val + max(sku_qty)*0.01, i, f'{val:,.0f}', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_volume_by_sku.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_volume_by_sku.png')
    
    # 6. Delay Category Distribution (Pie Chart)
    if 'delay_category' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        delay_counts = df['delay_category'].value_counts()
        colors_pie = ['darkred', 'orange', 'green', 'yellow', 'red']
        
        wedges, texts, autotexts = ax.pie(delay_counts, labels=delay_counts.index, 
                                           autopct='%1.1f%%', colors=colors_pie, startangle=90,
                                           textprops={'fontsize': 11, 'fontweight': 'bold'})
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title(f'Dispatch Delay Category Distribution\nTotal Dispatches: {len(df):,}', 
                    fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_delay_category_pie.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_delay_category_pie.png')
    
    # 7. Daily Dispatch Volume Timeseries
    if 'date' in df.columns:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        daily_volume = df.groupby('date').agg({
            'dispatch_id': 'count',
            'qty_dispatched': 'sum'
        })
        
        ax.plot(daily_volume.index, daily_volume['dispatch_id'], 
               marker='o', linewidth=2, markersize=4, color='steelblue', label='Dispatch Count')
        ax.axhline(daily_volume['dispatch_id'].mean(), color='red', linestyle='--', 
                  linewidth=2, label=f"Avg: {daily_volume['dispatch_id'].mean():.1f}")
        
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Dispatches', fontsize=12, fontweight='bold')
        ax.set_title('Daily Dispatch Volume Over Time', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_volume_timeseries.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_volume_timeseries.png')
    
    # 8. Vehicle Performance (Mean Delay - Top 15 worst)
    if 'vehicle_id' in df.columns and 'dispatch_delay_minutes' in df.columns:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        vehicle_perf = df.groupby('vehicle_id').agg({
            'dispatch_delay_minutes': 'mean',
            'dispatch_id': 'count'
        })
        vehicle_perf = vehicle_perf[vehicle_perf['dispatch_id'] >= 10]  # Min 10 trips
        vehicle_perf = vehicle_perf.sort_values('dispatch_delay_minutes', ascending=True).tail(15)
        
        colors_veh = ['red' if x > 60 else 'orange' if x > 30 else 'yellow' 
                     for x in vehicle_perf['dispatch_delay_minutes']]
        
        bars = ax.barh(range(len(vehicle_perf)), vehicle_perf['dispatch_delay_minutes'], color=colors_veh)
        ax.set_yticks(range(len(vehicle_perf)))
        ax.set_yticklabels(vehicle_perf.index)
        ax.set_xlabel('Mean Delay (minutes)', fontsize=12, fontweight='bold')
        ax.set_title('Top 15 Vehicles with Longest Delays (min 10 trips)', 
                    fontsize=14, fontweight='bold')
        ax.axvline(x=30, color='blue', linestyle='--', linewidth=2, label='Target: <30 min')
        ax.legend()
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, val in enumerate(vehicle_perf['dispatch_delay_minutes']):
            ax.text(val + 2, i, f'{val:.1f}', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(figures_dir / 'dispatch_delay_by_vehicle.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info('Saved dispatch_delay_by_vehicle.png')


def main():
    """Main execution function."""
    # Paths
    data_path = Path('data/processed/dispatch_dataset.parquet')
    reports_dir = Path('reports')
    summaries_dir = reports_dir / 'summaries'
    figures_dir = reports_dir / 'figures'
    
    # Load and prepare data
    df = load_and_prepare(data_path)
    
    # Generate outputs
    summary_stats(df, reports_dir)
    grouped_summaries(df, summaries_dir)
    visualizations(df, figures_dir)
    
    logger.info('✅ Dispatch EDA complete!')


if __name__ == '__main__':
    main()
