"""
Exploratory Data Analysis for Sales / Retail POS Dataset

This script analyzes the demand-side dataset that records actual customer purchases
at retail outlets. Sales data validates production and dispatch decisions and drives
demand forecasting.

Key Analyses:
- Demand patterns (daily/weekly/hourly)
- SKU performance (fast vs slow-moving products)
- Regional demand variations
- Promotion effectiveness and ROI
- Price elasticity and revenue analysis
- Holiday impact on sales
- Retailer performance ranking
- Sell-through analysis

Author: Baker's Inn Analytics Team
Date: 2025
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(message)s'
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'processed'
REPORTS_DIR = BASE_DIR / 'reports'
FIGURES_DIR = REPORTS_DIR / 'figures'
SUMMARIES_DIR = REPORTS_DIR / 'summaries'

# Create output directories
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

def load_and_prepare():
    """
    Load sales POS dataset and prepare derived fields.
    
    Returns:
        pd.DataFrame: Sales data with derived fields
    """
    df = pd.read_parquet(DATA_DIR / 'sales_pos_dataset.parquet')
    logging.info(f"Loaded {len(df):,} sales transactions")
    
    # Derive time-based features
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
    df['day_name'] = df['timestamp'].dt.day_name()
    df['month'] = df['timestamp'].dt.month
    df['month_name'] = df['timestamp'].dt.month_name()
    df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
    
    # Derive business metrics
    df['revenue'] = df['quantity_sold'] * df['price']
    
    # Promotion categorization
    df['promotion_category'] = df['promotion_name'].fillna('No Promotion')
    
    return df

def summary_stats(df):
    """
    Generate comprehensive summary statistics for sales POS dataset.
    
    Args:
        df: Sales DataFrame
    """
    summary_path = REPORTS_DIR / 'sales_pos_summary.txt'
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SALES / RETAIL POS DATASET - EXPLORATORY DATA ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        # Dataset overview
        f.write("📊 DATASET OVERVIEW\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Sales Transactions: {len(df):,}\n")
        f.write(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}\n")
        f.write(f"Total Units Sold: {df['quantity_sold'].sum():,}\n")
        f.write(f"Total Revenue: ${df['revenue'].sum():,.2f}\n")
        f.write(f"Average Transaction Size: {df['quantity_sold'].mean():.1f} units\n")
        f.write(f"Average Price: ${df['price'].mean():.2f}\n")
        f.write(f"Unique Retailers: {df['retailer_id'].nunique()}\n")
        f.write(f"Regions: {df['region'].nunique()} - {', '.join(sorted(df['region'].unique()))}\n")
        f.write(f"SKUs: {df['sku'].nunique()}\n\n")
        
        # Promotion overview
        promo_count = df['promotion_flag'].sum()
        promo_pct = (promo_count / len(df)) * 100
        f.write("🎯 PROMOTION OVERVIEW\n")
        f.write("-" * 80 + "\n")
        f.write(f"Sales with Promotions: {promo_count:,} ({promo_pct:.1f}%)\n")
        f.write(f"Sales without Promotions: {len(df) - promo_count:,} ({100 - promo_pct:.1f}%)\n")
        f.write(f"Unique Promotions: {df[df['promotion_flag'] == 1]['promotion_name'].nunique()}\n\n")
        
        # Promotion effectiveness
        promo_sales = df.groupby('promotion_flag').agg({
            'quantity_sold': ['sum', 'mean'],
            'revenue': ['sum', 'mean'],
            'price': 'mean'
        }).round(2)
        f.write("Promotion vs Non-Promotion Performance:\n")
        f.write(f"{promo_sales}\n\n")
        
        promo_uplift_qty = ((promo_sales.loc[1, ('quantity_sold', 'mean')] / 
                             promo_sales.loc[0, ('quantity_sold', 'mean')]) - 1) * 100
        promo_uplift_rev = ((promo_sales.loc[1, ('revenue', 'mean')] / 
                            promo_sales.loc[0, ('revenue', 'mean')]) - 1) * 100
        
        if promo_uplift_qty > 0:
            f.write(f"✅ Promotion Uplift: +{promo_uplift_qty:.1f}% quantity, +{promo_uplift_rev:.1f}% revenue per transaction\n\n")
        else:
            f.write(f"⚠️ WARNING: Promotions showing NEGATIVE uplift: {promo_uplift_qty:.1f}% quantity\n\n")
        
        # Top promotions by volume
        f.write("Top Promotions by Sales Volume:\n")
        top_promos = df[df['promotion_flag'] == 1].groupby('promotion_name').agg({
            'quantity_sold': 'sum',
            'revenue': 'sum',
            'sale_id': 'count'
        }).sort_values('quantity_sold', ascending=False).head(10)
        top_promos.columns = ['Units Sold', 'Revenue', 'Transactions']
        f.write(f"{top_promos}\n\n")
        
        # Regional performance
        f.write("🌍 REGIONAL DEMAND ANALYSIS\n")
        f.write("-" * 80 + "\n")
        regional = df.groupby('region').agg({
            'quantity_sold': 'sum',
            'revenue': 'sum',
            'sale_id': 'count',
            'retailer_id': 'nunique'
        }).sort_values('quantity_sold', ascending=False)
        regional.columns = ['Units Sold', 'Revenue', 'Transactions', 'Retailers']
        regional['Avg Units/Transaction'] = (regional['Units Sold'] / regional['Transactions']).round(1)
        regional['Avg Revenue/Transaction'] = (regional['Revenue'] / regional['Transactions']).round(2)
        f.write(f"{regional}\n\n")
        
        # SKU performance
        f.write("🍞 SKU PERFORMANCE ANALYSIS\n")
        f.write("-" * 80 + "\n")
        sku_perf = df.groupby('sku').agg({
            'quantity_sold': 'sum',
            'revenue': 'sum',
            'sale_id': 'count',
            'price': 'mean'
        }).sort_values('quantity_sold', ascending=False)
        sku_perf.columns = ['Units Sold', 'Revenue', 'Transactions', 'Avg Price']
        sku_perf['% of Total Units'] = (sku_perf['Units Sold'] / sku_perf['Units Sold'].sum() * 100).round(1)
        sku_perf['% of Total Revenue'] = (sku_perf['Revenue'] / sku_perf['Revenue'].sum() * 100).round(1)
        f.write(f"{sku_perf}\n\n")
        
        # Identify fast vs slow-moving SKUs
        sku_daily_avg = df.groupby(['date', 'sku'])['quantity_sold'].sum().reset_index()
        sku_daily_mean = sku_daily_avg.groupby('sku')['quantity_sold'].mean().sort_values(ascending=False)
        f.write("Fast-Moving SKUs (Top 5 by daily avg):\n")
        f.write(f"{sku_daily_mean.head()}\n\n")
        f.write("Slow-Moving SKUs (Bottom 5 by daily avg):\n")
        f.write(f"{sku_daily_mean.tail()}\n\n")
        
        # Temporal patterns
        f.write("⏰ TEMPORAL DEMAND PATTERNS\n")
        f.write("-" * 80 + "\n")
        
        # Day of week
        dow_sales = df.groupby('day_name').agg({
            'quantity_sold': 'sum',
            'revenue': 'sum',
            'sale_id': 'count'
        }).reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        dow_sales.columns = ['Units', 'Revenue', 'Transactions']
        f.write("Sales by Day of Week:\n")
        f.write(f"{dow_sales}\n\n")
        
        # Weekend vs weekday
        weekend_comp = df.groupby('is_weekend').agg({
            'quantity_sold': ['sum', 'mean'],
            'revenue': ['sum', 'mean']
        }).round(2)
        weekend_comp.index = ['Weekday', 'Weekend']
        f.write("Weekday vs Weekend:\n")
        f.write(f"{weekend_comp}\n\n")
        
        # Hourly patterns
        hourly = df.groupby('hour')['quantity_sold'].agg(['sum', 'mean', 'count']).round(1)
        hourly.columns = ['Total Units', 'Avg Units/Sale', 'Transactions']
        peak_hour = hourly['Total Units'].idxmax()
        lowest_hour = hourly['Total Units'].idxmin()
        f.write("Hourly Sales Summary:\n")
        f.write(f"{hourly}\n\n")
        f.write(f"Peak Sales Hour: {peak_hour}:00 ({hourly.loc[peak_hour, 'Total Units']:.0f} units)\n")
        f.write(f"Lowest Sales Hour: {lowest_hour}:00 ({hourly.loc[lowest_hour, 'Total Units']:.0f} units)\n\n")
        
        # Price analysis
        f.write("💲 PRICE ANALYSIS\n")
        f.write("-" * 80 + "\n")
        price_stats = df.groupby('sku')['price'].agg(['min', 'mean', 'max', 'std']).round(2)
        price_stats.columns = ['Min Price', 'Avg Price', 'Max Price', 'Std Dev']
        f.write("Price Statistics by SKU:\n")
        f.write(f"{price_stats}\n\n")
        
        # Price elasticity indicator (correlation between price and quantity)
        f.write("Price vs Quantity Correlation by SKU:\n")
        for sku in df['sku'].unique()[:10]:  # Top 10 SKUs
            sku_data = df[df['sku'] == sku]
            if len(sku_data) > 10:  # Need sufficient data
                corr = sku_data['price'].corr(sku_data['quantity_sold'])
                f.write(f"  {sku}: {corr:.3f}")
                if corr < -0.3:
                    f.write(" (strong negative - price sensitive)")
                elif corr > 0.3:
                    f.write(" (positive - premium product)")
                else:
                    f.write(" (weak relationship)")
                f.write("\n")
        f.write("\n")
        
        # Retailer performance
        f.write("🏪 TOP RETAILERS BY SALES VOLUME\n")
        f.write("-" * 80 + "\n")
        retailer_perf = df.groupby('retailer_id').agg({
            'quantity_sold': 'sum',
            'revenue': 'sum',
            'sale_id': 'count'
        }).sort_values('quantity_sold', ascending=False).head(20)
        retailer_perf.columns = ['Units Sold', 'Revenue', 'Transactions']
        retailer_perf['Avg Units/Transaction'] = (retailer_perf['Units Sold'] / retailer_perf['Transactions']).round(1)
        f.write(f"{retailer_perf}\n\n")
        
        # ACTION ITEMS
        f.write("🎯 KEY INSIGHTS & ACTION ITEMS\n")
        f.write("=" * 80 + "\n")
        
        # Check for anomalies
        low_transaction_retailers = df.groupby('retailer_id')['sale_id'].count()
        underperforming = low_transaction_retailers[low_transaction_retailers < low_transaction_retailers.quantile(0.1)]
        f.write(f"1. ⚠️ {len(underperforming)} retailers with very low sales (<10th percentile)\n")
        f.write("   Action: Investigate stock-outs, poor locations, or dispatch issues\n\n")
        
        # Zero sales check (retailers in dispatch but not in sales)
        f.write("2. Check for retailers receiving dispatch but showing zero/low sales\n")
        f.write("   Action: Cross-reference with dispatch_dataset to identify overstock situations\n\n")
        
        # Promotion effectiveness
        if promo_uplift_qty < 0:
            f.write("3. ⚠️ CRITICAL: Promotions showing negative impact on sales volume\n")
            f.write("   Action: Review promotion strategy, pricing, and communication\n\n")
        
        # SKU rationalization
        slow_movers = sku_daily_mean[sku_daily_mean < sku_daily_mean.quantile(0.2)]
        f.write(f"4. {len(slow_movers)} slow-moving SKUs identified\n")
        f.write("   Action: Consider reducing production or discontinuing low-demand products\n\n")
        
        # Regional expansion
        top_region = regional.index[0]
        f.write(f"5. {top_region} is the strongest market ({regional.loc[top_region, 'Units Sold']:,.0f} units)\n")
        f.write("   Action: Expand retailer network and dispatch capacity in high-demand regions\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("✅ Sales POS summary complete!\n")
    
    logging.info(f"Wrote {summary_path}")

def grouped_summaries(df):
    """
    Generate grouped summary CSV files.
    
    Args:
        df: Sales DataFrame
    """
    # 1. Sales by SKU
    sku_summary = df.groupby('sku').agg({
        'quantity_sold': ['sum', 'mean', 'count'],
        'revenue': ['sum', 'mean'],
        'price': ['min', 'mean', 'max'],
        'promotion_flag': 'sum'
    }).round(2)
    sku_summary.columns = ['_'.join(col).strip() for col in sku_summary.columns]
    sku_summary = sku_summary.sort_values('quantity_sold_sum', ascending=False)
    sku_summary.to_csv(SUMMARIES_DIR / 'sales_pos_by_sku.csv')
    logging.info("Wrote sales_pos_by_sku.csv")
    
    # 2. Sales by region
    region_summary = df.groupby('region').agg({
        'quantity_sold': ['sum', 'mean'],
        'revenue': ['sum', 'mean'],
        'sale_id': 'count',
        'retailer_id': 'nunique',
        'promotion_flag': 'sum'
    }).round(2)
    region_summary.columns = ['_'.join(col).strip() for col in region_summary.columns]
    region_summary = region_summary.sort_values('quantity_sold_sum', ascending=False)
    region_summary.to_csv(SUMMARIES_DIR / 'sales_pos_by_region.csv')
    logging.info("Wrote sales_pos_by_region.csv")
    
    # 3. Sales by retailer (top 50)
    retailer_summary = df.groupby('retailer_id').agg({
        'quantity_sold': ['sum', 'mean'],
        'revenue': ['sum', 'mean'],
        'sale_id': 'count',
        'promotion_flag': 'sum',
        'region': 'first'
    }).round(2)
    retailer_summary.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in retailer_summary.columns]
    retailer_summary = retailer_summary.sort_values('quantity_sold_sum', ascending=False).head(50)
    retailer_summary.to_csv(SUMMARIES_DIR / 'sales_pos_by_retailer_top50.csv')
    logging.info("Wrote sales_pos_by_retailer_top50.csv")
    
    # 4. Sales by date
    daily_summary = df.groupby('date').agg({
        'quantity_sold': 'sum',
        'revenue': 'sum',
        'sale_id': 'count',
        'promotion_flag': 'sum'
    }).round(2)
    daily_summary.columns = ['total_units', 'total_revenue', 'transactions', 'promo_transactions']
    daily_summary.to_csv(SUMMARIES_DIR / 'sales_pos_by_date.csv')
    logging.info("Wrote sales_pos_by_date.csv")
    
    # 5. Sales by hour of day
    hourly_summary = df.groupby('hour').agg({
        'quantity_sold': ['sum', 'mean', 'count'],
        'revenue': ['sum', 'mean']
    }).round(2)
    hourly_summary.columns = ['_'.join(col).strip() for col in hourly_summary.columns]
    hourly_summary.to_csv(SUMMARIES_DIR / 'sales_pos_by_hour.csv')
    logging.info("Wrote sales_pos_by_hour.csv")
    
    # 6. Promotion performance
    promo_summary = df[df['promotion_flag'] == 1].groupby('promotion_name').agg({
        'quantity_sold': ['sum', 'mean', 'count'],
        'revenue': ['sum', 'mean'],
        'price': 'mean',
        'retailer_id': 'nunique'
    }).round(2)
    promo_summary.columns = ['_'.join(col).strip() for col in promo_summary.columns]
    promo_summary = promo_summary.sort_values('quantity_sold_sum', ascending=False)
    promo_summary.to_csv(SUMMARIES_DIR / 'sales_pos_by_promotion.csv')
    logging.info("Wrote sales_pos_by_promotion.csv")
    
    # 7. Regional SKU preferences
    regional_sku = df.groupby(['region', 'sku']).agg({
        'quantity_sold': 'sum',
        'revenue': 'sum'
    }).round(2)
    regional_sku = regional_sku.sort_values('quantity_sold', ascending=False)
    regional_sku.to_csv(SUMMARIES_DIR / 'sales_pos_regional_sku_preferences.csv')
    logging.info("Wrote sales_pos_regional_sku_preferences.csv")

def visualizations(df):
    """
    Generate comprehensive visualizations for sales POS dataset.
    
    Args:
        df: Sales DataFrame
    """
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 6)
    
    # 1. Sales volume by SKU
    fig, ax = plt.subplots(figsize=(14, 7))
    sku_sales = df.groupby('sku')['quantity_sold'].sum().sort_values(ascending=True)
    colors = ['green' if x > sku_sales.median() else 'orange' for x in sku_sales]
    sku_sales.plot(kind='barh', ax=ax, color=colors)
    ax.set_title('Total Sales Volume by SKU', fontsize=16, fontweight='bold')
    ax.set_xlabel('Units Sold', fontsize=12)
    ax.set_ylabel('SKU', fontsize=12)
    ax.axvline(sku_sales.median(), color='red', linestyle='--', linewidth=2, label=f'Median: {sku_sales.median():.0f}')
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_volume_by_sku.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_volume_by_sku.png")
    
    # 2. Revenue by region
    fig, ax = plt.subplots(figsize=(12, 6))
    region_rev = df.groupby('region')['revenue'].sum().sort_values(ascending=False)
    region_rev.plot(kind='bar', ax=ax, color='steelblue')
    ax.set_title('Total Revenue by Region', fontsize=16, fontweight='bold')
    ax.set_xlabel('Region', fontsize=12)
    ax.set_ylabel('Revenue ($)', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    for i, v in enumerate(region_rev.values):
        ax.text(i, v, f'${v:,.0f}', ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_revenue_by_region.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_revenue_by_region.png")
    
    # 3. Promotion effectiveness comparison
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Volume comparison
    promo_comp = df.groupby('promotion_flag')['quantity_sold'].mean()
    promo_labels = ['No Promotion', 'With Promotion']
    colors_promo = ['lightcoral', 'lightgreen']
    axes[0].bar(promo_labels, promo_comp.values, color=colors_promo)
    axes[0].set_title('Average Units Sold per Transaction', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Avg Units', fontsize=12)
    for i, v in enumerate(promo_comp.values):
        axes[0].text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Revenue comparison
    promo_rev = df.groupby('promotion_flag')['revenue'].mean()
    axes[1].bar(promo_labels, promo_rev.values, color=colors_promo)
    axes[1].set_title('Average Revenue per Transaction', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Avg Revenue ($)', fontsize=12)
    for i, v in enumerate(promo_rev.values):
        axes[1].text(i, v, f'${v:.2f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.suptitle('Promotion Effectiveness Analysis', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_promotion_effectiveness.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_promotion_effectiveness.png")
    
    # 4. Daily sales trend
    fig, ax = plt.subplots(figsize=(14, 6))
    daily_sales = df.groupby('date')['quantity_sold'].sum().reset_index()
    daily_sales['date'] = pd.to_datetime(daily_sales['date'])
    
    ax.plot(daily_sales['date'], daily_sales['quantity_sold'], linewidth=2, color='darkblue', alpha=0.7)
    ax.fill_between(daily_sales['date'], daily_sales['quantity_sold'], alpha=0.3, color='skyblue')
    
    # Add 7-day moving average
    daily_sales['ma7'] = daily_sales['quantity_sold'].rolling(window=7, center=True).mean()
    ax.plot(daily_sales['date'], daily_sales['ma7'], linewidth=3, color='red', label='7-Day Moving Avg')
    
    ax.set_title('Daily Sales Trend (Units Sold)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Units Sold', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_daily_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_daily_trend.png")
    
    # 5. Hourly sales pattern
    fig, ax = plt.subplots(figsize=(12, 6))
    hourly_sales = df.groupby('hour')['quantity_sold'].sum()
    ax.bar(hourly_sales.index, hourly_sales.values, color='teal', alpha=0.7)
    ax.plot(hourly_sales.index, hourly_sales.values, color='darkred', marker='o', linewidth=2, markersize=8)
    ax.set_title('Sales Volume by Hour of Day', fontsize=16, fontweight='bold')
    ax.set_xlabel('Hour', fontsize=12)
    ax.set_ylabel('Total Units Sold', fontsize=12)
    ax.set_xticks(range(0, 24))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_hourly_pattern.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_hourly_pattern.png")
    
    # 6. Day of week comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_sales = df.groupby('day_name')['quantity_sold'].sum().reindex(dow_order)
    colors_dow = ['lightblue' if day not in ['Saturday', 'Sunday'] else 'lightcoral' for day in dow_order]
    ax.bar(dow_order, dow_sales.values, color=colors_dow)
    ax.set_title('Sales Volume by Day of Week', fontsize=16, fontweight='bold')
    ax.set_xlabel('Day', fontsize=12)
    ax.set_ylabel('Total Units Sold', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    for i, v in enumerate(dow_sales.values):
        ax.text(i, v, f'{v:,.0f}', ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_day_of_week.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_day_of_week.png")
    
    # 7. Top promotions by volume
    fig, ax = plt.subplots(figsize=(12, 7))
    promo_sales = df[df['promotion_flag'] == 1].groupby('promotion_name')['quantity_sold'].sum().sort_values(ascending=True)
    if len(promo_sales) > 0:
        promo_sales.plot(kind='barh', ax=ax, color='gold')
        ax.set_title('Sales Volume by Promotion', fontsize=16, fontweight='bold')
        ax.set_xlabel('Units Sold', fontsize=12)
        ax.set_ylabel('Promotion', fontsize=12)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / 'sales_pos_promotion_volume.png', dpi=300, bbox_inches='tight')
        plt.close()
        logging.info("Saved sales_pos_promotion_volume.png")
    else:
        plt.close()
    
    # 8. Regional SKU preferences heatmap
    fig, ax = plt.subplots(figsize=(14, 8))
    regional_sku = df.pivot_table(
        values='quantity_sold',
        index='sku',
        columns='region',
        aggfunc='sum',
        fill_value=0
    )
    sns.heatmap(regional_sku, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Units Sold'})
    ax.set_title('Regional SKU Preferences Heatmap', fontsize=16, fontweight='bold')
    ax.set_xlabel('Region', fontsize=12)
    ax.set_ylabel('SKU', fontsize=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_regional_sku_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_regional_sku_heatmap.png")
    
    # 9. Price distribution by SKU
    fig, ax = plt.subplots(figsize=(14, 7))
    sku_list = df['sku'].value_counts().head(10).index.tolist()
    df_top_skus = df[df['sku'].isin(sku_list)]
    sns.boxplot(data=df_top_skus, x='price', y='sku', ax=ax, palette='Set2')
    ax.set_title('Price Distribution by Top 10 SKUs', fontsize=16, fontweight='bold')
    ax.set_xlabel('Price ($)', fontsize=12)
    ax.set_ylabel('SKU', fontsize=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_price_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_price_distribution.png")
    
    # 10. Top 20 retailers by revenue
    fig, ax = plt.subplots(figsize=(12, 8))
    retailer_rev = df.groupby('retailer_id')['revenue'].sum().sort_values(ascending=True).tail(20)
    retailer_rev.plot(kind='barh', ax=ax, color='mediumseagreen')
    ax.set_title('Top 20 Retailers by Revenue', fontsize=16, fontweight='bold')
    ax.set_xlabel('Total Revenue ($)', fontsize=12)
    ax.set_ylabel('Retailer ID', fontsize=12)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'sales_pos_top_retailers.png', dpi=300, bbox_inches='tight')
    plt.close()
    logging.info("Saved sales_pos_top_retailers.png")

def main():
    """
    Main execution function for Sales POS EDA.
    """
    # Load and prepare data
    df = load_and_prepare()
    
    # Generate summary statistics
    summary_stats(df)
    
    # Generate grouped summaries
    grouped_summaries(df)
    
    # Generate visualizations
    visualizations(df)
    
    logging.info("✅ Sales POS EDA complete!")

if __name__ == '__main__':
    main()
