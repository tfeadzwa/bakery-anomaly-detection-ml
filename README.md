# Dispatch Features Explorer

This project contains a Streamlit app to explore dispatch features and run a quick anomaly detection demo.

Quick start (requires the project's virtual environment):

1. Activate the project's venv (Windows PowerShell example):

```bash
# If using bash on Windows (Git Bash / WSL), adapt accordingly
source .venv/Scripts/activate
```

2. Install dependencies (only needed once or after changes to `requirements.txt`):

```bash
pip install -r requirements.txt
```

3. Run the Streamlit app:

```bash
streamlit run app/streamlit_dispatch_explorer.py
```

By default the app runs on `http://localhost:8501`.

Notes:
- Ensure `data/features/dispatch_features.parquet` exists (created by the feature-engineering step). If not, run `python src/analysis/feature_engineer_dispatch.py` first.
- The app includes an IsolationForest demo; it uses numeric features present in the features parquet. For large datasets, consider increasing memory or using the `--server.maxUploadSize` Streamlit option.

```streamlit run app/streamlit_dispatch_explorer.py --server.port 8501 --server.headless true```

# Run Streamlit module via the venv's python executable
C:/Users/Tafadzwa/Documents/mywork/taps/.venv/Scripts/python -m streamlit run app/streamlit_dispatch_explorer.py --server.port 8501

$ python -m py_compile "C:/Users/Tafadzwa/Documents/mywork/taps/app/streamlit_dispatch_explorer.py"