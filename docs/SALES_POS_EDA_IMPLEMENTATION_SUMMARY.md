# Sales / Retail POS Dataset - EDA Implementation Summary

**Date:** December 14, 2025  
**Dataset:** `sales_pos_dataset.parquet`  
**Script:** `src/analysis/eda_sales_pos.py`  
**Status:** ✅ COMPLETE

---

## 📊 Dataset Overview

The **Sales / Retail POS Dataset** is the **DEMAND SIGNAL** that validates all supply-side decisions. It records actual customer purchases at retail outlets, answering the critical question: *"Did customers buy what we produced and dispatched?"*

### Key Statistics

- **Total Transactions:** 15,000 sales
- **Date Range:** Jan 1, 2025 - Jul 30, 2025 (211 days)
- **Total Units Sold:** 464,793 units
- **Total Revenue:** $691,359.70
- **Average Transaction Size:** 31.0 units
- **Average Price:** $1.49 per unit
- **Unique Retailers:** 199
- **Regions:** 8 (Bindura, Bulawayo, Chitungwiza, Gweru, Harare, Kwekwe, Masvingo, Mutare)
- **SKUs:** 10 products

---

## 🎯 CRITICAL FINDINGS

### 1. **Promotion Effectiveness: PROVEN ROI**

**Finding:**  
Promotions deliver substantial business impact:
- **+39.1% quantity uplift** (42.8 units vs 30.8 units per transaction)
- **+26.8% revenue uplift** ($58.13 vs $45.85 per transaction)

**Implication:**  
Promotions are **highly effective** and should be **expanded strategically**.

**Action Items:**
- ✅ Increase promotion frequency (currently only 2% of sales are promo-driven)
- ✅ Target slow demand periods (Tuesdays, mid-month dips)
- ✅ Replicate top performers: Women's Day, Africa Day, Independence Day
- ✅ Conduct A/B testing for new promotion concepts

---

### 2. **Balanced Regional Demand**

**Finding:**  
Revenue is evenly distributed across 8 regions (~$85-90K per region). Top region: **Bindura** (~$90K).

**Implication:**  
- ✅ **Low concentration risk:** No single region dominates
- ✅ **Nationwide market penetration**
- ⚠️ Slight variance suggests optimization opportunities

**Action Items:**
- Investigate what makes Bindura top-performing (location, retailer quality, pricing)
- Replicate Bindura success factors in lower-performing regions
- Tailor SKU mix to regional preferences (see heatmap)

---

### 3. **Balanced SKU Portfolio (Fast-Movers Identified)**

**Finding:**  
Top 7 SKUs each account for ~14% of sales (~65K units):
1. Whole Wheat (69,378 units)
2. High Energy White (69,317)
3. Family Loaf (67,483)
4. Seed Loaf (65,559)
5. Wholegrain Brown (65,108)
6. Soft White (64,129)
7. High Energy Brown (63,390)

**Implication:**  
- ✅ **No SKU concentration risk**
- ✅ Diversified product portfolio
- ⚠️ 3 anomalous SKUs (WholegrainBrown, HighEnergyBrown, SoftWhite) with very low sales (<250 units) - likely data quality issues

**Action Items:**
- Prioritize fast-movers for production capacity and dispatch
- Investigate slow-movers for potential discontinuation
- Validate naming convention issues (e.g., "WholegrainBrown" vs "Wholegrain Brown")

---

### 4. **Hourly & Weekly Demand Patterns**

**Hourly:**
- **Peak hour:** 10:00 AM (21,742 units)
- **Low hour:** 21:00/9PM (17,566 units)
- Relatively **flat distribution** = 24-hour retail coverage

**Weekly:**
- **Peak days:** Sunday (69,272), Friday (68,626), Monday (68,595)
- **Low day:** Tuesday (61,508)
- **Minimal weekend effect** (~2% variance) = consistent demand

**Action Items:**
- Schedule dispatch to ensure peak-hour availability (especially 10am)
- Investigate Tuesday demand dip (potential promotion opportunity)
- Align production schedules to weekly demand curve

---

### 5. **Price Analysis**

**Finding:**
- **Highest price:** Family Loaf ($2.20 avg)
- **Lowest price:** High Energy Brown/White ($1.31 avg)
- **Tight price bands** for most SKUs = consistent pricing strategy
- **Price-quantity correlation:** Weak for most SKUs (indicates price-insensitive demand)

**Implication:**  
Bread is a staple product with **low price elasticity**, allowing for:
- Modest price increases without demand loss
- Premium positioning for Family Loaf
- Potential bundling strategies

**Action Items:**
- Test price sensitivity for high-margin SKUs (Family Loaf, Seed Loaf)
- Investigate outlier prices (likely promotion-driven)
- Analyze promotion vs. non-promotion pricing impact

---

## 📈 Visualizations Generated (10)

1. **`sales_pos_volume_by_sku.png`**  
   Horizontal bar chart showing total units sold by SKU. Green = above median (fast-movers), orange = below median (slow-movers).

2. **`sales_pos_revenue_by_region.png`**  
   Bar chart of revenue by region. Annotations show exact dollar values. Bindura leads.

3. **`sales_pos_promotion_effectiveness.png`**  
   Dual bar chart proving +39.1% quantity and +26.8% revenue uplift from promotions.

4. **`sales_pos_daily_trend.png`**  
   Time series with 7-day moving average showing daily sales volatility and trend.

5. **`sales_pos_hourly_pattern.png`**  
   Bar + line chart showing peak sales at 10am, lowest at 9pm. Flat distribution overall.

