# 🍞 SmartBakery: Anomaly Detection and Waste Reduction in Bakery Operations

**End-to-End Machine Learning System for Bakery Supply Chain Optimization**

An integrated data-driven analytics and machine learning platform that analyzes bakery production, logistics, sales, and quality data to detect anomalies, predict waste, and optimize supply-chain performance.

---

## 📋 Project Overview

SmartBakery is a data-driven analytics and machine learning project designed to detect operational anomalies and reduce product waste in bakery production and supply-chain operations. Using large-scale transactional data generated across the bakery lifecycle — including production, quality control, dispatch, retail sales, returns, waste, inventory movements, transport routes, equipment sensors, and calendar events — the system provides end-to-end visibility into how bread products are manufactured, distributed, sold, and lost.

The project applies **anomaly detection**, **time-series analysis**, and **predictive modeling** techniques to identify unusual patterns such as abnormal production volumes, quality defects, late or inefficient dispatch routes, mismatches between supply and demand, excessive returns, and avoidable waste. By linking batch-level production data with quality inspections, logistics metadata, point-of-sale demand signals, and environmental or equipment conditions, SmartBakery enables **root-cause analysis** of operational failures that lead to spoilage, stock-outs, or inefficiencies.

In addition to detecting anomalies, the system supports **demand forecasting** and **waste prediction** by incorporating contextual factors such as public holidays, promotions, regional demand differences, and route complexity. The resulting insights can be used to optimize production planning, improve dispatch scheduling, enhance quality control processes, and reduce financial losses caused by expired or unsold products.

**SmartBakery demonstrates how machine learning and data analytics can be applied in a realistic bakery operations context to improve efficiency, sustainability, and decision-making, making it suitable for both academic research and practical industry adoption.**

### 🔑 Core Capabilities

- ✅ **Anomaly Detection** across production, logistics, and sales operations
- ✅ **Batch-Level Traceability** and root-cause analysis for quality failures
- ✅ **Waste & Returns Prediction** using supervised learning models
- ✅ **Demand Forecasting** with holiday and promotion effects
- ✅ **Route Performance Analysis** and dispatch optimization
- ✅ **Inventory Reconciliation** and stock-out detection
- ✅ **Multi-Source Data Integration** from 10+ operational datasets
- ✅ **Real-Time IoT Analytics** for temperature and equipment monitoring

---

## 🚨 Critical Findings

### **Data Integrity Crisis**
- **29.2% of inventory movements show negative balances** (5,286 out of 18,073 records)
- **Flow efficiency: 8.6%** (should be 100%) - 2.75M units "missing" between plant dispatch and store receipt
- **Root cause**: Missing inbound records, double-counted dispatch, or unlogged waste
- **Impact**: Cannot trust inventory for production planning or demand forecasting

### **Quality Control Emergency**
- **36.15% QC fail rate** (6,540 fails out of 18,090 checks) - **18X above target (2%)**
- **Top failing parameters**: crust_color_level (55.53%), slice_uniformity (54.32%)
- **Impact**: 3 out of 4 batches rejected → massive rework costs, dispatch delays, waste

### **Waste & Returns Drivers**
- **1.3M units wasted**: 59.3% at production stage, 40.7% post-dispatch
- **791K units returned**: 58.4% preventable (cold chain/quality failures)
- **Top waste reason**: Contaminated (10.5%) - sanitation crisis
- **Top return reason**: Mould Growth (15%) - cold chain failure

### **Logistics Insights**
- **47.7% rural routes** (>60km) - freshness degradation risk
- **4 high-risk routes** (>0.7 risk score) - need priority monitoring
- **100% vehicles underutilized** (<50% capacity) - consolidation opportunity
- **Monday B2B ordering peak**: 359K units (weekly restocking pattern)

---

## 📊 Datasets Analyzed

| Dataset | Records | Key Insights |
|---------|---------|--------------|
| **Production** | 15,000 batches | 444K defects (2.68% rate), 5 lines, 7 SKUs |
| **Quality Control** | 18,090 checks | **36.15% fail rate**, crust_color worst (55.53%) |
| **Dispatch** | 15,000 trips | Mean 17.1 min delay, 12 routes, IoT-tracked |
| **Sales (B2C)** | 15,000 transactions | 465K units, $1.43 avg, **+39.1% promo uplift** |
| **Sales (B2B)** | 15,099 orders | 2.45M units, 162 units/order (5.2X retail) |
| **Waste** | 14,070 incidents | **1.3M units**, 59.3% production-stage |
| **Returns** | 13,065 incidents | **791K units**, 58.4% preventable |
| **Inventory** | 18,073 movements | **🚨 29.2% negative balances**, 8.6% flow efficiency |
| **Route Metadata** | 216 configs | 69 routes, 101 vehicles, 31.7 km/h avg speed |
| **IoT Sensors** | 450,000 readings | Temp/humidity/vibration monitoring |

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.10+
- Git
- 8GB+ RAM recommended

