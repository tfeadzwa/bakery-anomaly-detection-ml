"""
Enhanced EDA for Sales Dataset (B2B Channel) - Wholesale/Depot Distribution

Business Context:
================
The Sales Dataset captures B2B wholesale transactions where depots distribute products 
to stores/retailers. This is distinct from Sales POS (B2C retail transactions):

- Sales Dataset (THIS) = B2B channel: Depot → Store (wholesale orders)
- Sales POS = B2C channel: Retailer → Consumer (retail transactions)

Key Business Questions:
1. How do depot-to-store orders differ from retail POS patterns?
2. Which depots are highest volume distributors?
3. Are wholesale order sizes larger than retail transactions?
4. Do stores order different SKU mixes than retail POS demand?
5. Which routes connect depots to stores most efficiently?
6. Is wholesale pricing lower than retail (expected margin structure)?

Critical Links:
- Depots distribute to Stores (this dataset)
- Stores then sell to consumers (Sales POS dataset)
- Can correlate: Depot orders → Store POS sales for inventory optimization
- Route performance impacts both depot distribution and store freshness

Analysis Focus:
- Depot performance (volume, SKU mix, store coverage)
- Store ordering patterns (frequency, volume, SKU preferences)
- Route efficiency (which routes serve which depot-store pairs)
- Pricing analysis (wholesale vs retail margin validation)
- Temporal patterns (B2B ordering behavior vs B2C demand patterns)
- Depot-Store-Route network optimization opportunities
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# Paths
DATA_DIR = Path('data/processed')
REPORTS_DIR = Path('reports')
FIGURES_DIR = REPORTS_DIR / 'figures'
SUMMARIES_DIR = REPORTS_DIR / 'summaries'

# Ensure output directories exist
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

# Styling
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_and_prepare():
    """
    Load Sales Dataset (B2B channel) and prepare time-based features.
    
    Returns:
        pd.DataFrame: Cleaned and feature-enriched dataframe
    """
    df = pd.read_parquet(DATA_DIR / 'sales_dataset.parquet')
    logging.info(f"Loaded {len(df):,} B2B sales records")
    
    # Handle missing values
    initial_rows = len(df)
    df = df.dropna(subset=['timestamp', 'store_id', 'sku', 'quantity_sold'])
    logging.info(f"Dropped {initial_rows - len(df):,} rows with critical missing values")
    
    # Fill missing depot_id (some may be direct store orders)
    df['depot_id'] = df['depot_id'].fillna('DIRECT')
    
    # Fill missing route_id
    df['route_id'] = df['route_id'].fillna('UNKNOWN')
    
    # Fill missing price with median per SKU
    df['price_per_unit'] = df.groupby('sku')['price_per_unit'].transform(
        lambda x: x.fillna(x.median())
    )
    
    # Derive time features
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    df['week'] = df['timestamp'].dt.isocalendar().week
    df['month'] = df['timestamp'].dt.month
    df['month_name'] = df['timestamp'].dt.month_name()
    
    # Derive revenue
    df['revenue'] = df['quantity_sold'] * df['price_per_unit']
    
    # Extract region from depot name (if possible)
    df['depot_region'] = df['depot_id'].apply(lambda x: x.split('_')[0] if '_' in str(x) else 'DIRECT')
    
    logging.info(f"Final dataset: {len(df):,} records with {df['quantity_sold'].sum():,} units sold")
    logging.info(f"Total revenue: ${df['revenue'].sum():,.2f}")
    
    return df


def summary_stats(df):
    """
    Generate comprehensive summary statistics for B2B Sales Dataset.
    
    Focus Areas:
    - Depot distribution performance
    - Store ordering patterns
    - Route efficiency
    - SKU demand by depot/store
    - Pricing structure (wholesale vs retail validation)
    - Temporal ordering patterns
    - Network optimization opportunities (depot-route-store)
    """
    lines = []
    lines.append("=" * 80)
    lines.append("SALES DATASET (B2B CHANNEL) - ENHANCED SUMMARY REPORT")
    lines.append("Analysis Period: Wholesale/Depot Distribution to Stores")
    lines.append("=" * 80)
    lines.append("")
    
    # === 1. OVERALL METRICS ===
    lines.append("=" * 80)
    lines.append("1. OVERALL B2B SALES METRICS")
    lines.append("=" * 80)
    
    total_records = len(df)
    total_units = df['quantity_sold'].sum()
    total_revenue = df['revenue'].sum()
    n_stores = df['store_id'].nunique()
    n_depots = df['depot_id'].nunique()
    n_routes = df['route_id'].nunique()
    n_skus = df['sku'].nunique()
    
    lines.append(f"Total B2B Orders: {total_records:,}")
    lines.append(f"Total Units Distributed: {total_units:,}")
    lines.append(f"Total Revenue (Wholesale): ${total_revenue:,.2f}")
    lines.append(f"Unique Stores Served: {n_stores}")
    lines.append(f"Active Depots: {n_depots}")
    lines.append(f"Distribution Routes: {n_routes}")
    lines.append(f"SKUs Distributed: {n_skus}")
    lines.append(f"Average Order Size: {total_units / total_records:.1f} units")
    lines.append(f"Average Order Value: ${total_revenue / total_records:.2f}")
    lines.append(f"Average Wholesale Price: ${df['price_per_unit'].mean():.2f}/unit")
    lines.append("")
    
    # === 2. DEPOT PERFORMANCE ===
    lines.append("=" * 80)
    lines.append("2. DEPOT DISTRIBUTION PERFORMANCE")
    lines.append("=" * 80)
    
    depot_stats = df.groupby('depot_id').agg({
        'quantity_sold': ['sum', 'count'],
        'revenue': 'sum',
        'store_id': 'nunique',
        'route_id': 'nunique'
    }).round(2)
    depot_stats.columns = ['Total_Units', 'Orders', 'Revenue', 'Stores_Served', 'Routes_Used']
    depot_stats = depot_stats.sort_values('Total_Units', ascending=False)
    depot_stats['Units_Pct'] = (depot_stats['Total_Units'] / total_units * 100).round(2)
    depot_stats['Revenue_Pct'] = (depot_stats['Revenue'] / total_revenue * 100).round(2)
    depot_stats['Avg_Order_Size'] = (depot_stats['Total_Units'] / depot_stats['Orders']).round(1)
    
    lines.append(f"\nTop 5 Depots by Volume:")
    for idx, (depot, row) in enumerate(depot_stats.head().iterrows(), 1):
        lines.append(f"{idx}. {depot}:")
        lines.append(f"   - Units Distributed: {row['Total_Units']:,.0f} ({row['Units_Pct']:.1f}%)")
        lines.append(f"   - Revenue: ${row['Revenue']:,.2f} ({row['Revenue_Pct']:.1f}%)")
        lines.append(f"   - Stores Served: {row['Stores_Served']:.0f}")
        lines.append(f"   - Routes Used: {row['Routes_Used']:.0f}")
        lines.append(f"   - Avg Order Size: {row['Avg_Order_Size']:.1f} units")
    
    # Depot concentration analysis
    top3_depots_pct = depot_stats.head(3)['Units_Pct'].sum()
    lines.append(f"\n📊 Depot Concentration: Top 3 depots = {top3_depots_pct:.1f}% of volume")
    if top3_depots_pct > 60:
        lines.append(f"   ⚠️  HIGH CONCENTRATION: {top3_depots_pct:.1f}% concentrated in top 3 depots")
        lines.append(f"   → Risk: Over-reliance on few depots (capacity/disruption risk)")
    else:
        lines.append(f"   ✅ BALANCED: Healthy distribution across depot network")
    lines.append("")
    
    # === 3. STORE ORDERING PATTERNS ===
    lines.append("=" * 80)
    lines.append("3. STORE ORDERING PATTERNS")
    lines.append("=" * 80)
    
    store_stats = df.groupby('store_id').agg({
        'quantity_sold': ['sum', 'count', 'mean'],
        'revenue': 'sum',
        'depot_id': lambda x: x.value_counts().index[0],  # Primary depot
        'sku': 'nunique'
    }).round(2)
    store_stats.columns = ['Total_Units', 'Orders', 'Avg_Order_Size', 'Revenue', 'Primary_Depot', 'SKU_Variety']
    store_stats = store_stats.sort_values('Total_Units', ascending=False)
    
    lines.append(f"\nTop 10 Stores by Volume:")
    for idx, (store, row) in enumerate(store_stats.head(10).iterrows(), 1):
        lines.append(f"{idx}. {store}: {row['Total_Units']:,.0f} units, {row['Orders']:.0f} orders, "
                    f"${row['Revenue']:,.2f} revenue, Avg: {row['Avg_Order_Size']:.1f} units/order "
                    f"(Primary depot: {row['Primary_Depot']})")
    
    # Store ordering frequency
    avg_orders_per_store = store_stats['Orders'].mean()
    lines.append(f"\n📦 Average Orders per Store: {avg_orders_per_store:.1f} orders")
    lines.append(f"📦 Average Order Size per Store: {store_stats['Avg_Order_Size'].mean():.1f} units")
    
    # High-volume vs low-volume stores
    high_vol_threshold = store_stats['Total_Units'].quantile(0.75)
    high_vol_stores = (store_stats['Total_Units'] >= high_vol_threshold).sum()
    lines.append(f"\n🏪 High-Volume Stores (top 25%): {high_vol_stores} stores account for significant volume")
    lines.append("")
    
    # === 4. ROUTE EFFICIENCY ===
    lines.append("=" * 80)
    lines.append("4. DISTRIBUTION ROUTE EFFICIENCY")
    lines.append("=" * 80)
    
    route_stats = df.groupby('route_id').agg({
        'quantity_sold': ['sum', 'count'],
        'revenue': 'sum',
        'store_id': 'nunique',
        'depot_id': lambda x: x.value_counts().index[0] if len(x) > 0 else 'N/A'
    }).round(2)
    route_stats.columns = ['Total_Units', 'Trips', 'Revenue', 'Stores_Served', 'Primary_Depot']
    route_stats = route_stats.sort_values('Total_Units', ascending=False)
    route_stats['Avg_Units_Per_Trip'] = (route_stats['Total_Units'] / route_stats['Trips']).round(1)
    
    lines.append(f"\nTop 10 Routes by Volume:")
    for idx, (route, row) in enumerate(route_stats.head(10).iterrows(), 1):
        lines.append(f"{idx}. {route}:")
        lines.append(f"   - Units Distributed: {row['Total_Units']:,.0f}")
        lines.append(f"   - Trips: {row['Trips']:.0f}")
        lines.append(f"   - Stores Served: {row['Stores_Served']:.0f}")
        lines.append(f"   - Avg Units/Trip: {row['Avg_Units_Per_Trip']:.1f}")
        lines.append(f"   - Primary Depot: {row['Primary_Depot']}")
    
    # Route efficiency analysis
    lines.append(f"\n🚚 Route Efficiency Metrics:")
    lines.append(f"   - Average units per trip: {route_stats['Avg_Units_Per_Trip'].mean():.1f} units")
    lines.append(f"   - Average stores per route: {route_stats['Stores_Served'].mean():.1f} stores")
    lines.append(f"   - Most efficient route: {route_stats['Avg_Units_Per_Trip'].idxmax()} "
                f"({route_stats['Avg_Units_Per_Trip'].max():.1f} units/trip)")
    lines.append(f"   - Least efficient route: {route_stats['Avg_Units_Per_Trip'].idxmin()} "
                f"({route_stats['Avg_Units_Per_Trip'].min():.1f} units/trip)")
    lines.append("")
    
    # === 5. SKU DEMAND ANALYSIS ===
    lines.append("=" * 80)
    lines.append("5. SKU DEMAND IN B2B CHANNEL")
    lines.append("=" * 80)
    
    sku_stats = df.groupby('sku').agg({
        'quantity_sold': 'sum',
        'revenue': 'sum',
        'price_per_unit': 'mean',
        'store_id': 'nunique',
        'depot_id': 'nunique'
    }).round(2)
    sku_stats.columns = ['Total_Units', 'Revenue', 'Avg_Price', 'Stores_Ordering', 'Depots_Stocking']
    sku_stats = sku_stats.sort_values('Total_Units', ascending=False)
    sku_stats['Units_Pct'] = (sku_stats['Total_Units'] / total_units * 100).round(2)
    
    lines.append(f"\nTop 10 SKUs by B2B Volume:")
    for idx, (sku, row) in enumerate(sku_stats.head(10).iterrows(), 1):
        lines.append(f"{idx}. {sku}:")
        lines.append(f"   - Units: {row['Total_Units']:,.0f} ({row['Units_Pct']:.1f}%)")
        lines.append(f"   - Revenue: ${row['Revenue']:,.2f}")
        lines.append(f"   - Avg Wholesale Price: ${row['Avg_Price']:.2f}/unit")
        lines.append(f"   - Stores Ordering: {row['Stores_Ordering']:.0f} ({row['Stores_Ordering']/n_stores*100:.1f}% coverage)")
    
    # SKU variety analysis
    lines.append(f"\n📊 SKU Portfolio:")
    lines.append(f"   - Total SKUs: {n_skus}")
    lines.append(f"   - Top 5 SKUs: {sku_stats.head(5)['Units_Pct'].sum():.1f}% of volume")
    lines.append(f"   - Top 10 SKUs: {sku_stats.head(10)['Units_Pct'].sum():.1f}% of volume")
    lines.append("")
    
    # === 6. PRICING ANALYSIS ===
    lines.append("=" * 80)
    lines.append("6. WHOLESALE PRICING STRUCTURE")
    lines.append("=" * 80)
    
    price_stats = df.groupby('sku')['price_per_unit'].agg(['mean', 'std', 'min', 'max']).round(2)
    price_stats = price_stats.sort_values('mean', ascending=False)
    
    lines.append(f"\nSKU Pricing (Wholesale):")
    lines.append(f"Overall Average Wholesale Price: ${df['price_per_unit'].mean():.2f}/unit")
    lines.append(f"Price Range: ${df['price_per_unit'].min():.2f} - ${df['price_per_unit'].max():.2f}")
    lines.append(f"\nTop 5 Most Expensive SKUs (Wholesale):")
    for idx, (sku, row) in enumerate(price_stats.head(5).iterrows(), 1):
        lines.append(f"{idx}. {sku}: ${row['mean']:.2f} avg (${row['min']:.2f}-${row['max']:.2f})")
    
    lines.append(f"\n💰 Pricing Insights:")
    lines.append(f"   - Wholesale avg: ${df['price_per_unit'].mean():.2f}/unit")
    lines.append(f"   - Price variability: Std Dev = ${df['price_per_unit'].std():.2f}")
    lines.append(f"   ℹ️  Compare with Sales POS (retail) to validate margin structure")
    lines.append("")
    
    # === 7. TEMPORAL PATTERNS ===
    lines.append("=" * 80)
    lines.append("7. TEMPORAL ORDERING PATTERNS (B2B)")
    lines.append("=" * 80)
    
    # Daily patterns
    daily_stats = df.groupby('date').agg({
        'quantity_sold': 'sum',
        'store_id': 'nunique'
    })
    
    lines.append(f"\n📅 Daily Metrics:")
    lines.append(f"   - Average daily volume: {daily_stats['quantity_sold'].mean():.0f} units")
    lines.append(f"   - Average stores ordering per day: {daily_stats['store_id'].mean():.1f}")
    lines.append(f"   - Peak day volume: {daily_stats['quantity_sold'].max():,.0f} units")
    lines.append(f"   - Lowest day volume: {daily_stats['quantity_sold'].min():,.0f} units")
    
    # Day of week patterns
    dow_stats = df.groupby('day_of_week')['quantity_sold'].sum().sort_values(ascending=False)
    lines.append(f"\n📊 Day of Week Patterns:")
    lines.append(f"   - Highest volume day: {dow_stats.index[0]} ({dow_stats.iloc[0]:,.0f} units)")
    lines.append(f"   - Lowest volume day: {dow_stats.index[-1]} ({dow_stats.iloc[-1]:,.0f} units)")
    
    # Hourly patterns
    hourly_stats = df.groupby('hour')['quantity_sold'].sum().sort_values(ascending=False)
    lines.append(f"\n⏰ Hourly Ordering Patterns:")
    lines.append(f"   - Peak hour: {hourly_stats.index[0]:02d}:00 ({hourly_stats.iloc[0]:,.0f} units)")
    lines.append(f"   - Slowest hour: {hourly_stats.index[-1]:02d}:00 ({hourly_stats.iloc[-1]:,.0f} units)")
    lines.append("")
    
    # === 8. B2B vs B2C COMPARISON (conceptual) ===
    lines.append("=" * 80)
    lines.append("8. B2B CHANNEL CHARACTERISTICS")
    lines.append("=" * 80)
    
    avg_b2b_order = df['quantity_sold'].mean()
    lines.append(f"\n📦 B2B Order Profile:")
    lines.append(f"   - Average B2B order size: {avg_b2b_order:.1f} units")
    lines.append(f"   - Median B2B order size: {df['quantity_sold'].median():.0f} units")
    lines.append(f"   - 75th percentile: {df['quantity_sold'].quantile(0.75):.0f} units")
    lines.append(f"   - 95th percentile: {df['quantity_sold'].quantile(0.95):.0f} units")
    lines.append(f"   ℹ️  Compare with Sales POS avg order size (~31 units) for B2B vs B2C validation")
    lines.append(f"   ℹ️  B2B orders should be 3-5x larger (depot→store vs store→consumer)")
    
    lines.append(f"\n🔗 Network Structure:")
    lines.append(f"   - Depots → Stores: {n_depots} depots serving {n_stores} stores")
    lines.append(f"   - Average stores per depot: {n_stores / n_depots:.1f}")
    lines.append(f"   - Routes connecting network: {n_routes}")
    lines.append(f"   - Average stores per route: {route_stats['Stores_Served'].mean():.1f}")
    lines.append("")
    
    # === 9. DEPOT-SKU PREFERENCES ===
    lines.append("=" * 80)
    lines.append("9. DEPOT-SPECIFIC SKU DEMAND")
    lines.append("=" * 80)
    
    depot_sku = df.groupby(['depot_id', 'sku'])['quantity_sold'].sum().reset_index()
    depot_sku_pivot = depot_sku.pivot(index='sku', columns='depot_id', values='quantity_sold').fillna(0)
    
    lines.append(f"\nDepot-SKU Matrix Summary:")
    lines.append(f"   - Total depot-SKU combinations: {len(depot_sku)}")
    for depot in depot_sku_pivot.columns[:5]:  # Top 5 depots
        top_sku = depot_sku_pivot[depot].idxmax()
        top_units = depot_sku_pivot[depot].max()
        lines.append(f"   - {depot} top SKU: {top_sku} ({top_units:,.0f} units)")
    lines.append("")
    
    # === 10. KEY INSIGHTS & ACTIONS ===
    lines.append("=" * 80)
    lines.append("10. KEY INSIGHTS & ACTION ITEMS")
    lines.append("=" * 80)
    
    lines.append("\n🎯 Critical Findings:")
    
    # Finding 1: Depot concentration
    if top3_depots_pct > 60:
        lines.append(f"\n1. HIGH DEPOT CONCENTRATION ({top3_depots_pct:.1f}%)")
        lines.append(f"   → Risk: Over-reliance on top 3 depots creates capacity bottleneck")
        lines.append(f"   → Action: Expand secondary depot capacity, backup distribution plans")
    else:
        lines.append(f"\n1. BALANCED DEPOT NETWORK ({top3_depots_pct:.1f}%)")
        lines.append(f"   → Strength: No single-point-of-failure in depot network")
        lines.append(f"   → Action: Maintain balanced load distribution")
    
    # Finding 2: B2B order size
    if avg_b2b_order < 100:
        lines.append(f"\n2. SMALL B2B ORDER SIZES ({avg_b2b_order:.1f} units)")
        lines.append(f"   → Issue: Orders may be too frequent/small (inefficient logistics)")
        lines.append(f"   → Action: Encourage larger, less frequent orders (MOQ policies)")
    else:
        lines.append(f"\n2. HEALTHY B2B ORDER SIZES ({avg_b2b_order:.1f} units)")
        lines.append(f"   → Strength: Bulk ordering reduces distribution frequency/cost")
        lines.append(f"   → Action: Maintain MOQ policies, volume discounts")
    
    # Finding 3: Route efficiency variance
    route_eff_std = route_stats['Avg_Units_Per_Trip'].std()
    if route_eff_std > 50:
        lines.append(f"\n3. HIGH ROUTE EFFICIENCY VARIANCE (Std: {route_eff_std:.1f})")
        lines.append(f"   → Issue: Some routes severely underutilized")
        lines.append(f"   → Action: Route consolidation, store clustering optimization")
    
    # Finding 4: SKU coverage
    avg_sku_coverage = sku_stats['Stores_Ordering'].mean() / n_stores * 100
    lines.append(f"\n4. SKU COVERAGE ACROSS STORES: {avg_sku_coverage:.1f}%")
    if avg_sku_coverage < 50:
        lines.append(f"   → Issue: Low SKU availability across store network")
        lines.append(f"   → Action: Improve depot SKU stocking, demand forecasting")
    else:
        lines.append(f"   → Strength: Good SKU availability network-wide")
    
    lines.append("\n" + "=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    # Write to file
    summary_path = REPORTS_DIR / 'sales_b2b_enhanced_summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    logging.info(f"Wrote {summary_path}")
    
    return '\n'.join(lines)


def grouped_summaries(df):
    """
    Generate grouped summary CSVs for pivot analysis.
    """
    # 1. By Depot
    depot_summary = df.groupby('depot_id').agg({
        'quantity_sold': ['sum', 'count', 'mean'],
        'revenue': 'sum',
        'store_id': 'nunique',
        'route_id': 'nunique',
        'sku': 'nunique'
    }).round(2)
    depot_summary.columns = ['Total_Units', 'Orders', 'Avg_Order_Size', 'Revenue', 
                             'Stores_Served', 'Routes_Used', 'SKU_Variety']
    depot_summary = depot_summary.sort_values('Total_Units', ascending=False)
    depot_summary.to_csv(SUMMARIES_DIR / 'sales_b2b_by_depot.csv')
    logging.info("Wrote sales_b2b_by_depot.csv")
    
    # 2. By Store (Top 50)
    store_summary = df.groupby('store_id').agg({
        'quantity_sold': ['sum', 'count', 'mean'],
        'revenue': 'sum',
        'depot_id': lambda x: x.value_counts().index[0],
        'sku': 'nunique'
    }).round(2)
    store_summary.columns = ['Total_Units', 'Orders', 'Avg_Order_Size', 'Revenue', 
                            'Primary_Depot', 'SKU_Variety']
    store_summary = store_summary.sort_values('Total_Units', ascending=False).head(50)
    store_summary.to_csv(SUMMARIES_DIR / 'sales_b2b_by_store_top50.csv')
    logging.info("Wrote sales_b2b_by_store_top50.csv")
    
    # 3. By Route (Top 30)
    route_summary = df.groupby('route_id').agg({
        'quantity_sold': ['sum', 'count', 'mean'],
        'revenue': 'sum',
        'store_id': 'nunique',
        'depot_id': lambda x: x.value_counts().index[0] if len(x) > 0 else 'N/A'
    }).round(2)
    route_summary.columns = ['Total_Units', 'Trips', 'Avg_Units_Per_Trip', 'Revenue', 
                            'Stores_Served', 'Primary_Depot']
    route_summary = route_summary.sort_values('Total_Units', ascending=False).head(30)
    route_summary.to_csv(SUMMARIES_DIR / 'sales_b2b_by_route_top30.csv')
    logging.info("Wrote sales_b2b_by_route_top30.csv")
    
    # 4. By SKU
    sku_summary = df.groupby('sku').agg({
        'quantity_sold': 'sum',
        'revenue': 'sum',
        'price_per_unit': 'mean',
        'store_id': 'nunique',
        'depot_id': 'nunique'
    }).round(2)
    sku_summary.columns = ['Total_Units', 'Revenue', 'Avg_Wholesale_Price', 
                          'Stores_Ordering', 'Depots_Stocking']
    sku_summary = sku_summary.sort_values('Total_Units', ascending=False)
    sku_summary.to_csv(SUMMARIES_DIR / 'sales_b2b_by_sku.csv')
    logging.info("Wrote sales_b2b_by_sku.csv")
    
    # 5. By Date
    date_summary = df.groupby('date').agg({
        'quantity_sold': 'sum',
        'revenue': 'sum',
        'store_id': 'nunique',
        'depot_id': 'nunique'
    }).round(2)
    date_summary.columns = ['Total_Units', 'Revenue', 'Stores_Ordering', 'Depots_Active']
    date_summary.to_csv(SUMMARIES_DIR / 'sales_b2b_by_date.csv')
    logging.info("Wrote sales_b2b_by_date.csv")
    
    # 6. Depot-SKU Matrix
    depot_sku = df.groupby(['depot_id', 'sku'])['quantity_sold'].sum().reset_index()
    depot_sku_pivot = depot_sku.pivot(index='sku', columns='depot_id', values='quantity_sold').fillna(0)
    depot_sku_pivot.to_csv(SUMMARIES_DIR / 'sales_b2b_depot_sku_matrix.csv')
    logging.info("Wrote sales_b2b_depot_sku_matrix.csv")
    
    # 7. Route-Store Mapping (network structure)
    route_store = df.groupby(['route_id', 'store_id']).agg({
        'quantity_sold': 'sum',
        'depot_id': lambda x: x.value_counts().index[0] if len(x) > 0 else 'N/A'
    }).reset_index()
    route_store.columns = ['Route_ID', 'Store_ID', 'Total_Units', 'Primary_Depot']
    route_store = route_store.sort_values('Total_Units', ascending=False)
    route_store.to_csv(SUMMARIES_DIR / 'sales_b2b_route_store_network.csv', index=False)
    logging.info("Wrote sales_b2b_route_store_network.csv")


def visualizations(df):
    """
    Generate 10+ comprehensive visualizations for B2B Sales Dataset.
    """
    
    # 1. Depot Performance Bar Chart
    plt.figure(figsize=(12, 6))
    depot_vol = df.groupby('depot_id')['quantity_sold'].sum().sort_values(ascending=True)
    colors = ['crimson' if x > depot_vol.quantile(0.66) else 'orange' if x > depot_vol.quantile(0.33) else 'gold' 
              for x in depot_vol]
    depot_vol.plot(kind='barh', color=colors)
    plt.xlabel('Total Units Distributed', fontsize=12, fontweight='bold')
    plt.ylabel('Depot ID', fontsize=12, fontweight='bold')
    plt.title('Depot Distribution Performance - Total Units Distributed', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_by_depot.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_by_depot.png")
    
    # 2. Store Ordering Volume (Top 20)
    plt.figure(figsize=(12, 8))
    store_vol = df.groupby('store_id')['quantity_sold'].sum().sort_values(ascending=True).tail(20)
    colors = ['green' if x > store_vol.median() else 'orange' for x in store_vol]
    store_vol.plot(kind='barh', color=colors)
    plt.xlabel('Total Units Ordered', fontsize=12, fontweight='bold')
    plt.ylabel('Store ID', fontsize=12, fontweight='bold')
    plt.title('Top 20 Stores by Order Volume (B2B)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_by_store_top20.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_by_store_top20.png")
    
    # 3. Route Efficiency (Top 15)
    plt.figure(figsize=(12, 7))
    route_eff = df.groupby('route_id').agg({
        'quantity_sold': ['sum', 'count']
    })
    route_eff.columns = ['Total_Units', 'Trips']
    route_eff['Avg_Per_Trip'] = route_eff['Total_Units'] / route_eff['Trips']
    route_eff = route_eff.sort_values('Avg_Per_Trip', ascending=True).tail(15)
    
    colors = ['green' if x > route_eff['Avg_Per_Trip'].median() else 'red' 
              for x in route_eff['Avg_Per_Trip']]
    route_eff['Avg_Per_Trip'].plot(kind='barh', color=colors)
    plt.xlabel('Average Units per Trip', fontsize=12, fontweight='bold')
    plt.ylabel('Route ID', fontsize=12, fontweight='bold')
    plt.title('Top 15 Most Efficient Routes (Avg Units per Trip)', fontsize=14, fontweight='bold')
    plt.axvline(route_eff['Avg_Per_Trip'].median(), color='blue', linestyle='--', 
                linewidth=2, label=f"Median: {route_eff['Avg_Per_Trip'].median():.1f}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_route_efficiency_top15.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_route_efficiency_top15.png")
    
    # 4. SKU Demand in B2B Channel
    plt.figure(figsize=(12, 8))
    sku_vol = df.groupby('sku')['quantity_sold'].sum().sort_values(ascending=True)
    colors = ['darkgreen' if x > sku_vol.quantile(0.75) else 'orange' if x > sku_vol.median() else 'gold' 
              for x in sku_vol]
    sku_vol.plot(kind='barh', color=colors)
    plt.xlabel('Total Units Distributed (B2B)', fontsize=12, fontweight='bold')
    plt.ylabel('SKU', fontsize=12, fontweight='bold')
    plt.title('SKU Distribution Volume in B2B Channel', fontsize=14, fontweight='bold')
    plt.axvline(sku_vol.median(), color='red', linestyle='--', linewidth=2, 
                label=f"Median: {sku_vol.median():,.0f}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_by_sku.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_by_sku.png")
    
    # 5. Daily Sales Trend
    plt.figure(figsize=(14, 6))
    daily_sales = df.groupby('date')['quantity_sold'].sum().sort_index()
    plt.fill_between(daily_sales.index, daily_sales.values, alpha=0.3, color='steelblue')
    plt.plot(daily_sales.index, daily_sales.values, color='darkblue', linewidth=2, label='Daily Volume')
    
    # 7-day moving average
    ma7 = daily_sales.rolling(window=7, center=True).mean()
    plt.plot(ma7.index, ma7.values, color='red', linewidth=2, linestyle='--', label='7-Day Moving Avg')
    
    plt.xlabel('Date', fontsize=12, fontweight='bold')
    plt.ylabel('Units Distributed', fontsize=12, fontweight='bold')
    plt.title('Daily B2B Distribution Volume with Moving Average', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_daily_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_daily_trend.png")
    
    # 6. Day of Week Pattern
    plt.figure(figsize=(10, 6))
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_sales = df.groupby('day_of_week')['quantity_sold'].sum().reindex(dow_order)
    
    colors = ['steelblue' if day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] 
              else 'coral' for day in dow_sales.index]
    bars = plt.bar(dow_sales.index, dow_sales.values, color=colors)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.xlabel('Day of Week', fontsize=12, fontweight='bold')
    plt.ylabel('Total Units Distributed', fontsize=12, fontweight='bold')
    plt.title('B2B Distribution Volume by Day of Week', fontsize=14, fontweight='bold')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_day_of_week.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_day_of_week.png")
    
    # 7. Hourly Ordering Pattern
    plt.figure(figsize=(12, 6))
    hourly_sales = df.groupby('hour')['quantity_sold'].sum()
    plt.bar(hourly_sales.index, hourly_sales.values, color='teal', alpha=0.7)
    plt.plot(hourly_sales.index, hourly_sales.values, color='red', marker='o', linewidth=2)
    plt.xlabel('Hour of Day (24-hour format)', fontsize=12, fontweight='bold')
    plt.ylabel('Total Units Ordered', fontsize=12, fontweight='bold')
    plt.title('B2B Order Volume by Hour of Day', fontsize=14, fontweight='bold')
    plt.xticks(range(0, 24))
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_hourly_pattern.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_hourly_pattern.png")
    
    # 8. Order Size Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(df['quantity_sold'], bins=50, color='steelblue', edgecolor='black', alpha=0.7)
    plt.axvline(df['quantity_sold'].mean(), color='red', linestyle='--', linewidth=2, 
                label=f"Mean: {df['quantity_sold'].mean():.1f}")
    plt.axvline(df['quantity_sold'].median(), color='green', linestyle='--', linewidth=2, 
                label=f"Median: {df['quantity_sold'].median():.1f}")
    plt.xlabel('Order Size (Units)', fontsize=12, fontweight='bold')
    plt.ylabel('Frequency', fontsize=12, fontweight='bold')
    plt.title('B2B Order Size Distribution', fontsize=14, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_order_size_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_order_size_distribution.png")
    
    # 9. Depot-SKU Heatmap
    plt.figure(figsize=(14, 10))
    depot_sku = df.groupby(['depot_id', 'sku'])['quantity_sold'].sum().unstack(fill_value=0)
    sns.heatmap(depot_sku.T, cmap='YlOrRd', annot=True, fmt='.0f', cbar_kws={'label': 'Units Distributed'})
    plt.xlabel('Depot ID', fontsize=12, fontweight='bold')
    plt.ylabel('SKU', fontsize=12, fontweight='bold')
    plt.title('Depot-SKU Distribution Heatmap', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_depot_sku_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_depot_sku_heatmap.png")
    
    # 10. Wholesale Pricing by SKU
    plt.figure(figsize=(12, 8))
    price_by_sku = df.groupby('sku')['price_per_unit'].agg(['mean', 'std']).sort_values('mean', ascending=True)
    
    # Box plot alternative: mean with error bars
    plt.barh(range(len(price_by_sku)), price_by_sku['mean'], 
             xerr=price_by_sku['std'], color='gold', edgecolor='black', alpha=0.7)
    plt.yticks(range(len(price_by_sku)), price_by_sku.index)
    plt.xlabel('Wholesale Price per Unit ($)', fontsize=12, fontweight='bold')
    plt.ylabel('SKU', fontsize=12, fontweight='bold')
    plt.title('Wholesale Pricing by SKU (Mean ± Std Dev)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_pricing_by_sku.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_pricing_by_sku.png")
    
    # 11. Depot Market Share (Pie Chart)
    plt.figure(figsize=(10, 10))
    depot_share = df.groupby('depot_id')['quantity_sold'].sum().sort_values(ascending=False)
    colors_pie = plt.cm.Set3(range(len(depot_share)))
    
    plt.pie(depot_share.values, labels=depot_share.index, autopct='%1.1f%%', 
            colors=colors_pie, startangle=90)
    plt.title('Depot Market Share (by Volume)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_depot_share_pie.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_depot_share_pie.png")
    
    # 12. Revenue by Depot
    plt.figure(figsize=(12, 6))
    depot_revenue = df.groupby('depot_id')['revenue'].sum().sort_values(ascending=True)
    colors = ['darkgreen' if x > depot_revenue.quantile(0.66) else 'orange' 
              if x > depot_revenue.quantile(0.33) else 'gold' for x in depot_revenue]
    depot_revenue.plot(kind='barh', color=colors)
    plt.xlabel('Total Revenue ($)', fontsize=12, fontweight='bold')
    plt.ylabel('Depot ID', fontsize=12, fontweight='bold')
    plt.title('Depot Performance by Revenue (Wholesale)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_b2b_depot_revenue.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_b2b_depot_revenue.png")


def main():
    """
    Main execution function.
    """
    logging.info("=" * 80)
    logging.info("Starting Sales Dataset (B2B Channel) Enhanced EDA")
    logging.info("=" * 80)
    
    # Load and prepare data
    df = load_and_prepare()
    
    # Generate summary statistics
    summary_stats(df)
    
    # Generate grouped summaries
    grouped_summaries(df)
    
    # Generate visualizations
    visualizations(df)
    
    logging.info("=" * 80)
    logging.info("✅ Sales B2B EDA complete!")
    logging.info(f"   - Summary: reports/sales_b2b_enhanced_summary.txt")
    logging.info(f"   - Figures: reports/figures/sales_b2b_*.png (12 visualizations)")
    logging.info(f"   - CSVs: reports/summaries/sales_b2b_*.csv (7 summary files)")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()
