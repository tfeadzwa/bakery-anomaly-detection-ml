"""Streamlit EDA Explorer - Interactive viewer for all dataset EDAs

Shows:
- Dataset selector (Returns, Waste, Inventory, Production, Sensors)
- Sample data view
- Summary statistics
- Key visualizations
- Download buttons for reports

Run:
    streamlit run app/streamlit_eda_explorer.py
"""
from pathlib import Path
import streamlit as st
import pandas as pd
import json
from PIL import Image

st.set_page_config(page_title="EDA Explorer", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = Path('data/processed')
REPORTS_DIR = Path('reports')
FIGURES_DIR = REPORTS_DIR / 'figures'
SUMMARIES_DIR = REPORTS_DIR / 'summaries'

DATASETS = {
    'Production': {
        'file': 'production_dataset.parquet',
        'description': '**Production Dataset** - The backbone of the entire supply chain. Tracks batch production, line performance, operator efficiency, and quality defects. All downstream analysis (dispatch, waste, QC, returns) starts here.',
        'summary_file': 'production_summary.txt',
        'figures': ['production_qty_hist.png', 'production_by_plant_bar.png', 'production_timeseries.png', 'production_by_hour.png', 'production_defects_breakdown.png', 'production_by_line.png', 'production_by_sku.png'],
        'summaries': ['production_by_plant.csv', 'production_by_line.csv', 'production_by_operator.csv', 'production_by_sku.csv', 'production_by_hour.csv', 'production_defects_summary.csv']
    },
    'Quality Control': {
        'file': 'quality_control_dataset.parquet',
        'description': '**Quality Control (QC) Dataset** - Critical checkpoint between Production and Dispatch. Every batch undergoes QC inspection (moisture, weight, temp, color, texture, seal). Failed QC = waste/rework. Links batch_id to quality outcomes. **36.15% fail rate** indicates major quality issues requiring immediate attention.',
        'summary_file': 'qc_summary.txt',
        'figures': ['qc_fail_rate_by_parameter.png', 'qc_value_distribution_by_parameter.png', 'qc_fail_rate_timeseries.png', 'qc_fail_rate_by_sku.png', 'qc_hourly_pattern.png', 'qc_pass_fail_pie.png', 'qc_failed_batches_by_parameter.png', 'qc_checks_per_batch_hist.png'],
        'summaries': ['qc_by_parameter.csv', 'qc_by_sku.csv', 'qc_by_batch.csv', 'qc_failed_batches_detail.csv', 'qc_by_hour.csv', 'qc_by_date.csv']
    },
    'Dispatch': {
        'file': 'dispatch_dataset.parquet',
        'description': '**Dispatch Dataset** - The bridge from bakery to retailers. Tracks delivery performance, route efficiency, vehicle reliability, and product freshness. Controls timing between production and sales. **74.6% on-time rate** below 90% target indicates logistical issues requiring optimization.',
        'summary_file': 'dispatch_summary.txt',
        'figures': ['dispatch_delay_hist.png', 'dispatch_delay_by_route_box.png', 'delay_hour_day_heatmap.png', 'dispatch_ontime_by_route.png', 'dispatch_volume_by_sku.png', 'dispatch_delay_category_pie.png', 'dispatch_volume_timeseries.png', 'dispatch_delay_by_vehicle.png'],
        'summaries': ['dispatch_by_plant.csv', 'dispatch_by_route.csv', 'dispatch_by_vehicle.csv', 'dispatch_by_sku.csv', 'dispatch_by_retailer_top50.csv', 'dispatch_by_hour.csv']
    },
    'Sales POS': {
        'file': 'sales_pos_dataset.parquet',
        'description': '**Sales / Retail POS Dataset** - THE DEMAND SIGNAL (B2C channel). Records actual customer purchases at retail outlets. Validates whether production and dispatch decisions were correct. 15,000 transactions, 464,793 units sold, $691,360 revenue. **Promotions deliver +39.1% quantity uplift**. This is the ground truth that drives forecasting and optimization.',
        'summary_file': 'sales_pos_summary.txt',
        'figures': ['sales_pos_volume_by_sku.png', 'sales_pos_revenue_by_region.png', 'sales_pos_promotion_effectiveness.png', 'sales_pos_daily_trend.png', 'sales_pos_hourly_pattern.png', 'sales_pos_day_of_week.png', 'sales_pos_promotion_volume.png', 'sales_pos_regional_sku_heatmap.png', 'sales_pos_price_distribution.png', 'sales_pos_top_retailers.png'],
        'summaries': ['sales_pos_by_sku.csv', 'sales_pos_by_region.csv', 'sales_pos_by_retailer_top50.csv', 'sales_pos_by_date.csv', 'sales_pos_by_hour.csv', 'sales_pos_by_promotion.csv', 'sales_pos_regional_sku_preferences.csv']
    },
    'Sales B2B': {
        'file': 'sales_dataset.parquet',
        'description': '**Sales Dataset (B2B Channel)** - WHOLESALE DISTRIBUTION. Depot → Store orders (15,099 orders, 2.45M units, $3.5M revenue). **Avg order: 162 units (5x larger than retail)**. 11 depots serving 139 stores via 50 routes. Balanced depot network (31.4% top 3). Monday peak ordering. Compare with Sales POS to validate inventory flow.',
        'summary_file': 'sales_b2b_enhanced_summary.txt',
        'figures': ['sales_b2b_by_depot.png', 'sales_b2b_by_store_top20.png', 'sales_b2b_route_efficiency_top15.png', 'sales_b2b_by_sku.png', 'sales_b2b_daily_trend.png', 'sales_b2b_day_of_week.png', 'sales_b2b_hourly_pattern.png', 'sales_b2b_order_size_distribution.png', 'sales_b2b_depot_sku_heatmap.png', 'sales_b2b_pricing_by_sku.png', 'sales_b2b_depot_share_pie.png', 'sales_b2b_depot_revenue.png'],
        'summaries': ['sales_b2b_by_depot.csv', 'sales_b2b_by_store_top50.csv', 'sales_b2b_by_route_top30.csv', 'sales_b2b_by_sku.csv', 'sales_b2b_by_date.csv', 'sales_b2b_depot_sku_matrix.csv', 'sales_b2b_route_store_network.csv']
    },
    'Inventory': {
        'file': 'inventory_stock_movements_dataset.parquet',
        'description': '**Inventory / Stock Movements** - THE STATE OF THE SYSTEM. Final reconciliation of all activities (18,073 records, 4.28M in, 3.54M out). **🚨 CRITICAL: 29.2% negative balances** = severe data integrity crisis. Flow efficiency only 8.6% (should be 100%). Exposes missing records, double-counting, unlogged waste. Inventory is the "final truth" - if numbers don\'t add up here, something upstream failed.',
        'summary_file': 'inventory_enhanced_summary.txt',
        'figures': ['inventory_movement_types.png', 'inventory_balance_distribution.png', 'inventory_negative_balances.png', 'inventory_qty_flow.png', 'inventory_sku_balances.png', 'inventory_daily_trend.png', 'inventory_expiry_risk_pie.png', 'inventory_days_to_expiry.png', 'inventory_plant_vs_store.png', 'inventory_adjustments.png', 'inventory_turnover_ratio.png', 'inventory_net_movement_dow.png'],
        'summaries': ['inventory_by_movement_type.csv', 'inventory_by_location.csv', 'inventory_by_sku.csv', 'inventory_by_date.csv', 'inventory_expiry_risk.csv', 'inventory_anomalies_top50.csv']
    },
    'Route Metadata': {
        'file': 'route_transport_multivehicle.parquet',
        'description': '**Route & Transport Metadata** - THE "WHY" BEHIND LOGISTICS. Reference dataset (216 configs, 69 routes, 101 vehicles, 119 drivers). Avg route: 57.6km, 2.2 hours, 13 stops. **Speed: 31.7 km/h** (includes stop time). **47.7% rural routes** (>60km, freshness risk). **100% vehicles underutilized** (<50% capacity). 4 high-risk routes (>0.7 score) need priority monitoring. Links to dispatch for delay normalization.',
        'summary_file': 'routes_transport_meta_summary.txt',
        'figures': ['routes_distance_distribution.png', 'routes_type_distribution.png', 'routes_stops_distribution.png', 'routes_distance_vs_stops.png', 'routes_by_region.png', 'routes_capacity_distribution.png', 'routes_capacity_strain.png', 'routes_efficiency_by_type.png', 'routes_start_window.png', 'routes_risk_distribution.png', 'routes_top_risk.png', 'routes_complexity_vs_risk.png'],
        'summaries': ['routes_by_route.csv', 'routes_by_region.csv', 'routes_by_vehicle.csv', 'routes_by_driver.csv', 'routes_by_type.csv', 'routes_high_risk_top50.csv']
    },
    'Waste': {
        'file': 'waste_dataset.parquet',
        'description': '**Waste Dataset** - THE FINAL LOSS. 1.3M units wasted (59.3% production, 40.7% post-dispatch). Top reason: Contaminated (10.5%). **Night shift worst performer (33.6%)**. Direct financial loss requiring immediate prevention. Production quality + cold chain failures dominate.',
        'summary_file': 'waste_enhanced_summary.txt',
        'figures': ['waste_by_stage.png', 'waste_by_reason_top10.png', 'waste_by_sku.png', 'waste_daily_trend.png', 'waste_by_shift.png', 'waste_temperature_distribution.png', 'waste_by_handling_condition.png', 'waste_day_of_week.png', 'waste_by_route_top15.png', 'waste_stage_pie.png'],
        'summaries': ['waste_by_stage.csv', 'waste_by_reason.csv', 'waste_by_sku.csv', 'waste_by_plant.csv', 'waste_by_shift.csv', 'waste_by_handling.csv', 'waste_by_route_top30.csv', 'waste_by_retailer_top30.csv']
    },
    'Returns': {
        'file': 'returns_dataset.parquet',
        'description': '**Returns Dataset** - DOWNSTREAM FAILURE SIGNAL. 791K units returned from retailers (58.4% preventable: expired/damaged/mould). Top reason: Mould Growth (15%). Worst route: RT_058. Worst retailer: STORE_086. Returns often lead to waste - critical feedback loop for dispatch optimization.',
        'summary_file': 'returns_enhanced_summary.txt',
        'figures': ['returns_by_reason.png', 'returns_by_route_top15.png', 'returns_by_retailer_top15.png', 'returns_by_sku.png', 'returns_daily_trend.png', 'returns_day_of_week.png', 'returns_temperature_distribution.png', 'returns_by_handling_condition.png', 'returns_quantity_distribution.png', 'returns_reason_pie.png'],
        'summaries': ['returns_by_reason.csv', 'returns_by_route_top30.csv', 'returns_by_retailer_top30.csv', 'returns_by_sku.csv', 'returns_by_handling.csv', 'returns_by_date.csv']
    },
    'Sensors/IoT': {
        'file': 'equipment_iot_sensor_dataset.parquet',
        'description': '**Equipment & IoT Sensors** - Temperature, equipment metrics, and sensor readings from plants. Root cause analysis for quality issues and equipment failures.',
        'summary_file': 'sensors_summary.txt',
        'figures': ['sensors_value_hist.png', 'sensors_by_metric_box.png', 'sensors_timeseries.png', 'sensors_by_equipment_bar.png'],
        'summaries': ['sensors_by_plant.csv', 'sensors_by_metric_name.csv', 'sensors_by_equipment.csv']
    } 
}
 

# Visualization explanations for each figure
VIZ_EXPLANATIONS = {
    'production_qty_hist.png': {
        'title': '📊 Batch Size Distribution',
        'explanation': 'Distribution of production batch sizes with mean (red) and median (green) reference lines. **Key insights:** Batch consistency indicates production stability. Mean ~1,098 units. Tight distribution = standardized runs; wide spread = variable planning or equipment constraints.',
        'key_points': ['• **X-axis:** Batch size (units produced)', '• **Y-axis:** Frequency of batches', '• **Red line:** Mean batch size (1,098)', '• **Green line:** Median batch size', '• **Tight peak:** Consistent batch planning', '• **Long tail:** Investigate small/large batch anomalies']
    },
    'production_by_plant_bar.png': {
        'title': '🏭 Production Volume & Defect Rates by Plant',
        'explanation': 'Dual chart showing total production volume (left) and overall defect rate % (right) for each plant. **Key insights:** Balances production capacity with quality. High volume + high defects = process issues; low volume + high defects = equipment/training needs.',
        'key_points': ['• **Left chart:** Total units produced per plant', '• **Right chart:** Defect rate % by plant', '• **Blue bars:** Production capacity utilization', '• **Orange bars:** Quality performance (lower is better)', '• **Compare:** Volume vs. quality trade-offs', '• **Target:** <3% defect rate benchmark']
    },
    'production_timeseries.png': {
        'title': '📈 Daily Production Trends',
        'explanation': 'Daily production volumes over time with average reference line (red). **Key insights:** Shows production stability and identifies disruptions. Consistent output = healthy operations; sudden drops = equipment downtime, material shortages, or demand changes.',
        'key_points': ['• **X-axis:** Date (2025-01 to 2025-10)', '• **Y-axis:** Daily production quantity', '• **Red line:** Average daily production', '• **Above average:** High-demand periods', '• **Below average:** Investigate capacity issues', '• **Gaps:** Production shutdowns or data quality issues']
    },
    'production_by_hour.png': {
        'title': '⏰ Hourly Production Patterns (Shift Analysis)',
        'explanation': 'Average production by hour of day with batch count annotations. **Key insights:** Reveals shift patterns and identifies peak productivity hours. Helps optimize scheduling and staffing. Expected peaks during 1st/2nd shifts; valleys during off-shifts.',
        'key_points': ['• **X-axis:** Hour (0-23, 24-hour format)', '• **Y-axis:** Average production quantity', '• **Annotations:** Total batch count per hour', '• **Peaks:** High-productivity shifts (typically 6am-2pm, 2pm-10pm)', '• **Valleys:** Night shift or downtime', '• **Use case:** Optimize shift scheduling and line assignments']
    },
    'production_defects_breakdown.png': {
        'title': '🔍 Defect Type Analysis (Bar + Pie)',
        'explanation': 'Comprehensive defect breakdown showing 7 defect categories. **Total:** 444,447 defects (2.68% overall rate). **Key insights:** Identifies dominant defect types for targeted waste reduction. Bar chart shows absolute counts; pie chart shows proportions.',
        'key_points': ['• **7 defect types:** stacked_before_robot, squashed, torn, undersized_small, valleys, loose_packs, pale_underbaked', '• **Bar chart (left):** Absolute defect counts by type', '• **Pie chart (right):** Percentage breakdown', '• **Top defects:** Focus quality improvement here', '• **Action items:** Root cause analysis for top 2-3 defect types', '• **Impact:** Defects drive waste, returns, and QC failures downstream']
    },
    'production_by_line.png': {
        'title': '🏭 Production by Line (Top 10)',
        'explanation': 'Total production volume comparison across production lines. **Key insights:** Shows line utilization and capacity balance. 5 lines evenly distributed (~3,000 batches each = good load balancing). Identifies underperforming or over-utilized lines.',
        'key_points': ['• **X-axis:** Production line identifier', '• **Y-axis:** Total batches produced', '• **Even distribution:** Well-balanced line utilization', '• **Outliers:** Investigate capacity constraints or efficiency issues', '• **Top performers:** Line5 (3,036), Line3 (3,027), Line1 (3,015)', '• **Use case:** Line assignment optimization and capacity planning']
    },
    'production_by_sku.png': {
        'title': '🍞 Production by SKU (Top 10)',
        'explanation': 'Top 10 SKUs by production volume (horizontal bar chart). **Key insights:** Shows product mix and demand patterns. Top 7 SKUs evenly distributed (~14% each) = balanced portfolio. Heavily skewed production = demand concentration risk.',
        'key_points': ['• **X-axis:** Total production quantity', '• **Y-axis:** SKU names (sorted by volume)', '• **Top SKUs:** Seed Loaf (14.6%), Family Loaf (14.6%), Whole Wheat (14.5%)', '• **Balance:** Even distribution = diversified demand', '• **Skew:** Investigate if one SKU dominates (single-point-of-failure risk)', '• **Use case:** Production planning, batch sizing, line assignment per SKU']
    },
    'qc_fail_rate_by_parameter.png': {
        'title': '🧪 QC Fail Rate by Parameter',
        'explanation': 'Bar chart showing QC fail rate % for each quality parameter (moisture, weight, temp, color, texture, seal, slice uniformity). **CRITICAL:** Overall 36.15% fail rate (Target: <2%). Color-coded: Red >5%, Orange >2%, Green ≤2%. **Key insight:** crust_color_level (55.53%) and slice_uniformity_mm (54.32%) are top problem areas.',
        'key_points': ['• **X-axis:** QC parameter type', '• **Y-axis:** Fail rate %', '• **Red bars:** Critical issues (>5% fail rate)', '• **Orange bars:** Warning (>2% fail rate)', '• **Green bars:** Acceptable (≤2%)', '• **Blue dashed line:** 2% target threshold', '• **Action:** Focus on top 3 failing parameters for immediate improvement']
    },
    'qc_value_distribution_by_parameter.png': {
        'title': '📏 QC Parameter Value Distributions',
        'explanation': 'Box plot showing measurement value ranges for each QC parameter. **Key insights:** Wide boxes = high variability (process inconsistency); outliers = extreme measurements requiring investigation. Helps identify tolerance limit issues and calibration problems.',
        'key_points': ['• **X-axis:** Measurement values', '• **Y-axis:** QC parameters', '• **Box:** Interquartile range (middle 50% of values)', '• **Line in box:** Median value', '• **Whiskers:** Min/max within 1.5×IQR', '• **Dots:** Outliers (potential defects or sensor errors)', '• **Use case:** Validate tolerance limits, identify measurement drift']
    },
    'qc_fail_rate_timeseries.png': {
        'title': '📈 QC Fail Rate Trend Over Time',
        'explanation': 'Daily QC fail rate % tracked over time (Jan-Jul 2025). **Key insights:** Shows quality deterioration or improvement trends. Rising trend = worsening quality; falling trend = process improvements taking effect. Helps identify seasonal patterns or production changes affecting quality.',
        'key_points': ['• **X-axis:** Date', '• **Y-axis:** Daily fail rate %', '• **Red line:** Daily fail rate trend', '• **Blue dashed:** Average fail rate (36.15%)', '• **Green dashed:** Target (2%)', '• **Spikes:** Investigate production issues on those dates', '• **Action:** Correlate spikes with production logs, equipment changes, operator shifts']
    },
    'qc_fail_rate_by_sku.png': {
        'title': '🍞 QC Fail Rate by SKU (Top 10 Worst)',
        'explanation': 'Horizontal bar chart showing top 10 SKUs with highest QC fail rates. **Key insights:** Identifies problematic products requiring recipe/process review. "Whole grain Brown" at 71.43% indicates severe quality issues. Some SKUs may have unrealistic tolerance limits.',
        'key_points': ['• **X-axis:** Fail rate %', '• **Y-axis:** SKU names (sorted worst to better)', '• **Red bars:** Critical (>5%)', '• **Orange bars:** Warning (>2%)', '• **Yellow bars:** Below 5% but above target', '• **Green line:** 2% target', '• **Action:** Recipe review for top 3 SKUs, adjust tolerance limits if needed']
    },
    'qc_hourly_pattern.png': {
        'title': '⏰ QC Hourly Pattern (Shift Analysis)',
        'explanation': 'Dual chart: Top shows fail rate % by hour; Bottom shows QC check volume by hour. **Key insights:** Hour 15 (3pm) has peak failures (39.04%) - shift fatigue? Hour 21 (9pm) has best performance (31.65%). Helps identify shift-specific quality issues and staffing optimization.',
        'key_points': ['• **Top chart:** QC fail rate by hour (red line)', '• **Bottom chart:** Number of QC checks per hour (blue bars)', '• **Peak failures:** Hour 15 - investigate afternoon shift issues', '• **Best performance:** Hour 21 - study what\'s working', '• **Check volume:** Shows production/QC activity by shift', '• **Action:** Assign best operators during high-volume hours, address shift fatigue']
    },
    'qc_pass_fail_pie.png': {
        'title': '🥧 QC Pass vs Fail Distribution',
        'explanation': 'Pie chart showing overall proportion of passed vs failed QC checks. **CRITICAL:** 36.15% failure rate (6,540 fails out of 18,090 checks). This is 18X above target (2%). **Immediate action required** - massive quality crisis affecting 3 out of 4 batches.',
        'key_points': ['• **Green slice:** Passed checks (63.85%)', '• **Red slice:** Failed checks (36.15%)', '• **Total checks:** 18,090', '• **Target:** >98% pass rate', '• **Current:** Only 63.85% pass - severe underperformance', '• **Impact:** High fail rate drives waste, rework costs, dispatch delays', '• **Action:** Immediate quality task force, root cause analysis, process overhaul']
    },
    'qc_failed_batches_by_parameter.png': {
        'title': '❌ Failed Batches by QC Parameter',
        'explanation': 'Bar chart showing number of unique batches that failed for each QC parameter. **Key insights:** Identifies which parameters cause the most batch rejections. Focus quality improvements on parameters affecting most batches (crust_color, slice_uniformity, internal_temp).',
        'key_points': ['• **X-axis:** QC parameter', '• **Y-axis:** Number of batches with failures', '• **Dark red bars:** Batch rejection counts', '• **Top offenders:** Parameters causing most batch failures', '• **4,476 batches (74.6%) had failures** out of 6,000 inspected', '• **Action:** Prioritize fixing top 3 parameters to reduce batch rejections', '• **Link to waste:** Failed batches → waste or rework → cost']
    },
    'qc_checks_per_batch_hist.png': {
        'title': '🔍 QC Check Intensity Distribution',
        'explanation': 'Histogram showing how many QC checks are performed per batch. **Key insights:** Mean ~3 checks per batch. Consistent checking intensity = standardized QC protocol. Wide variation may indicate inconsistent inspection rigor across shifts/operators.',
        'key_points': ['• **X-axis:** Number of QC checks per batch', '• **Y-axis:** Frequency (number of batches)', '• **Red line:** Mean checks per batch (~3)', '• **Green line:** Median checks per batch', '• **Tight peak:** Consistent QC protocol adherence', '• **Wide spread:** Inconsistent inspection rigor', '• **Action:** Standardize QC check frequency, ensure all parameters tested per batch']
    },
    'dispatch_delay_hist.png': {
        'title': '🚚 Dispatch Delay Distribution',
        'explanation': 'Histogram of dispatch delays (actual - expected arrival time). **Key insights:** Mean 17.1 min delay. Positive values = late delivery (stale bread risk), negative = early (good freshness). Wide spread indicates inconsistent route performance.',
        'key_points': ['• **X-axis:** Delay in minutes (negative = early, positive = late)', '• **Y-axis:** Frequency of dispatches', '• **Red line:** Mean delay (17.1 min)', '• **Green line:** Median delay (17.0 min)', '• **Blue line:** On-time (0 min)', '• **Target:** Delays within ±30 minutes', '• **Action:** Investigate extreme delays, optimize slow routes']
    },
    'dispatch_delay_by_route_box.png': {
        'title': '🛣️ Dispatch Delay by Route (Top 20)',
        'explanation': 'Box plot showing delay distributions for top 20 busiest routes. **Key insights:** Box width = consistency; median line = typical delay. Routes with high median or wide boxes need optimization. Identifies problematic routes causing late deliveries.',
        'key_points': ['• **X-axis:** Route ID (sorted by median delay)', '• **Y-axis:** Delay in minutes', '• **Box:** Middle 50% of delays', '• **Line in box:** Median delay', '• **Whiskers:** Min/max delays', '• **Outliers:** Extreme delays (breakdowns, traffic)', '• **Blue line:** On-time (0 min)', '• **Action:** Focus on routes with median >30 min or wide boxes']
    },
    'delay_hour_day_heatmap.png': {
        'title': '🗓️ Delay Heatmap: Hour × Day of Week',
        'explanation': 'Heatmap showing average delay patterns by hour and day. **Key insights:** Red = high delays (traffic, demand surges); Green = low delays. Identifies peak congestion times and best dispatch windows. Hour 15 (3pm) shows highest delays.',
        'key_points': ['• **X-axis:** Hour of day (0-23)', '• **Y-axis:** Day of week', '• **Color:** Red = longer delays, Green = shorter delays', '• **Peak delays:** Typically weekday afternoons (traffic)', '• **Best times:** Early morning, late evening', '• **Action:** Schedule critical deliveries during green zones', '• **Use case:** Route planning, dispatch time optimization']
    },
    'dispatch_ontime_by_route.png': {
        'title': '✅ On-Time Delivery Rate by Route',
        'explanation': 'Horizontal bar chart showing on-time rate % for top 20 routes (min 10 trips). **Key insights:** Green bars >90% = excellent; Orange 80-90% = acceptable; Red <80% = needs immediate attention. Current overall: 74.6% (below 90% target).',
        'key_points': ['• **X-axis:** On-time delivery rate %', '• **Y-axis:** Route ID', '• **Green bars:** >90% on-time (target met)', '• **Orange bars:** 80-90% (needs improvement)', '• **Red bars:** <80% (critical)', '• **Blue line:** 90% target', '• **Action:** Prioritize red/orange routes for optimization', '• **Impact:** Low on-time rates → stale bread → waste → returns']
    },
    'dispatch_volume_by_sku.png': {
        'title': '🍞 Dispatch Volume by SKU (Top 10)',
        'explanation': 'Horizontal bar chart showing total quantity dispatched for top 10 SKUs. **Key insights:** Reveals demand patterns and product distribution focus. Top SKUs: Soft White, Seed Loaf, Whole Wheat (each ~14%). Even distribution = balanced demand.',
        'key_points': ['• **X-axis:** Total units dispatched', '• **Y-axis:** SKU names', '• **Top SKUs:** Products with highest distribution volume', '• **Even distribution:** Balanced demand across products', '• **Skewed distribution:** Demand concentration (single-point risk)', '• **Use case:** Production planning, route loading optimization', '• **Link to waste:** High volume SKUs must have efficient dispatch to avoid staleness']
    },
    'dispatch_delay_category_pie.png': {
        'title': '⏱️ Delay Category Distribution',
        'explanation': 'Pie chart showing proportion of dispatches in each delay category. **Key insights:** Only 54.8% on-time (±30 min), 25.4% late (30-60 min). Target: >80% on-time. Current performance indicates systemic delivery issues.',
        'key_points': ['• **Green slice:** On-Time (±30 min) - 54.8%', '• **Yellow/Orange slices:** Late (30-60 min) - 25.4%', '• **Light green:** Early (<30 min) - 19.8%', '• **Target:** >80% in on-time category', '• **Current:** Only 54.8% on-time = poor performance', '• **Impact:** Late deliveries → stale product → waste/returns', '• **Action:** Route optimization, vehicle upgrades, driver training']
    },
    'dispatch_volume_timeseries.png': {
        'title': '📈 Daily Dispatch Volume Trend',
        'explanation': 'Line chart showing number of dispatches per day over time. **Key insights:** Shows dispatch consistency and identifies volume spikes/drops. Average ~59 dispatches/day. Consistent volume = stable operations; spikes = high demand periods.',
        'key_points': ['• **X-axis:** Date (Jan-Jul 2025)', '• **Y-axis:** Number of dispatch events', '• **Blue line:** Daily dispatch count', '• **Red dashed:** Average daily dispatches', '• **Spikes:** High-demand periods (holidays, promotions)', '• **Drops:** Low-demand or operational issues', '• **Action:** Correlate drops with production/quality issues', '• **Use case:** Capacity planning, demand forecasting']
    },
    'dispatch_delay_by_vehicle.png': {
        'title': '🚛 Vehicle Performance (Top 15 Worst)',
        'explanation': 'Horizontal bar chart showing mean delay for vehicles with longest delays (min 10 trips). **Key insights:** Identifies unreliable vehicles. Red bars >60 min = critical maintenance needed. Worst: TRUCK_005 (19.6 min avg delay). Vehicle issues cause late deliveries.',
        'key_points': ['• **X-axis:** Mean delay in minutes', '• **Y-axis:** Vehicle ID', '• **Red bars:** >60 min avg delay (critical)', '• **Orange bars:** 30-60 min (needs attention)', '• **Yellow bars:** <30 min (acceptable)', '• **Blue line:** 30 min target threshold', '• **Action:** Maintenance schedule for worst performers, consider replacement', '• **Impact:** Unreliable vehicles → late deliveries → waste → customer dissatisfaction']
    },
    'sales_pos_volume_by_sku.png': {
        'title': '🍞 Sales Volume by SKU (Total Units Sold)',
        'explanation': 'Horizontal bar chart showing total units sold for each SKU. **Key insights:** Reveals fast-moving vs slow-moving products. Top 7 SKUs (Whole Wheat, High Energy White, Family Loaf, Seed Loaf, Wholegrain Brown, Soft White, High Energy Brown) dominate with ~65K units each (~14% each). Balanced portfolio = low SKU concentration risk.',
        'key_points': ['• **X-axis:** Total units sold', '• **Y-axis:** SKU names (sorted by volume)', '• **Green bars:** Above-median sellers (fast-movers)', '• **Orange bars:** Below-median sellers (slow-movers)', '• **Red line:** Median sales volume', '• **Fast-movers:** Prioritize for production and dispatch', '• **Slow-movers:** Evaluate for discontinuation or reduced batch sizes', '• **Use case:** SKU rationalization, demand forecasting']
    },
    'sales_pos_revenue_by_region.png': {
        'title': '💰 Total Revenue by Region',
        'explanation': 'Bar chart of total sales revenue across 8 regions (Bindura, Gweru, Harare, Mutare, Kwekwe, Chitungwiza, Masvingo, Bulawayo). **Key insights:** Bindura leads with highest revenue (~$90K). Relatively balanced regional demand (~$85-90K per region) indicates nationwide market penetration with no extreme concentration.',
        'key_points': ['• **X-axis:** Region names', '• **Y-axis:** Total revenue ($)', '• **Annotations:** Revenue values displayed above bars', '• **Top region:** Bindura (highest revenue opportunity)', '• **Even distribution:** Low regional dependency risk', '• **Use case:** Regional expansion strategy, targeted promotions', '• **Action:** Investigate why top regions outperform others']
    },
    'sales_pos_promotion_effectiveness.png': {
        'title': '🎯 Promotion Effectiveness Analysis',
        'explanation': 'Dual bar chart comparing average units sold (left) and average revenue (right) per transaction with vs without promotions. **CRITICAL FINDING:** Promotions deliver +39.1% quantity uplift and +26.8% revenue uplift. Proves promotion ROI is positive and should be expanded strategically.',
        'key_points': ['• **Left chart:** Avg units per transaction (No Promo: 30.8, With Promo: 42.8)', '• **Right chart:** Avg revenue per transaction (No Promo: $45.85, With Promo: $58.13)', '• **Green bars:** With Promotion (higher is better)', '• **Red bars:** No Promotion (baseline)', '• **Uplift calculation:** (Promo / No Promo) - 1', '• **Action:** Expand promotions during slow demand periods', '• **Best promotions:** Women\'s Day, Africa Day, Independence Day']
    },
    'sales_pos_daily_trend.png': {
        'title': '📈 Daily Sales Trend with Moving Average',
        'explanation': 'Time series showing daily units sold from Jan 1 to Jul 30, 2025. Dark blue line = daily sales, red line = 7-day moving average, light blue fill = volume. **Key insights:** Identifies demand volatility, seasonal patterns, and anomalies. Smooth moving average helps filter noise and reveal underlying trends.',
        'key_points': ['• **X-axis:** Date (Jan-Jul 2025)', '• **Y-axis:** Daily units sold', '• **Blue line:** Actual daily sales (volatile)', '• **Red line:** 7-day moving average (trend)', '• **Filled area:** Visual emphasis on volume', '• **Spikes:** High-demand days (holidays, promotions)', '• **Dips:** Low-demand periods (investigate causes)', '• **Use case:** Demand forecasting, production planning']
    },
    'sales_pos_hourly_pattern.png': {
        'title': '⏰ Sales Volume by Hour of Day',
        'explanation': 'Bar chart + line plot showing total units sold by hour (0-23). **Key insights:** Peak sales hour is 10:00 AM (21,742 units), lowest is 21:00/9PM (17,566 units). Relatively flat hourly distribution suggests 24-hour retail operations with consistent demand. No extreme peaks/valleys = stable demand profile.',
        'key_points': ['• **X-axis:** Hour of day (0-23, 24-hour format)', '• **Y-axis:** Total units sold', '• **Teal bars:** Hourly volume', '• **Red line:** Trend line connecting hourly peaks', '• **Peak hour:** 10:00 AM (morning shopping)', '• **Low hour:** 21:00/9PM (late evening)', '• **Flat pattern:** 24-hour retail coverage', '• **Use case:** Staffing optimization, dispatch timing']
    },
    'sales_pos_day_of_week.png': {
        'title': '📅 Sales Volume by Day of Week',
        'explanation': 'Bar chart comparing total units sold across 7 days (Mon-Sun). **Key insights:** Sunday has highest sales (69,272 units), followed by Friday (68,626) and Monday (68,595). Weekend shopping behavior visible. Tuesday is weakest day (61,508 units). Minimal weekday vs weekend difference (~2% variance).',
        'key_points': ['• **X-axis:** Day of week', '• **Y-axis:** Total units sold', '• **Blue bars:** Weekdays (Mon-Fri)', '• **Red bars:** Weekend (Sat-Sun)', '• **Annotations:** Volume displayed above bars', '• **Peak days:** Sunday, Friday, Monday', '• **Low days:** Tuesday (investigate cause)', '• **Use case:** Weekly production planning, promotion scheduling']
    },
    'sales_pos_promotion_volume.png': {
        'title': '🏷️ Sales Volume by Promotion',
        'explanation': 'Horizontal bar chart showing units sold during each promotion campaign. **Key insights:** Women\'s Day Promo leads with 3,514 units, followed by Africa Day (3,388) and Independence Day (2,901). Valentine Promo has lowest volume (2,688). Only 2% of sales (293/15,000 transactions) occurred during promotions = huge opportunity for expansion.',
        'key_points': ['• **X-axis:** Total units sold', '• **Y-axis:** Promotion name', '• **Gold bars:** Promotion-driven sales', '• **Top promo:** Women\'s Day (3,514 units)', '• **Bottom promo:** Valentine (2,688 units)', '• **Opportunity:** Only 2% of sales are promo-driven', '• **Action:** Increase promotion frequency and coverage', '• **Best timing:** National holidays and celebrations']
    },
    'sales_pos_regional_sku_heatmap.png': {
        'title': '🗺️ Regional SKU Preferences Heatmap',
        'explanation': 'Heatmap showing units sold for each SKU × Region combination. **Key insights:** Reveals regional taste preferences and product-market fit. Darker cells = higher demand. Uniform color distribution = consistent nationwide preferences; clustered hotspots = region-specific favorites requiring tailored dispatch strategies.',
        'key_points': ['• **X-axis:** Regions', '• **Y-axis:** SKUs', '• **Color intensity:** Units sold (red = high demand)', '• **Annotations:** Exact units sold per cell', '• **Use case:** Regional dispatch optimization', '• **Action:** Allocate high-demand SKUs to high-volume regions', '• **Insights:** Identify mismatches between dispatch and demand', '• **Strategy:** Customize SKU mix per region for reduced waste']
    },
    'sales_pos_price_distribution.png': {
        'title': '💲 Price Distribution by Top 10 SKUs',
        'explanation': 'Box plot showing price range for each SKU. **Key insights:** Family Loaf has highest avg price ($2.20), while High Energy Brown/White are lowest ($1.31). Tight boxes = consistent pricing; wide boxes = price variability (promotions, regional differences). Outliers indicate special pricing events.',
        'key_points': ['• **X-axis:** Price ($)', '• **Y-axis:** SKU names', '• **Box:** Interquartile range (25th-75th percentile)', '• **Line in box:** Median price', '• **Whiskers:** Price range (min/max)', '• **Dots:** Outliers (unusual prices)', '• **Use case:** Price elasticity analysis, promotion strategy', '• **Action:** Test price sensitivity for high-margin SKUs']
    },
    'sales_pos_top_retailers.png': {
        'title': '🏪 Top 20 Retailers by Revenue',
        'explanation': 'Horizontal bar chart ranking retailers by total revenue. **Key insights:** Top retailer generates ~$3,500-4,000 in revenue. Relatively even distribution among top 20 (no extreme outliers) = healthy retailer network with low single-customer dependency risk. Focus on replicating top performer success factors.',
        'key_points': ['• **X-axis:** Total revenue ($)', '• **Y-axis:** Retailer IDs (sorted by revenue)', '• **Green bars:** Top revenue generators', '• **Top performers:** Investigate success factors (location, service, pricing)', '• **Even distribution:** Low concentration risk', '• **Use case:** Retailer partnership strategy, sales team focus', '• **Action:** Expand similar profiles to underperforming regions']
    },
    
    # ==================== WASTE DATASET VISUALIZATIONS ====================
    'waste_by_stage.png': {
        'title': '🏭 Waste Volume: Production vs Post-Dispatch',
        'explanation': 'Horizontal bar chart comparing waste at production stage vs post-dispatch stage. **CRITICAL FINDING:** 59.3% of waste (772K units) occurs during production, 40.7% (531K units) post-dispatch. Production-dominant waste indicates quality control, equipment, or batch sizing issues. Focus interventions on production processes, not just logistics.',
        'key_points': ['• **X-axis:** Total units wasted', '• **Y-axis:** Waste stage (Production, Post-Dispatch)', '• **Red bar:** Production waste (59.3%) - quality/equipment failures', '• **Orange bar:** Post-dispatch waste (40.7%) - cold chain/logistics', '• **Target:** Reduce production waste below 50%', '• **Action:** Root cause analysis of production contamination, equipment maintenance', '• **Impact:** 772K units wasted at production = $1M+ direct loss', '• **Strategy:** QC tightening, shift training, batch traceability']
    },
    'waste_by_reason_top10.png': {
        'title': '❌ Top 10 Waste Reasons',
        'explanation': 'Horizontal bar chart showing units wasted by top 10 reasons. **CRITICAL FINDING:** "Contaminated" leads with 136,900 units (10.5%) = sanitation/process contamination issue. "Stale" and "Expired" follow = shelf-life/dispatch timing problems. Top 3 reasons account for 29% of all waste.',
        'key_points': ['• **X-axis:** Total units wasted', '• **Y-axis:** Waste reason codes', '• **Red bars:** Critical reasons (>100K units)', '• **Orange bars:** Significant reasons (50K-100K)', '• **Top reason:** Contaminated (136,900 units) - sanitation failure', '• **2nd/3rd:** Stale (129,420), Expired (124,660) - timing issues', '• **Action:** Sanitation audit, HACCP review, shelf-life optimization', '• **Impact:** Top 10 reasons = 93% of waste (addressable)', '• **Strategy:** Reason-specific intervention plans']
    },
    'waste_by_sku.png': {
        'title': '🍞 Waste by SKU',
        'explanation': 'Horizontal bar chart showing total waste for each SKU. **Key insights:** 7 SKUs account for >10% of waste each (Family Loaf, High Energy Brown, Seed Loaf, High Energy White, Whole Wheat, Soft White, Wholegrain Brown). Relatively even distribution = systemic issue affecting all products, not specific SKU defects.',
        'key_points': ['• **X-axis:** Total units wasted', '• **Y-axis:** SKU names', '• **Red bars:** >150K units wasted (high-waste SKUs)', '• **Orange bars:** 130K-150K (medium waste)', '• **Even distribution:** All SKUs ~14% waste = process issue, not recipe', '• **Action:** SKU-agnostic interventions (temperature, handling, contamination)', '• **Link to sales:** Cross-reference with best-sellers to prioritize', '• **Strategy:** Focus on high-volume SKUs for maximum impact']
    },
    'waste_daily_trend.png': {
        'title': '📈 Daily Waste Trend with Moving Average',
        'explanation': 'Time series showing daily waste units from Jan 1 to Jul 30, 2025. Dark red line = daily waste, yellow line = 7-day moving average, light red fill = volume. **Key insights:** Identifies waste spikes (contamination events, equipment failures), seasonal patterns, and trend direction. Moving average reveals if waste is increasing or decreasing.',
        'key_points': ['• **X-axis:** Date (Jan-Jul 2025)', '• **Y-axis:** Daily units wasted', '• **Red line:** Actual daily waste (volatile)', '• **Yellow line:** 7-day moving average (trend)', '• **Spikes:** Contamination events, batch failures', '• **Dips:** Good production days (analyze success factors)', '• **Trend:** Increasing trend = systemic deterioration', '• **Action:** Correlate spikes with batch IDs, shifts, plants', '• **Use case:** Early warning system for waste escalation']
    },
    'waste_by_shift.png': {
        'title': '🌙 Waste by Production Shift',
        'explanation': 'Bar chart comparing waste across Morning, Day, and Night shifts. **CRITICAL FINDING:** Night shift has 438,080 units wasted (33.6%) - worst performer despite likely equal production volume. Indicates supervision gaps, fatigue, or equipment issues during night operations. Immediate intervention needed.',
        'key_points': ['• **X-axis:** Shift names', '• **Y-axis:** Total units wasted', '• **Red bar:** Night shift (438K units, 33.6%) - CRITICAL', '• **Orange bars:** Morning (435K, 33.4%), Day (430K, 33.0%)', '• **Target:** <30% waste per shift (if equal production)', '• **Action:** Night shift supervision increase, training, equipment audit', '• **Impact:** Night shift waste costs $150K+ annually', '• **Strategy:** Shift-specific SOPs, manager presence, fatigue management']
    },
    'waste_temperature_distribution.png': {
        'title': '🌡️ Temperature at Waste Check',
        'explanation': 'Histogram showing temperature distribution when waste was recorded. **Key insights:** Most waste occurs at 20-30°C (ambient). High temperatures (>35°C) correlate with spoilage reasons (Mould Growth, Stale). Identifies cold chain failures if waste happens at high temps.',
        'key_points': ['• **X-axis:** Temperature (°C)', '• **Y-axis:** Frequency (number of waste incidents)', '• **Peak:** 20-30°C (most waste recorded at ambient)', '• **High temp:** >35°C = cold chain failure (spoilage)', '• **Low temp:** <10°C = proper refrigeration (non-temp waste)', '• **Action:** Cross-reference high-temp waste with reasons (Mould, Stale)', '• **Impact:** Temperature control critical for shelf-life', '• **Strategy:** IoT sensors, refrigeration audits']
    },
    'waste_by_handling_condition.png': {
        'title': '📦 Waste by Handling Condition',
        'explanation': 'Bar chart showing waste volume for each handling condition. **Key insights:** "Damaged" handling has highest waste = physical damage during production/dispatch. "Good" condition waste = quality failures (contamination, expired). "Crushed" and "Leaking" = logistics damage.',
        'key_points': ['• **X-axis:** Handling condition', '• **Y-axis:** Total units wasted', '• **Red bars:** Damaged (highest) - physical handling issues', '• **Orange bars:** Good (quality failures), Crushed, Leaking', '• **Action:** Handling SOPs, packaging improvements, operator training', '• **Impact:** Physical damage = avoidable waste', '• **Strategy:** Conveyor belt audits, packaging redesign', '• **Link to dispatch:** Crushed/Leaking = vehicle loading/route issues']
    },
    'waste_day_of_week.png': {
        'title': '📅 Waste by Day of Week',
        'explanation': 'Bar chart showing total waste across 7 days (Mon-Sun). **Key insights:** Identifies weekly waste patterns. Weekend spikes = reduced supervision or staff issues. Consistent waste = systemic process problems. Low-waste days = best practice learning opportunities.',
        'key_points': ['• **X-axis:** Day of week', '• **Y-axis:** Total units wasted', '• **Red bars:** High-waste days (investigate causes)', '• **Green bars:** Low-waste days (replicate success factors)', '• **Weekend patterns:** Staff availability, supervisor presence', '• **Weekday patterns:** Production volume, shift schedules', '• **Action:** Day-specific root cause analysis', '• **Use case:** Staffing optimization, best practice documentation']
    },
    'waste_by_route_top15.png': {
        'title': '🚚 Top 15 Routes by Waste (Post-Dispatch)',
        'explanation': 'Horizontal bar chart showing routes with highest post-dispatch waste. **Key insights:** Worst routes have 12K+ units wasted = cold chain failures, rough roads, or excessive travel time. Route-specific waste patterns indicate logistical issues, not product quality.',
        'key_points': ['• **X-axis:** Total units wasted', '• **Y-axis:** Route IDs (sorted by waste)', '• **Red bars:** >10K units (critical routes)', '• **Orange bars:** 8K-10K (needs attention)', '• **Action:** Route audits (travel time, refrigeration, road quality)', '• **Impact:** Top routes = $200K+ annual waste loss', '• **Strategy:** Route optimization, vehicle upgrades, driver training', '• **Link to dispatch:** Cross-reference with dispatch delay data']
    },
    'waste_stage_pie.png': {
        'title': '🥧 Waste Stage Distribution (Pie Chart)',
        'explanation': 'Pie chart showing production vs post-dispatch waste proportions. **CRITICAL VISUAL:** 59.3% production (red) vs 40.7% post-dispatch (orange). Reinforces that majority of waste is preventable at production stage through quality control, not logistics improvements.',
        'key_points': ['• **Red slice:** Production waste (59.3%, 772K units)', '• **Orange slice:** Post-dispatch waste (40.7%, 531K units)', '• **Insight:** Production-dominant = focus on quality, not logistics', '• **Action:** Production QC tightening before dispatch optimization', '• **Impact:** Reducing production waste by 10% saves 77K units', '• **Strategy:** Batch testing, equipment maintenance, shift training', '• **Next steps:** Deep dive into production stage waste reasons']
    },
    
    # ==================== RETURNS DATASET VISUALIZATIONS ====================
    'returns_by_reason.png': {
        'title': '🔴 Returns Volume by Reason',
        'explanation': 'Horizontal bar chart showing units returned by reason. **CRITICAL FINDING:** "Mould Growth" leads with 118,620 units (15.0%) = cold chain failure. 58.4% of returns are preventable (Expired, Damaged, Crushed, Mould) = quality/logistics failures. Only 14.1% are demand mismatch (Returned Unsold) = forecasting relatively good.',
        'key_points': ['• **X-axis:** Total units returned', '• **Y-axis:** Return reason codes', '• **Red bars:** Critical preventable reasons (>100K units)', '• **Orange bars:** Significant reasons (50K-100K)', '• **Top reason:** Mould Growth (118,620 units, 15.0%) - cold chain failure', '• **Preventable:** Expired, Damaged, Crushed, Mould = 462K units (58.4%)', '• **Demand mismatch:** Returned Unsold = 111K units (14.1%)', '• **Action:** Cold chain audits, packaging improvements, shelf-life optimization', '• **Impact:** Preventing 50% of returns saves $300K+ annually']
    },
    'returns_by_route_top15.png': {
        'title': '🚛 Top 15 Routes by Returns',
        'explanation': 'Horizontal bar chart showing routes with highest return volumes. **CRITICAL FINDING:** RT_058 is worst with 15,174 units returned (1.92%). Route-specific patterns indicate dispatch/logistics issues (late deliveries, rough handling, temperature control). Target underperforming routes for improvement.',
        'key_points': ['• **X-axis:** Total units returned', '• **Y-axis:** Route IDs (sorted by returns)', '• **Red bars:** >12K units (critical routes)', '• **Orange bars:** 10K-12K (needs attention)', '• **Worst route:** RT_058 (15,174 units, 1.92%)', '• **Action:** Route audits (delivery timing, vehicle condition, driver training)', '• **Impact:** Top 15 routes = 25% of all returns', '• **Strategy:** Route optimization, vehicle maintenance, temperature monitoring', '• **Link to waste:** Returns often lead to waste']
    },
    'returns_by_retailer_top15.png': {
        'title': '🏪 Top 15 Retailers by Returns',
        'explanation': 'Horizontal bar chart showing retailers with highest return volumes. **CRITICAL FINDING:** STORE_086 is worst with 5,936 units returned (0.75%). Retailer-specific patterns indicate storage issues, forecasting problems, or product handling failures. Focus on partnership improvements.',
        'key_points': ['• **X-axis:** Total units returned', '• **Y-axis:** Retailer IDs (sorted by returns)', '• **Red bars:** >5K units (critical retailers)', '• **Orange bars:** 4K-5K (needs attention)', '• **Worst retailer:** STORE_086 (5,936 units, 0.75%)', '• **Action:** Retailer audits (storage conditions, FIFO compliance, forecasting)', '• **Impact:** Top 15 retailers = 10% of all returns', '• **Strategy:** Retailer training, storage guidelines, demand planning support', '• **Link to sales:** Cross-reference with sales volume (high volume = high returns acceptable)']
    },
    'returns_by_sku.png': {
        'title': '🍞 Returns by SKU',
        'explanation': 'Horizontal bar chart showing total returns for each SKU. **Key insights:** 7 SKUs account for >10% of returns each (Soft White, Wholegrain Brown, High Energy White, Whole Wheat, Seed Loaf, High Energy Brown, Family Loaf). Relatively even distribution = systemic issue (cold chain, dispatch timing), not specific recipe defects.',
        'key_points': ['• **X-axis:** Total units returned', '• **Y-axis:** SKU names', '• **Red bars:** >100K units returned (high-return SKUs)', '• **Orange bars:** 80K-100K (medium returns)', '• **Even distribution:** All SKUs ~14% returns = process issue', '• **Action:** SKU-agnostic interventions (cold chain, dispatch speed)', '• **Link to sales:** Cross-reference with best-sellers (high volume = higher returns expected)', '• **Strategy:** Focus on preventing cold chain failures for all products']
    },
    'returns_daily_trend.png': {
        'title': '📈 Daily Returns Trend with Moving Average',
        'explanation': 'Time series showing daily return units from Jan 1 to Jul 30, 2025. Dark orange line = daily returns, blue line = 7-day moving average, light orange fill = volume. **Key insights:** Identifies return spikes (batch failures, retailer issues), seasonal patterns, and trend direction. Moving average reveals if returns are increasing.',
        'key_points': ['• **X-axis:** Date (Jan-Jul 2025)', '• **Y-axis:** Daily units returned', '• **Orange line:** Actual daily returns (volatile)', '• **Blue line:** 7-day moving average (trend)', '• **Spikes:** Batch failures, cold chain events, retailer issues', '• **Dips:** Good dispatch/quality days', '• **Trend:** Increasing trend = deteriorating quality/logistics', '• **Action:** Correlate spikes with batch IDs, routes, retailers', '• **Use case:** Early warning system for quality degradation']
    },
    'returns_day_of_week.png': {
        'title': '📅 Returns by Day of Week',
        'explanation': 'Bar chart showing total returns across 7 days (Mon-Sun). **Key insights:** Identifies weekly return patterns. Monday spikes = weekend storage issues. Friday spikes = end-of-week rushed dispatches. Consistent returns = systemic problems. Low-return days = best practice learning.',
        'key_points': ['• **X-axis:** Day of week', '• **Y-axis:** Total units returned', '• **Red bars:** High-return days (investigate causes)', '• **Green bars:** Low-return days (replicate success)', '• **Monday patterns:** Weekend storage, stale product from Fri dispatch', '• **Friday patterns:** Rushed dispatches, quality shortcuts', '• **Action:** Day-specific root cause analysis', '• **Use case:** Dispatch scheduling optimization']
    },
    'returns_temperature_distribution.png': {
        'title': '🌡️ Temperature at Return',
        'explanation': 'Histogram showing temperature distribution when products were returned. **Key insights:** Most returns occur at 20-30°C (ambient). High temperatures (>35°C) correlate with Mould Growth and Expired reasons = cold chain failures. Low temps (<10°C) = non-temperature related returns (Damaged, Unsold).',
        'key_points': ['• **X-axis:** Temperature (°C)', '• **Y-axis:** Frequency (number of return incidents)', '• **Peak:** 20-30°C (most returns at ambient)', '• **High temp:** >35°C = cold chain failure (mould, expiry)', '• **Low temp:** <10°C = proper refrigeration (non-temp returns)', '• **Action:** Cross-reference high-temp returns with reasons (Mould, Expired)', '• **Impact:** Temperature control critical for shelf-life', '• **Strategy:** Retailer refrigeration audits, IoT monitoring']
    },
    'returns_by_handling_condition.png': {
        'title': '📦 Returns by Handling Condition',
        'explanation': 'Bar chart showing return volume for each handling condition. **Key insights:** "Good" condition returns = demand mismatch (Returned Unsold) or hidden quality issues (Mould inside). "Damaged" returns = physical handling failures. "Crushed" and "Leaking" = logistics damage.',
        'key_points': ['• **X-axis:** Handling condition', '• **Y-axis:** Total units returned', '• **Orange bars:** Good (demand mismatch or hidden quality)', '• **Red bars:** Damaged, Crushed, Leaking (physical handling)', '• **Action:** Physical damage = packaging improvements, handling SOPs', '• **Impact:** Good-condition returns = forecasting or quality (non-visual)', '• **Strategy:** Packaging redesign, retailer training, forecasting improvements', '• **Link to waste:** Damaged returns likely become waste']
    },
    'returns_quantity_distribution.png': {
        'title': '📊 Return Quantity Distribution',
        'explanation': 'Histogram showing distribution of return quantities per incident. **Key insights:** Most returns are small (5-15 units) = individual transaction issues. Large returns (>30 units) = batch-level failures or retailer overstocking. Tail distribution = bulk return events.',
        'key_points': ['• **X-axis:** Units returned per incident', '• **Y-axis:** Frequency (number of return events)', '• **Peak:** 5-15 units (individual transaction returns)', '• **Tail:** >30 units (batch failures, overstocking)', '• **Small returns:** Quality issues at consumer level', '• **Large returns:** Forecasting errors, batch contamination', '• **Action:** Small returns = quality control; Large returns = demand planning', '• **Impact:** Reducing large returns has outsized impact on total volume']
    },
    'returns_reason_pie.png': {
        'title': '🥧 Returns Reason Distribution (Pie Chart)',
        'explanation': 'Pie chart showing proportion of returns by reason category. **CRITICAL VISUAL:** Red/orange slices (Mould, Expired, Damaged, Crushed) = 58.4% preventable returns. Green slice (Returned Unsold) = 14.1% demand mismatch. Emphasizes that majority of returns are quality/logistics failures, not forecasting errors.',
        'key_points': ['• **Red slices:** Mould Growth (15.0%), Expired (11.8%) - cold chain failures', '• **Orange slices:** Damaged (15.9%), Crushed (15.7%) - physical handling', '• **Green slice:** Returned Unsold (14.1%) - demand mismatch', '• **Preventable:** 58.4% (Mould, Expired, Damaged, Crushed)', '• **Demand issues:** 14.1% (Returned Unsold)', '• **Action:** Focus on cold chain and handling before forecasting', '• **Impact:** Preventing 50% of preventable returns saves 230K units', '• **Strategy:** Quality > Forecasting for maximum return reduction']
    },
    
    # ==================== SALES B2B DATASET VISUALIZATIONS ====================
    'sales_b2b_by_depot.png': {
        'title': '🏭 Depot Distribution Performance',
        'explanation': 'Horizontal bar chart showing total units distributed by each depot. **Key insights:** 11 depots with balanced distribution (top 3 = 31.4%). Mutare_Branch and Marondera_Depot lead with ~258K units each (10.6%). All depots serve all 139 stores via 50 routes. Healthy network with no single-point-of-failure.',
        'key_points': ['• **X-axis:** Total units distributed', '• **Y-axis:** Depot ID', '• **Crimson bars:** Top-performing depots (>250K units)', '• **Orange bars:** Mid-tier depots', '• **Gold bars:** Lower-volume depots', '• **Balanced network:** Top 3 depots only 31.4% (not concentrated)', '• **Avg order size:** ~162 units per depot order', '• **Action:** Maintain balanced load, expand secondary depot capacity']
    },
    'sales_b2b_by_store_top20.png': {
        'title': '🏪 Top 20 Stores by B2B Order Volume',
        'explanation': 'Horizontal bar chart showing stores with highest wholesale order volumes. **Key insights:** STORE_087 leads with 23,658 units (142 orders). Top stores order 166-179 units/order on average. Relatively even distribution = healthy customer base. High-volume stores are spread across different primary depots.',
        'key_points': ['• **X-axis:** Total units ordered from depots', '• **Y-axis:** Store ID (top 20)', '• **Green bars:** Above-median stores (high-volume)', '• **Orange bars:** Below-median stores (medium-volume)', '• **Top store:** STORE_087 (23,658 units from Bindura_Depot)', '• **Avg orders per store:** 109 orders over analysis period', '• **Action:** Replicate success factors of top stores', '• **Use case:** Store partnership strategy, credit limits']
    },
    'sales_b2b_route_efficiency_top15.png': {
        'title': '🚚 Top 15 Most Efficient Distribution Routes',
        'explanation': 'Horizontal bar chart showing routes with highest average units per trip. **Key insights:** RT_009 most efficient (172.6 units/trip). Route efficiency varies from 154-173 units/trip. Green bars = above-median efficiency (good route utilization). Red bars = below-median (potential consolidation candidates).',
        'key_points': ['• **X-axis:** Average units per trip', '• **Y-axis:** Route ID (top 15 by efficiency)', '• **Green bars:** Efficient routes (>median units/trip)', '• **Red bars:** Less efficient routes (<median)', '• **Blue line:** Median efficiency threshold', '• **Best route:** RT_009 (172.6 units/trip, serves 128 stores)', '• **Action:** Route consolidation for low-efficiency routes', '• **Impact:** Improving efficiency by 10% saves $50K+ in logistics']
    },
    'sales_b2b_by_sku.png': {
        'title': '🍞 SKU Distribution Volume (B2B Channel)',
        'explanation': 'Horizontal bar chart showing total wholesale units distributed for each SKU. **Key insights:** 25 SKUs distributed through B2B channel. Relatively even distribution across SKUs (~100K units each). Family Loaf and High Energy variants lead. Balanced portfolio = low SKU concentration risk.',
        'key_points': ['• **X-axis:** Total units distributed (wholesale)', '• **Y-axis:** SKU names', '• **Dark green bars:** Top sellers (>100K units)', '• **Orange bars:** Mid-tier SKUs', '• **Gold bars:** Lower-volume SKUs', '• **Red line:** Median volume marker', '• **Even distribution:** All SKUs get depot stocking', '• **Action:** Compare with Sales POS (retail) to validate inventory flow', '• **Use case:** Depot SKU stocking decisions']
    },
    'sales_b2b_daily_trend.png': {
        'title': '📈 Daily B2B Distribution Volume with Moving Average',
        'explanation': 'Time series showing daily wholesale distribution from Jan 1 to Dec 5, 2025. Dark blue line = daily volume, red line = 7-day moving average, light blue fill = volume emphasis. **Key insights:** Avg 11,533 units/day. Peak day: 18,640 units. Spikes indicate bulk ordering days or promotional restocking.',
        'key_points': ['• **X-axis:** Date (Jan-Dec 2025)', '• **Y-axis:** Daily units distributed', '• **Blue line:** Actual daily volume (volatile)', '• **Red line:** 7-day moving average (trend)', '• **Filled area:** Visual volume emphasis', '• **Spikes:** Bulk ordering, promotional restocking, holiday prep', '• **Dips:** Low-demand periods or operational issues', '• **Use case:** Capacity planning, depot staffing', '• **Action:** Correlate spikes with POS sales for inventory optimization']
    },
    'sales_b2b_day_of_week.png': {
        'title': '📅 B2B Distribution Volume by Day of Week',
        'explanation': 'Bar chart comparing wholesale distribution across 7 days. **CRITICAL FINDING:** Monday has highest volume (359,217 units) = stores restocking for the week. Friday lowest (338,752 units) = end-of-week slowdown. Weekday vs weekend pattern shows B2B operational rhythm.',
        'key_points': ['• **X-axis:** Day of week', '• **Y-axis:** Total units distributed', '• **Blue bars:** Weekdays (Mon-Fri)', '• **Coral bars:** Weekend (Sat-Sun)', '• **Annotations:** Volume displayed above bars', '• **Peak day:** Monday (359K units) - weekly restocking', '• **Low day:** Friday (339K units) - end-of-week slowdown', '• **Action:** Staff depots heavily on Monday, optimize Friday routes', '• **Use case:** Depot staffing schedule, driver allocation']
    },
    'sales_b2b_hourly_pattern.png': {
        'title': '⏰ B2B Order Volume by Hour of Day',
        'explanation': 'Bar chart + line plot showing total wholesale orders by hour (0-23). **Key insights:** Peak hour is midnight/00:00 (128,981 units) = automated overnight ordering systems. Slowest hour is 07:00 (92,059 units). Relatively flat distribution suggests 24-hour operations.',
        'key_points': ['• **X-axis:** Hour of day (24-hour format)', '• **Y-axis:** Total units ordered', '• **Teal bars:** Hourly order volume', '• **Red line:** Trend line', '• **Peak hour:** 00:00 midnight (automated systems)', '• **Low hour:** 07:00 (morning shift transition)', '• **Flat pattern:** 24-hour wholesale operations', '• **Use case:** Depot operating hours, order processing windows']
    },
    'sales_b2b_order_size_distribution.png': {
        'title': '📊 B2B Order Size Distribution',
        'explanation': 'Histogram showing distribution of wholesale order quantities. **CRITICAL VALIDATION:** Mean = 161.9 units, Median = 161 units. Normal distribution centered around 160 units. **Compare with Sales POS (~31 units):** B2B orders are 5x larger = validates wholesale vs retail channel distinction.',
        'key_points': ['• **X-axis:** Order size (units)', '• **Y-axis:** Frequency (number of orders)', '• **Red line:** Mean = 161.9 units (wholesale bulk orders)', '• **Green line:** Median = 161 units (consistent ordering)', '• **Distribution:** Normal curve = predictable order sizes', '• **Validation:** 5x larger than retail POS orders (31 units)', '• **Impact:** Bulk ordering = fewer trips, lower logistics cost', '• **Action:** Maintain MOQ policies, encourage larger orders']
    },
    'sales_b2b_depot_sku_heatmap.png': {
        'title': '🗺️ Depot-SKU Distribution Heatmap',
        'explanation': 'Heatmap showing units distributed for each Depot × SKU combination. **Key insights:** Reveals depot-specific SKU preferences and stocking patterns. Darker cells = higher demand. Uniform color = consistent nationwide preferences; clustered hotspots = depot-specific specialization.',
        'key_points': ['• **X-axis:** Depot IDs', '• **Y-axis:** SKU names', '• **Color intensity:** Units distributed (red = high demand)', '• **Annotations:** Exact units per cell', '• **Top combos:** Bindura_Depot + Family Loaf (31,748 units)', '• **Use case:** Depot SKU allocation optimization', '• **Action:** Allocate high-demand SKUs to high-volume depots', '• **Strategy:** Customize depot inventory based on regional demand']
    },
    'sales_b2b_pricing_by_sku.png': {
        'title': '💲 Wholesale Pricing by SKU (Mean ± Std Dev)',
        'explanation': 'Horizontal bar chart showing average wholesale price for each SKU with error bars. **Key insights:** Family Loaf highest ($2.25 wholesale), Buns 6-Pack lowest (~$1.30). Small error bars = consistent pricing. **Compare with Sales POS retail prices** to validate margin structure (retail should be 20-30% higher).',
        'key_points': ['• **X-axis:** Wholesale price per unit ($)', '• **Y-axis:** SKU names', '• **Gold bars:** Average wholesale price', '• **Error bars:** Price variability (std dev)', '• **Highest:** Family Loaf ($2.25) - premium product', '• **Lowest:** Buns 6-Pack ($1.30) - bulk item', '• **Validation:** Compare with POS retail prices ($1.43 wholesale avg)', '• **Action:** Ensure margin structure supports profitability', '• **Use case:** Pricing strategy, margin analysis']
    },
    'sales_b2b_depot_share_pie.png': {
        'title': '🥧 Depot Market Share (by Volume)',
        'explanation': 'Pie chart showing proportion of wholesale distribution by depot. **CRITICAL VISUAL:** Relatively even slices (each ~9-10%) = balanced depot network. No depot dominates >11%. Contrast with concentrated networks where top depot has >30%. Healthy distribution reduces single-point-of-failure risk.',
        'key_points': ['• **Each slice:** Depot contribution to total volume', '• **Percentages:** Distribution share (9-11% per depot)', '• **Top depot:** Mutare_Branch (10.6%)', '• **Balanced:** No depot >11% = healthy network', '• **Strength:** No single-point-of-failure risk', '• **Action:** Maintain balanced load distribution', '• **Impact:** Network resilience for capacity disruptions', '• **Strategy:** Avoid over-reliance on any single depot']
    },
    'sales_b2b_depot_revenue.png': {
        'title': '💰 Depot Performance by Revenue (Wholesale)',
        'explanation': 'Horizontal bar chart showing total wholesale revenue by depot. **Key insights:** Marondera_Depot leads with $373,646 revenue (10.7%). Total wholesale revenue: $3.5M. Revenue distribution mirrors volume distribution = consistent pricing across depots. Green bars = top revenue generators.',
        'key_points': ['• **X-axis:** Total revenue ($)', '• **Y-axis:** Depot ID', '• **Dark green bars:** Top revenue depots (>$360K)', '• **Orange bars:** Mid-tier depots', '• **Gold bars:** Lower revenue depots', '• **Top depot:** Marondera_Depot ($373,646, 10.7%)', '• **Total:** $3.5M wholesale revenue', '• **Validation:** Revenue mirrors volume = consistent pricing', '• **Action:** Focus growth investments on top-performing depots']
    },
    'inventory_balance_hist.png': {
        'title': '📊 Inventory Balance Distribution',
        'explanation': 'Distribution of inventory balance levels after stock movements. **Key insights:** Shows typical on-hand inventory levels. Very low balances = stockout risk, very high = spoilage/obsolescence risk.',
        'key_points': ['• **X-axis:** Balance after movement', '• **Y-axis:** Frequency', '• **Near zero:** Stockout risk', '• **Very high:** Overstocking/spoilage risk']
    },
    'inventory_by_plant_bar.png': {
        'title': '📊 Inventory In/Out by Plant',
        'explanation': 'Comparison of inbound vs. outbound inventory movements across plants. **Key insights:** Green bars (qty in) should generally exceed or match red bars (qty out). Large imbalances indicate inventory buildup or depletion.',
        'key_points': ['• **Green bars:** Quantity incoming', '• **Red bars:** Quantity outgoing', '• **In > Out:** Inventory accumulation', '• **Out > In:** Drawing down stock']
    },
    'inventory_timeseries.png': {
        'title': '📊 Inventory Balance Over Time',
        'explanation': 'Average inventory balance tracked daily. **Key insights:** Shows inventory trends—rising levels may indicate demand slowdown or overproduction, falling levels may signal supply chain issues.',
        'key_points': ['• **X-axis:** Date', '• **Y-axis:** Average balance', '• **Rising:** Inventory buildup (check demand)', '• **Falling:** Potential stockout risk']
    },
    'inventory_movement_types.png': {
        'title': '📊 Inventory Movement Types',
        'explanation': 'Frequency of different movement types (receipts, transfers, adjustments, sales, etc.). **Key insights:** High adjustment counts may indicate inventory accuracy issues. Unusual patterns suggest process problems.',
        'key_points': ['• **X-axis:** Movement type', '• **Y-axis:** Count', '• **High adjustments:** Inventory accuracy issues', '• **Pattern changes:** Process or system issues']
    },
    'waste_qty_hist.png': {
        'title': '📊 Waste Quantity Distribution',
        'explanation': 'Distribution of waste quantities per incident. **Key insights:** Shows typical waste event size and helps identify catastrophic waste events (extreme outliers) vs. routine spoilage.',
        'key_points': ['• **X-axis:** Waste quantity per incident', '• **Y-axis:** Frequency', '• **Small values:** Routine daily waste', '• **Large values:** Major spoilage events requiring investigation']
    },
    'waste_by_reason_bar.png': {
        'title': '📊 Top Waste Reasons',
        'explanation': 'Primary causes of waste ranked by frequency. **Key insights:** Top reasons (expiration, damage, quality defects) drive the majority of waste. Prioritize preventive measures for top 3 causes.',
        'key_points': ['• **Y-axis:** Waste reason/category', '• **X-axis:** Count of waste incidents', '• **Top reasons:** Highest impact on waste reduction', '• **Action:** Implement controls for top causes']
    },
    'waste_timeseries.png': {
        'title': '📊 Waste Over Time',
        'explanation': 'Daily waste quantities tracked over time. **Key insights:** Monitors waste trends, seasonal patterns (e.g., holiday peaks), and effectiveness of waste reduction initiatives.',
        'key_points': ['• **X-axis:** Date', '• **Y-axis:** Total daily waste', '• **Upward trend:** Worsening waste problem', '• **Sudden spikes:** Production/quality incidents']
    },
    'waste_by_location.png': {
        'title': '📊 Waste by Location',
        'explanation': 'Comparison of waste generation across different locations (plants, warehouses, stores). **Key insights:** Identifies problematic locations with high waste rates requiring targeted intervention.',
        'key_points': ['• **X-axis:** Location identifier', '• **Y-axis:** Waste quantity', '• **Highest bars:** Locations with worst waste performance', '• **Benchmark:** Compare against average line']
    },
    'returns_qty_hist.png': {
        'title': '📊 Return Quantity Distribution',
        'explanation': 'Shows the distribution of return quantities across all transactions. **Key insights:** Look for the typical return size (peak of histogram) and identify outliers (long tail). High return quantities may indicate systemic quality issues or delivery problems.',
        'key_points': ['• **X-axis:** Quantity returned per transaction', '• **Y-axis:** Frequency (number of occurrences)', '• **Peak:** Most common return quantity', '• **Right tail:** Large/unusual returns requiring investigation']
    },
    'returns_by_reason_bar.png': {
        'title': '📊 Top Return Reasons',
        'explanation': 'Horizontal bar chart ranking the most common reasons for product returns. **Key insights:** The top 3-5 reasons account for the majority of returns. Focus quality improvement efforts on addressing these primary causes.',
        'key_points': ['• **Y-axis:** Return reason/category', '• **X-axis:** Count of return incidents', '• **Longest bars:** Highest priority issues', '• **Action:** Target top 3 reasons for root cause analysis']
    },
    'returns_timeseries.png': {
        'title': '📊 Returns Over Time (Daily)',
        'explanation': 'Daily trend of total return quantities. **Key insights:** Identifies seasonal patterns, spikes indicating quality incidents, and overall trend direction (improving or worsening).',
        'key_points': ['• **X-axis:** Date', '• **Y-axis:** Total quantity returned', '• **Peaks:** Investigate spikes for batch/quality issues', '• **Trends:** Upward = worsening, downward = improving']
    },
    'returns_by_dayofweek.png': {
        'title': '📊 Returns by Day of Week',
        'explanation': 'Total returns aggregated by day of week. **Key insights:** Reveals if returns are higher on specific days (e.g., Mondays after weekend deliveries). Helps optimize inspection and processing schedules.',
        'key_points': ['• **X-axis:** Day of week (Monday-Sunday)', '• **Y-axis:** Total quantity returned', '• **Pattern:** Identifies operational day-of-week effects', '• **Use:** Schedule staffing for high-return days']
    },
    'sensors_value_hist.png': {
        'title': '📊 Sensor Metric Values Distribution',
        'explanation': 'Distribution of all sensor readings across equipment and metrics. **Key insights:** Multi-modal distribution may indicate different equipment types or metrics mixed together. Extreme outliers warrant investigation.',
        'key_points': ['• **X-axis:** Metric value', '• **Y-axis:** Frequency', '• **Outliers:** Equipment malfunctions or calibration issues', '• **Multiple peaks:** Different metric types']
    },
    'sensors_by_metric_box.png': {
        'title': '📊 Sensor Metrics by Name (Top 10)',
        'explanation': 'Box plots showing value ranges for top 10 sensor metrics. **Key insights:** Box shows quartiles (25th, 50th, 75th percentile). Whiskers show normal range. Dots are outliers requiring investigation.',
        'key_points': ['• **Box:** Middle 50% of values (IQR)', '• **Line in box:** Median value', '• **Whiskers:** Normal range (within 1.5×IQR)', '• **Dots:** Outliers (potential issues)']
    },
    'sensors_timeseries.png': {
        'title': '📊 Sensor Readings Over Time',
        'explanation': 'Hourly average of sensor values tracked over time. **Key insights:** Shows equipment/environmental trends. Sudden changes indicate equipment issues, seasonal patterns show environmental factors.',
        'key_points': ['• **X-axis:** Timestamp (hourly)', '• **Y-axis:** Average metric value', '• **Spikes:** Equipment malfunctions', '• **Gradual changes:** Seasonal/environmental patterns']
    },
    'sensors_by_equipment_bar.png': {
        'title': '📊 Top Equipment by Sensor Readings',
        'explanation': 'Top 15 equipment units ranked by number of sensor readings. **Key insights:** High reading counts suggest heavily monitored critical equipment. Unusually low counts may indicate sensor failures.',
        'key_points': ['• **X-axis:** Equipment identifier', '• **Y-axis:** Number of readings', '• **Tall bars:** Critical/heavily monitored equipment', '• **Short bars:** Check sensor connectivity']
    },
    
    # INVENTORY VISUALIZATIONS (12 figures)
    'inventory_movement_types.png': {
        'title': '📦 Inventory Movement Type Distribution',
        'explanation': 'Bar chart showing frequency of each movement type (PRODUCTION, DISPATCH, STORE_SALE, RETURN_FROM_STORE, WASTE, STOCK_ADJUSTMENT). **Key insights:** Balanced distribution (~3,000 records each) = comprehensive ledger coverage. Unusual spikes in adjustments indicate inventory accuracy issues.',
        'key_points': ['• **X-axis:** Movement type', '• **Y-axis:** Number of records', '• **Even distribution:** Healthy ledger system', '• **High adjustments:** Investigate inventory accuracy', '• **Total:** 18,073 movements tracked', '• **Action:** Monitor adjustment frequency monthly']
    },
    'inventory_balance_distribution.png': {
        'title': '📊 Inventory Balance After Movement (Filtered)',
        'explanation': 'Histogram showing distribution of inventory balance levels (outliers removed for visibility). **Key insights:** Balance range indicates typical stock levels. Peak shows most common inventory position. **🚨 WARNING:** 29.2% negative balances (5,286 records) hidden by filter - severe data integrity crisis.',
        'key_points': ['• **X-axis:** Balance after movement (units)', '• **Y-axis:** Frequency', '• **Peak:** Most common inventory level', '• **Right tail:** Overstock positions', '• **CRITICAL:** 5,286 negative balances not shown (filtered)', '• **Action:** See negative_balances chart for crisis details']
    },
    'inventory_negative_balances.png': {
        'title': '🚨 CRITICAL: Negative Balance Crisis by Location',
        'explanation': 'Bar chart showing 5,286 negative balance anomalies (29.2% of all records). **SEVERE DATA INTEGRITY FAILURE:** Stores have 4,197 negatives (79%), Plants have 1,089 (21%). Negative inventory is physically impossible = missing inbound records, double-counted sales, or unlogged waste. **URGENT ACTION REQUIRED.**',
        'key_points': ['• **Red bars:** Negative balance counts (CRITICAL)', '• **Stores:** 4,197 negatives (79% of problem)', '• **Plants:** 1,089 negatives (21%)', '• **Impact:** Cannot trust inventory for planning', '• **Root cause:** Missing dispatch/sales records', '• **Action:** Halt decisions, emergency reconciliation with Dispatch/Sales datasets', '• **Timeline:** Fix within 48 hours or risk operational chaos']
    },
    'inventory_qty_flow.png': {
        'title': '↔️ Quantity In vs Out by Movement Type',
        'explanation': 'Grouped bar chart comparing qty_in (green) vs qty_out (red) for each movement type. **Key insights:** Production is pure inflow (3.87M in), Dispatch is pure outflow (2.67M out), Adjustments net positive (+25K). Flow imbalances reveal ledger logic - PRODUCTION adds stock, DISPATCH/SALE removes stock.',
        'key_points': ['• **Green bars:** Quantity incoming', '• **Red bars:** Quantity outgoing', '• **Production:** 3.87M in (stock creation)', '• **Dispatch:** 2.67M out (plant → stores)', '• **Store Sales:** 527K out (stores → customers)', '• **Returns:** 241K in (stores → plants)', '• **Waste:** 304K out (stock destruction)', '• **Use case:** Validate ledger logic integrity']
    },
    'inventory_sku_balances.png': {
        'title': '🍞 Current Inventory by SKU (Top 15)',
        'explanation': 'Horizontal bar chart showing ending inventory balance for top 15 SKUs. **Key insights:** High Energy Brown dominates (65K units), High Energy White is lowest (148 units). SKU distribution reveals demand patterns and stocking strategy. **Caveat:** With 29.2% negative balances, these numbers are unreliable.',
        'key_points': ['• **X-axis:** Current balance (units)', '• **Y-axis:** SKU names', '• **Top SKU:** High Energy Brown (65,009 units)', '• **Bottom SKU:** High Energy White (148 units)', '• **7 SKUs tracked:** Comprehensive portfolio', '• **WARNING:** 29.2% negative balances = unreliable figures', '• **Action:** Reconcile before using for production planning']
    },
    'inventory_daily_trend.png': {
        'title': '📈 Daily Inventory Balance Trend (with 7-Day MA)',
        'explanation': 'Time series showing daily average inventory balance from Jan to Nov 2025. Blue line = daily balance, orange line = 7-day moving average. **Key insights:** Identifies inventory buildup or depletion trends. Moving average smooths volatility to reveal underlying direction. **Caveat:** With 29.2% negatives, trend direction may be misleading.',
        'key_points': ['• **X-axis:** Date (Jan-Nov 2025)', '• **Y-axis:** Average balance', '• **Blue line:** Daily balance (volatile)', '• **Orange line:** 7-day MA (trend)', '• **Rising trend:** Inventory accumulation (demand slowdown?)', '• **Falling trend:** Stock depletion (supply issues?)', '• **WARNING:** Negative balances distort true trend', '• **Action:** Fix data integrity before trend analysis']
    },
    'inventory_expiry_risk_pie.png': {
        'title': '⏳ Inventory by Expiry Risk Category',
        'explanation': 'Pie chart showing distribution of inventory across expiry risk levels. **Key insights:** 85.4% in Warning zone (3-5 days to expiry), only 0.2% expired. Majority of inventory is fresh with 4+ days shelf life. **SURPRISING:** Low expiry rate (0.2%) may be understated due to 29.2% negative balances masking true waste.',
        'key_points': ['• **Green (Safe):** 14.4% (>5 days)', '• **Yellow (Warning):** 85.4% (3-5 days)', '• **Orange (Critical):** 0.0% (0-2 days)', '• **Red (Expired):** 0.2% (negative days)', '• **Mean expiry:** 4.4 days ahead', '• **Good:** Most stock is fresh', '• **Caveat:** 29.2% negatives may hide true expiry waste', '• **Action:** Cross-check with Waste dataset (expired reason)']
    },
    'inventory_days_to_expiry.png': {
        'title': '📅 Days to Expiry Distribution (-10 to +30 Days)',
        'explanation': 'Histogram showing shelf-life distribution with focus on -10 to +30 day window. **Key insights:** Peak at 4 days = typical freshness at movement time. Negative days = already expired stock (31 movements, 0.2%). Long tail to +30 days = freshly produced inventory.',
        'key_points': ['• **X-axis:** Days until expiry (negative = expired)', '• **Y-axis:** Frequency', '• **Peak:** 4 days (typical freshness)', '• **Negative:** 31 expired movements (0.2%)', '• **Positive tail:** Fresh inventory (5-30 days)', '• **Outliers:** >30 days (unusual shelf-life)', '• **Action:** Monitor movements with <2 days shelf life', '• **Use case:** FIFO policy enforcement, expiry alerts']
    },
    'inventory_plant_vs_store.png': {
        'title': '🏭 Plant vs Store Flow Comparison',
        'explanation': 'Grouped bar chart comparing qty_in (green) and qty_out (red) at Plants vs Stores. **CRITICAL ANOMALY EXPOSED:** Plants out = 3.01M units (dispatch), Stores in = 259K units (received). **Flow efficiency: 8.6%** (should be ~100%). 2.75M units "missing" in transit = severe data integrity crisis linking Dispatch → Inventory.',
        'key_points': ['• **Green bars:** Quantity incoming', '• **Red bars:** Quantity outgoing', '• **Plants Out:** 3.01M units (dispatch)', '• **Stores In:** 259K units (received)', '• **Gap:** 2.75M units unaccounted (91.4% missing)', '• **🚨 CRISIS:** Flow efficiency = 8.6% (should be 100%)', '• **Root cause:** Missing store receipts OR double-counted dispatch', '• **Action:** Emergency reconciliation Dispatch ↔ Inventory', '• **Impact:** Cannot track depot→store flow accurately']
    },
    'inventory_adjustments.png': {
        'title': '🔧 Stock Adjustment Distribution (Shrinkage Analysis)',
        'explanation': 'Histogram showing size distribution of stock adjustments. **Key insights:** Most adjustments are small (<50 units). Shrinkage rate = 0.99% (42,152 units adjusted out / 4.28M inbound). **GOOD:** Below 1% industry benchmark. Large adjustments (>100 units) = only 6 incidents (0.2%) = shrinkage is not being abused for corrections.',
        'key_points': ['• **X-axis:** Adjustment quantity (negative = shrinkage)', '• **Y-axis:** Frequency', '• **Peak:** Small adjustments (normal variance)', '• **Shrinkage rate:** 0.99% (below 1% target)', '• **Large adjustments:** 6 records >100 units (investigate)', '• **Good:** Adjustment mechanism not abused', '• **Action:** Audit 6 large adjustments for legitimacy', '• **Use case:** Theft detection, process improvement']
    },
    'inventory_turnover_ratio.png': {
        'title': '🔄 Inventory Turnover Ratio by SKU (Top 15)',
        'explanation': 'Horizontal bar chart showing turnover ratio (qty_out / qty_in) for each SKU. **Key insights:** Ratio of 1.0 = perfect balance (in = out). <1.0 = inventory buildup, >1.0 = drawing down stock. All SKUs cluster around 0.78-0.91 = healthy movement with slight accumulation. Seed Loaf highest turnover (0.91).',
        'key_points': ['• **X-axis:** Turnover ratio (Out / In)', '• **Y-axis:** SKU names', '• **1.0 = Perfect:** In equals Out', '• **<1.0:** Inventory accumulating (0.78-0.91 range)', '• **>1.0:** Drawing down stock', '• **Highest:** Seed Loaf (0.91) - fast mover', '• **Lowest:** High Energy Brown (0.78) - slower mover', '• **Overall:** Healthy turnover (0.83 avg)', '• **Action:** No slow-moving SKUs detected']
    },
    'inventory_net_movement_dow.png': {
        'title': '📅 Net Inventory Movement by Day of Week',
        'explanation': 'Bar chart showing net movement (qty_in - qty_out) for each day of week. **Key insights:** Wednesday has highest net inflow (+116K), Monday highest net outflow (-11K). Weekly patterns show production/dispatch rhythm. Positive days = stock buildup, negative days = stock depletion.',
        'key_points': ['• **X-axis:** Day of week', '• **Y-axis:** Net movement (In - Out)', '• **Green bars:** Net inflow (stock increases)', '• **Red bars:** Net outflow (stock decreases)', '• **Wednesday peak:** +116K net (mid-week production surge)', '• **Monday dip:** -11K net (weekly dispatch restocking)', '• **Pattern:** Matches B2B Monday ordering peak', '• **Use case:** Weekly production scheduling, dispatch planning']
    },
    
    # ROUTE METADATA VISUALIZATIONS (12 figures)
    'routes_distance_distribution.png': {
        'title': '📏 Route Distance Distribution',
        'explanation': 'Histogram showing spread of route distances. **Key insights:** Mean = 57.6 km, Median = 59.0 km. High std dev (29.9 km) = wide variance from short urban routes (10.4 km) to long rural routes (109.2 km). Distribution shows logistics network diversity - no single route type dominates.',
        'key_points': ['• **X-axis:** Distance (km)', '• **Y-axis:** Frequency', '• **Red line:** Mean = 57.6 km', '• **Orange line:** Median = 59.0 km', '• **Range:** 10.4 - 109.2 km', '• **Std dev:** 29.9 km (high variance)', '• **Use case:** Route planning, fuel budgeting']
    },
    'routes_type_distribution.png': {
        'title': '🛣️ Route Type Distribution (Urban/Suburban/Rural)',
        'explanation': 'Bar chart showing route count by distance category. **Key insights:** 47.7% Rural (>60km, 103 routes) = highest proportion. 27.8% Suburban (30-60km), 24.5% Urban (<30km). Rural dominance = freshness risk priority (long distances degrade quality). Urban routes have traffic risk.',
        'key_points': ['• **Rural (Red):** 103 routes (47.7%), >60km, freshness risk', '• **Suburban (Orange):** 60 routes (27.8%), 30-60km, balanced', '• **Urban (Green):** 53 routes (24.5%), <30km, traffic risk', '• **Insight:** Rural dominance = focus on freshness preservation', '• **Action:** Refrigerated trucks for rural routes', '• **Use case:** Vehicle allocation, departure time optimization']
    },
    'routes_stops_distribution.png': {
        'title': '🏪 Stops per Route Distribution',
        'explanation': 'Histogram showing number of stores served per route. **Key insights:** Mean = 13 stops, Median = 14 stops. Range = 5-20 stops. More stops = higher complexity (delay accumulation, driver fatigue). Fewer stops = efficient but lower coverage. Distribution shows balanced complexity across network.',
        'key_points': ['• **X-axis:** Number of stops', '• **Y-axis:** Frequency', '• **Red line:** Mean = 13.0 stops', '• **Range:** 5-20 stops', '• **High stops (>17):** Complexity risk (delays)', '• **Low stops (<8):** Efficient delivery', '• **Use case:** Route optimization, stop sequencing']
    },
    'routes_distance_vs_stops.png': {
        'title': '🗺️ Distance vs Stops by Route Type (Scatter)',
        'explanation': 'Scatter plot showing relationship between route distance and number of stops, color-coded by route type. **Key insights:** Urban routes (green) cluster at short distance + many stops (high density). Rural routes (blue) spread across long distance + fewer stops (low density). Reveals route complexity patterns.',
        'key_points': ['• **X-axis:** Distance (km)', '• **Y-axis:** Number of stops', '• **Green:** Urban routes (short, dense)', '• **Orange:** Suburban routes (medium)', '• **Blue:** Rural routes (long, sparse)', '• **Pattern:** Distance ≠ stops (urban has more stops/km)', '• **Use case:** Route redesign, stop consolidation opportunities']
    },
    'routes_by_region.png': {
        'title': '🌍 Route Configurations by Region',
        'explanation': 'Horizontal bar chart showing number of route configurations per region. **Key insights:** Bindura leads with 29 configs (13.4%). Coverage across 9 regions = comprehensive national network. Balanced distribution (9-13% per region) = no single region overloaded. Healthy logistics footprint.',
        'key_points': ['• **X-axis:** Number of route configurations', '• **Y-axis:** Region names', '• **Top region:** Bindura (29 configs, 13.4%)', '• **Coverage:** 9 regions nationwide', '• **Balance:** No region >13.4% = no bottlenecks', '• **Action:** Maintain balanced regional distribution', '• **Use case:** Regional capacity planning, depot allocation']
    },
    'routes_capacity_distribution.png': {
        'title': '🚚 Vehicle Capacity Distribution',
        'explanation': 'Bar chart showing distribution of truck sizes (load capacity). **Key insights:** Four capacity tiers: 3,000kg (27%), 4,500kg (26%), 5,000kg (22%), 7,000kg (26%). Balanced fleet composition = flexibility for different route demands. No single vehicle type dominates.',
        'key_points': ['• **X-axis:** Load capacity (kg)', '• **Y-axis:** Number of configurations', '• **3,000 kg:** 58 routes (26.9%) - small trucks', '• **4,500 kg:** 55 routes (25.5%) - medium', '• **5,000 kg:** 48 routes (22.2%) - medium-large', '• **7,000 kg:** 55 routes (25.5%) - large trucks', '• **Balance:** Diverse fleet = operational flexibility', '• **Use case:** Vehicle acquisition planning, route-vehicle matching']
    },
    'routes_capacity_strain.png': {
        'title': '⚖️ Capacity Strain vs Stops (Overload Analysis)',
        'explanation': 'Scatter plot showing capacity strain (load/capacity) vs number of stops. **Key insights:** 100% routes <50% strain = massive underutilization (assuming 50kg/stop). 🟢 Green = OK, 🟠 Orange = high strain, 🔴 Red = overloaded (>100%). **Zero overloaded routes** = good safety, but poor efficiency. Consolidation opportunity.',
        'key_points': ['• **X-axis:** Number of stops', '• **Y-axis:** Capacity strain (load/capacity)', '• **Red line:** 100% capacity (overload threshold)', '• **Orange line:** 50% capacity', '• **🟢 All green:** No overloading (good safety)', '• **Problem:** 100% routes <50% = underutilized', '• **Opportunity:** Consolidate routes, downsize vehicles', '• **Impact:** Reduce fuel costs, improve efficiency']
    },
    'routes_efficiency_by_type.png': {
        'title': '⚡ Route Efficiency by Type (Box Plot)',
        'explanation': 'Box plot showing speed (km/min) distribution for each route type. **Key insights:** Median efficiency ~0.44 km/min (26 km/h). Includes stop time, so lower than pure driving speed. Urban and rural routes have similar efficiency (traffic vs distance balance out). Suburban slightly faster.',
        'key_points': ['• **X-axis:** Route type', '• **Y-axis:** Efficiency (km/min)', '• **Box:** Interquartile range (middle 50%)', '• **Line:** Median efficiency', '• **Speed:** ~0.44 km/min = 26 km/h (with stops)', '• **Insight:** Route type doesn\'t strongly affect efficiency', '• **Use case:** Realistic travel time estimation, delay detection']
    },
    'routes_start_window.png': {
        'title': '🕐 Trip Departure Time Windows',
        'explanation': 'Bar chart showing distribution of route start times. **Key insights:** 38.4% depart 04:00-06:00 (early morning), 31.9% depart 03:00-05:00 (overnight), 29.6% depart 05:00-07:00 (morning). Early departure strategy = avoid traffic, maximize freshness window. All routes return same day.',
        'key_points': ['• **X-axis:** Start time window', '• **Y-axis:** Number of routes', '• **04:00-06:00:** 83 routes (38.4%) - most popular', '• **03:00-05:00:** 69 routes (31.9%) - overnight start', '• **05:00-07:00:** 64 routes (29.6%) - morning', '• **Strategy:** Early departure = traffic avoidance + freshness', '• **Action:** Maintain early start discipline for quality']
    },
    'routes_risk_distribution.png': {
        'title': '⚠️ Route Risk Score Distribution',
        'explanation': 'Histogram showing distribution of composite risk scores (0-1 scale). **Key insights:** Mean risk = 0.43. Risk formula: 30% distance, 30% stops, 40% capacity strain. 4 routes >0.7 (high risk) need priority monitoring. 45 routes <0.3 (low risk) are operationally stable. Orange line marks high-risk threshold.',
        'key_points': ['• **X-axis:** Risk score (0-1)', '• **Y-axis:** Frequency', '• **Red line:** Mean = 0.43', '• **Orange line:** High risk threshold (0.7)', '• **High risk (>0.7):** 4 routes - priority monitoring', '• **Low risk (<0.3):** 45 routes - stable', '• **Use case:** Preventive monitoring, driver training allocation']
    },
    'routes_top_risk.png': {
        'title': '🔴 Top 15 Highest Risk Routes',
        'explanation': 'Horizontal bar chart ranking the 15 riskiest routes by risk score. **Critical routes:** RT_008 Bulawayo - Nkulumane Loop (0.74), RT_052 Chitungwiza - Unit L Loop (0.73). These routes have long distances + many stops + high capacity strain = triple risk. Require enhanced monitoring, experienced drivers, route redesign consideration.',
        'key_points': ['• **X-axis:** Risk score', '• **Y-axis:** Route ID + name', '• **Red bars:** Risk >0.7 (critical)', '• **Orange bars:** Risk 0.6-0.7 (high)', '• **Top risk:** RT_008 Bulawayo (0.74)', '• **Action:** Assign best drivers, add monitoring', '• **Long-term:** Consider route splitting or hub strategy']
    },
    'routes_complexity_vs_risk.png': {
        'title': '🧩 Route Complexity vs Risk (2D Analysis)',
        'explanation': 'Scatter plot showing relationship between complexity score (distance × stops / time) and risk score. **Key insights:** Positive correlation = complex routes are risky. Top 3 riskiest routes annotated (RT_008, RT_052, RT_014). Upper-right quadrant = high complexity + high risk = priority intervention zone.',
        'key_points': ['• **X-axis:** Complexity score', '• **Y-axis:** Risk score', '• **Purple dots:** Individual routes', '• **Annotations:** Highest risk routes labeled', '• **Pattern:** Complexity → Risk (correlation)', '• **Upper right:** High complexity + high risk = intervention zone', '• **Action:** Simplify complex routes (reduce stops, split distance)', '• **Use case:** Route optimization prioritization']
    }
}

@st.cache_data(show_spinner=False)
def load_dataset(file_path: Path):
    if not file_path.exists():
        return None
    return pd.read_parquet(file_path)


def show_dataset_eda(dataset_name: str, config: dict):
    st.header(f"📊 {dataset_name} - Exploratory Data Analysis")
    st.markdown(config['description'])
    st.markdown('---')
    
    # Load data
    data_path = DATA_DIR / config['file']
    df = load_dataset(data_path)
    
    if df is None:
        st.error(f"Dataset not found: {data_path}")
        st.info("Run the cleaning pipeline first: `python src/data/prepare_data.py`")
        return
    
    # Dataset overview
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{len(df):,}")
    col2.metric("Columns", df.shape[1])
    col3.metric("Memory", f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    
    # Date range - handle timestamp parsing carefully
    date_range = "N/A"
    if 'timestamp' in df.columns:
        try:
            ts_col = pd.to_datetime(df['timestamp'], errors='coerce')
            valid_ts = ts_col.dropna()
            if len(valid_ts) > 0:
                date_range = f"{valid_ts.min().date()} to {valid_ts.max().date()}"
        except:
            pass
    col4.metric("Date Range", date_range)
    
    # Sample data - convert timestamp columns to string to avoid Arrow serialization issues
    df_sample = df.head(100).copy()
    for col in df_sample.columns:
        if pd.api.types.is_datetime64_any_dtype(df_sample[col]):
            df_sample[col] = df_sample[col].astype(str)
    
    st.subheader("📋 Sample Data (first 100 rows)")
    st.dataframe(df_sample, use_container_width=True)
    
    # Download raw data
    csv_bytes = df.head(1000).to_csv(index=False).encode('utf-8')
    st.download_button(f'Download {dataset_name} sample (1000 rows, CSV)', csv_bytes, 
                      file_name=f'{dataset_name.lower()}_sample.csv', mime='text/csv')
    
    st.markdown('---')
    
    # Summary statistics
    st.subheader("📈 Summary Statistics")
    summary_path = REPORTS_DIR / config['summary_file']
    if summary_path.exists():
        summary_text = summary_path.read_text(encoding='utf-8')
        st.text(summary_text)
    else:
        st.info(f"Summary not found. Run: `python src/analysis/eda_{dataset_name.lower()}.py`")
        st.dataframe(df.describe(include='all'))
    
    st.markdown('---')
    
    # Grouped summaries
    st.subheader("📊 Grouped Summaries")
    available_summaries = []
    for summ_file in config.get('summaries', []):
        summ_path = SUMMARIES_DIR / summ_file
        if summ_path.exists():
            available_summaries.append((summ_file, summ_path))
    
    if available_summaries:
        tabs = st.tabs([s[0].replace('.csv', '').replace('_', ' ').title() for s in available_summaries])
        for i, (summ_file, summ_path) in enumerate(available_summaries):
            with tabs[i]:
                summ_df = pd.read_csv(summ_path)
                st.dataframe(summ_df, use_container_width=True)
                csv = summ_df.to_csv(index=False).encode('utf-8')
                st.download_button(f'Download {summ_file}', csv, file_name=summ_file, mime='text/csv')
    else:
        st.info("No summary files found. Run the EDA script to generate them.")
    
    st.markdown('---')
    
    # Visualizations with explanations
    st.subheader("📉 Key Visualizations")
    available_figs = []
    for fig_file in config.get('figures', []):
        fig_path = FIGURES_DIR / fig_file
        if fig_path.exists():
            available_figs.append((fig_file, fig_path))
    
    if available_figs:
        for fig_file, fig_path in available_figs:
            # Get explanation for this visualization
            viz_info = VIZ_EXPLANATIONS.get(fig_file, {})
            
            # Display title
            if viz_info.get('title'):
                st.markdown(f"### {viz_info['title']}")
            else:
                st.markdown(f"### {fig_file.replace('.png', '').replace('_', ' ').title()}")
            
            # Display explanation
            if viz_info.get('explanation'):
                st.info(viz_info['explanation'])
            
            # Display image
            st.image(str(fig_path), use_container_width=True)
            
            # Display key points
            if viz_info.get('key_points'):
                with st.expander("🔑 Key Interpretation Guide"):
                    for point in viz_info['key_points']:
                        st.markdown(point)
            
            st.markdown('---')
    else:
        st.info("No figures found. Run the EDA script to generate visualizations.")


def main():
    st.sidebar.title("🔍 EDA Explorer")
    st.sidebar.markdown("Select a dataset to explore")
    
    dataset = st.sidebar.selectbox("Dataset", list(DATASETS.keys()))
    
    if dataset:
        config = DATASETS[dataset]
        show_dataset_eda(dataset, config)
    
    st.sidebar.markdown('---')
    st.sidebar.caption('💡 Tip: Run EDA scripts first to generate reports:\n`python src/analysis/eda_<dataset>.py`')


if __name__ == '__main__':
    main()