### **1. Clone Repository**
```bash
git clone https://github.com/YOUR_USERNAME/taps-supply-chain-analytics.git
cd taps-supply-chain-analytics
```

### **2. Setup Environment**
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows Git Bash)
source .venv/Scripts/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **3. Prepare Data**
```bash
# Place your raw datasets in data/raw/
# Then run data pipeline
python src/data/prepare_data.py
```

### **4. Run EDA Scripts**
```bash
# Generate comprehensive analysis reports
python src/analysis/eda_production.py
python src/analysis/eda_quality_control.py
python src/analysis/eda_inventory_enhanced.py
python src/analysis/eda_routes_transport_meta.py
```

Each script generates:
- Comprehensive text summary in `reports/`
- 10-12 visualizations in `reports/figures/`
- 6-8 CSV summaries in `reports/summaries/`

### **5. Launch Streamlit Dashboards**

**Main EDA Explorer (Recommended):**
```bash
streamlit run app/streamlit_eda_explorer.py --server.port 8506
```
Access at: http://localhost:8506

**Dispatch Anomaly Detection:**
```bash
streamlit run app/streamlit_dispatch_explorer.py --server.port 8501
```
Access at: http://localhost:8501

---

## 📊 Expected Impact & ROI

### **Waste Reduction (30% achievable)**
- **Current waste**: 1.3M units/year
- **Target reduction**: 30% = 390K units saved
- **Value saved**: 390K × $1.43 = **$557,700/year**

### **Returns Reduction (35% of preventable)**
- **Preventable returns**: 462K units (58.4%)
- **Target reduction**: 35% = 162K units saved
- **Value saved**: 162K × $1.43 = **$231,660/year**

### **Quality Improvement (Fail rate 36.15% → 10%)**
- **Current fails**: 6,540 out of 18,090 checks
- **Target**: Reduce to 10% (still above 2% target, but realistic)
- **Rework savings**: 4,700 fewer failures × $50/rework = **$235,000/year**

### **Logistics Optimization**
- **Vehicle consolidation**: 30% fuel savings = **$100,000/year**
- **Route optimization**: 20% time savings = **$80,000/year**

### **Total Potential ROI: ~$1.2M/year**

---

## 🛠️ Technologies Used

- **Python 3.14**: Core programming language
- **Pandas 2.3.3**: Data manipulation & analysis
- **NumPy**: Numerical computing
- **Matplotlib / Seaborn**: Visualization
- **Streamlit**: Interactive dashboards
- **Scikit-learn**: Machine learning (IsolationForest, future models)
- **Parquet**: Efficient data storage format
- **Git**: Version control

---

## 📚 Documentation

- [**INVENTORY_CRISIS_REPORT.md**](docs/INVENTORY_CRISIS_REPORT.md) - Detailed analysis of 29.2% negative balance crisis
- [**SALES_POS_EDA_IMPLEMENTATION_SUMMARY.md**](docs/SALES_POS_EDA_IMPLEMENTATION_SUMMARY.md) - B2C sales analysis
- [**SALES_B2B_EDA_IMPLEMENTATION_SUMMARY.md**](docs/SALES_B2B_EDA_IMPLEMENTATION_SUMMARY.md) - Wholesale distribution analysis
- [**WASTE_RETURNS_EDA_IMPLEMENTATION_SUMMARY.md**](docs/WASTE_RETURNS_EDA_IMPLEMENTATION_SUMMARY.md) - Waste & returns deep dive
- [**QC_EDA_IMPLEMENTATION_SUMMARY.md**](docs/QC_EDA_IMPLEMENTATION_SUMMARY.md) - Quality control crisis report

---

## 🤝 Contributing

This is an active analytics project. For questions, suggestions, or collaboration:
- Open an issue for bug reports or feature requests
- Submit pull requests for improvements
- Contact the data team for access to additional datasets

---

## 📄 License

This project is proprietary and confidential. Unauthorized distribution prohibited.

---

## 🎓 Project Context

**Business Goal**: Reduce supply chain waste by 30% through data-driven interventions, saving $600K+ annually.

**Core Philosophy**: 
- "Inventory is not just another dataset — it is the state of the system."
- "If inventory is broken, something upstream failed."
- "Waste is the final loss, but it starts at production."

**Key Insight**: The supply chain is a system. You cannot optimize one component (e.g., dispatch) without understanding how it affects everything else (inventory, waste, returns). This project treats the entire value chain as an interconnected system and uses data to expose hidden failures.

---

**Last Updated**: December 14, 2025  
**Version**: 1.0.0  
**Status**: Active Development