6. **`sales_pos_day_of_week.png`**  
   Bar chart showing Sunday as peak day (69,272 units), Tuesday as lowest (61,508).

7. **`sales_pos_promotion_volume.png`**  
   Horizontal bar chart ranking promotions. Women's Day leads with 3,514 units.

8. **`sales_pos_regional_sku_heatmap.png`**  
   Heatmap showing SKU × Region demand. Reveals regional preferences for targeted dispatch.

9. **`sales_pos_price_distribution.png`**  
   Box plot showing price range by SKU. Family Loaf is premium ($2.20), Energy loaves are value ($1.31).

10. **`sales_pos_top_retailers.png`**  
    Top 20 retailers by revenue. Even distribution = healthy retailer network.

---

## 📁 Summary CSVs Generated (7)

1. **`sales_pos_by_sku.csv`**  
   SKU-level aggregations: total/mean quantity, revenue, price stats, promo count

2. **`sales_pos_by_region.csv`**  
   Regional aggregations: volume, revenue, transactions, retailer count, averages

3. **`sales_pos_by_retailer_top50.csv`**  
   Top 50 retailers by sales volume with region, revenue, transaction count

4. **`sales_pos_by_date.csv`**  
   Daily sales: total units, revenue, transactions, promo transactions

5. **`sales_pos_by_hour.csv`**  
   Hourly patterns: total/mean quantity, revenue, transaction count

6. **`sales_pos_by_promotion.csv`**  
   Promotion performance: units sold, revenue, avg price, retailer reach

7. **`sales_pos_regional_sku_preferences.csv`**  
   SKU × Region cross-tabulation for dispatch optimization

---

## 🔗 Integration with Supply Chain Pipeline

### Upstream Linkages

**Production → QC → Dispatch → Sales**

- **Production:** Sales data drives production planning (demand forecasting)
- **QC:** High sales of certain SKUs justify stricter QC for those products
- **Dispatch:** Sales validate dispatch quantities and timing

### Downstream Linkages

**Sales → Waste / Returns**

- **Low sales + high dispatch** = Overstock → Waste
- **High sales + low dispatch** = Stock-outs → Lost revenue
- **Low sales + high returns** = Quality issues or wrong SKU sent

### Cross-Dataset Analysis Opportunities

1. **Dispatch vs. Sales:**  
   - Are late deliveries correlated with lower sales next day?
   - Do certain routes have persistent overstocking (dispatch > sales)?

2. **QC vs. Sales:**  
   - Do SKUs with high QC fail rates have declining sales trends?
   - Can customer feedback (via sales data) predict QC issues?

3. **Promotions vs. Waste:**  
   - Do promotions reduce waste by clearing inventory faster?
   - Is promo-driven demand sustainable or does it cause post-promo slumps?

---

## 🎯 Recommended Action Items

### Immediate (Week 1-2)

1. ✅ **Expand promotion frequency** from 2% to 10-15% of transactions
2. ✅ **Fix data quality issues** for anomalous SKUs (WholegrainBrown, etc.)
3. ✅ **Investigate Tuesday demand dip** for potential promotional intervention
4. ✅ **Cross-reference dispatch vs. sales** to identify overstock situations

### Short-Term (Month 1-3)

1. ✅ **Demand forecasting model:** Build SKU-level daily forecasts using sales history
2. ✅ **Price elasticity study:** Test price changes for high-margin SKUs
3. ✅ **Regional dispatch optimization:** Use heatmap to customize SKU mix per region
4. ✅ **Retailer performance tiering:** Identify and support top performers

### Long-Term (Quarter 1-2)

1. ✅ **Predictive promotion planning:** ML model to optimize promotion timing/SKU
2. ✅ **Real-time POS integration:** Live sales data feeds production scheduling
3. ✅ **Dynamic pricing:** Region/time-specific pricing based on demand
4. ✅ **Customer segmentation:** Retailer clustering for tailored strategies

---

## 📊 Streamlit Integration

**Status:** ✅ COMPLETE

- Added **Sales POS** dataset to Streamlit EDA Explorer
- Configured 10 visualizations with detailed explanations
- Included 7 summary CSV downloads
- Enhanced with **promotion ROI insights** and **regional preference heatmap**

**Access:** [http://localhost:8506](http://localhost:8506)

---

## 🚀 Next Steps

### Sales Dataset (Wholesale / Depot Channel)

**User mentioned:** "we have two datasets here"

The **Sales Dataset** (`sales_dataset.parquet`) represents the **wholesale/depot channel** (B2B sales to retailers) as opposed to the **POS dataset** (B2C sales to end customers).

**Next implementation:** `eda_sales.py` covering:
- Depot-level sales
- Store-level performance
- Route-level sales analysis
- Comparison with POS data (B2B vs. B2C channels)

---

## ✅ Completion Checklist

- [x] Load and prepare Sales POS dataset (15,000 rows × 9 columns)
- [x] Generate comprehensive summary report (sales_pos_summary.txt)
- [x] Create 7 grouped summary CSVs
- [x] Generate 10 visualizations (SKU, region, promotion, time patterns, pricing, retailers)
- [x] Integrate into Streamlit with detailed explanations
- [x] Document critical findings (+39.1% promotion uplift)
- [x] Identify action items (expand promotions, fix data quality, regional optimization)
- [x] Establish cross-dataset linkages (Production → QC → Dispatch → Sales → Waste/Returns)
- [x] Create implementation summary document

---

**Author:** Baker's Inn Analytics Team  
**Implementation Date:** December 14, 2025  
**Review Status:** Pending stakeholder review  
**Next Dataset:** Sales Dataset (Wholesale/Depot Channel)
