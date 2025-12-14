"""Streamlit explorer for dispatch features

Features:
- Load `data/features/dispatch_features.parquet`
- Sidebar filters: route_id, plant_id, date range
- Summary metrics and visualizations (histogram, timeseries)
- IsolationForest anomaly demo with contamination slider and downloadable flagged rows

Run:
    streamlit run app/streamlit_dispatch_explorer.py
"""
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import IsolationForest
import os
import json
import logging
from datetime import datetime
import io
import subprocess
import sys
import threading
import time
import pathlib

LOG_DIR = Path('app/logs')
STATUS_FILE = Path('app/status.json')

DATA_PATH = Path("data/features/dispatch_features.parquet")

st.set_page_config(page_title="Dispatch Features Explorer", layout="wide")


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / 'streamlit.log'
    logger = logging.getLogger('streamlit_app')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding='utf-8')
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def write_status(status: str):
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps({
            'status': status,
            'ts': datetime.utcnow().isoformat(),
            'pid': os.getpid()
        }))
    except Exception:
        pass


@st.cache_data(show_spinner=False)
def load_data(path: Path):
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    # basic cleaning
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df


def compute_df_fingerprint(df: pd.DataFrame, numeric_cols):
    # lightweight fingerprint used for caching - not cryptographic
    if not numeric_cols:
        return 'no_numeric'
    s = df[numeric_cols].fillna(0).astype(float).sum().sum()
    return f"{df.shape[0]}_{len(numeric_cols)}_{int(s)}"


@st.cache_data(show_spinner=False)
def cached_compute_anomalies(fingerprint: str, contamination: float, n_estimators: int, X_vals):
    # X_vals is expected to be a 2D numpy array
    clf = IsolationForest(n_estimators=n_estimators, contamination=contamination, random_state=42)
    clf.fit(X_vals)
    scores = -clf.decision_function(X_vals)
    preds = clf.predict(X_vals)
    return scores, preds


def fig_to_png_bytes(fig):
    try:
        # plotly >=5: use fig.to_image (requires kaleido)
        return fig.to_image(format="png")
    except Exception:
        try:
            import plotly.io as pio
            return pio.to_image(fig, format='png', engine='kaleido')
        except Exception:
            return None


def fig_to_html_bytes(fig):
    try:
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return html.encode('utf-8')
    except Exception:
        return None


def check_png_available() -> bool:
    """Try to render a tiny figure to PNG to confirm kaleido/plotly image export works."""
    try:
        import plotly.express as px
        fig = px.scatter(x=[0, 1], y=[0, 1])
        img = fig.to_image(format='png')
        return img is not None
    except Exception:
        return False


# Cache availability at import time so UI can show it quickly
PNG_EXPORT_AVAILABLE = check_png_available()


def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header('Filters')
    routes = sorted(df['route_id'].dropna().unique().tolist()) if 'route_id' in df.columns else []
    plants = sorted(df['plant_id'].dropna().unique().tolist()) if 'plant_id' in df.columns else []
    selected_routes = st.sidebar.multiselect('Route', routes, default=routes[:5])
    selected_plants = st.sidebar.multiselect('Plant', plants, default=plants[:5])
    if 'timestamp' in df.columns:
        min_date = df['timestamp'].min()
        max_date = df['timestamp'].max()
        start, end = st.sidebar.date_input('Date range', [min_date.date(), max_date.date()])
    else:
        start, end = None, None
    return selected_routes, selected_plants, start, end


def filter_df(df: pd.DataFrame, routes, plants, start, end):
    out = df
    if routes:
        out = out[out['route_id'].isin(routes)] if 'route_id' in out.columns else out
    if plants:
        out = out[out['plant_id'].isin(plants)] if 'plant_id' in out.columns else out
    if start is not None and end is not None and 'timestamp' in out.columns:
        mask = (out['timestamp'].dt.date >= start) & (out['timestamp'].dt.date <= end)
        out = out.loc[mask]
    return out


def show_metrics(df: pd.DataFrame):
    st.title('Dispatch Features Explorer')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Dispatches', f"{len(df):,}")
    if 'dispatch_delay_minutes' in df.columns:
        avg = df['dispatch_delay_minutes'].mean()
        pct_delayed = (df['dispatch_delay_minutes'] > 15).mean() * 100
        c2.metric('Avg Delay (min)', f"{avg:.1f}")
        c3.metric('% >15min', f"{pct_delayed:.1f}%")
    else:
        c2.metric('Avg Delay (min)', 'n/a')
        c3.metric('% >15min', 'n/a')
    if 'route_id' in df.columns:
        c4.metric('Routes', df['route_id'].nunique())
    else:
        c4.metric('Routes', 'n/a')


def main():
    logger = setup_logging()
    logger.info('Starting Streamlit Dispatch Explorer')
    write_status('running')

    df = load_data(DATA_PATH)
    if df is None:
        st.error(f"Features file not found at {DATA_PATH}. Run the feature-engineering step first.")
        return

    routes, plants, start, end = sidebar_filters(df)
    df_f = filter_df(df, routes, plants, start, end)
    show_metrics(df_f)

    # show PNG export availability in the sidebar
    with st.sidebar.expander('Export capability'):
        if PNG_EXPORT_AVAILABLE:
            st.success('PNG export available (kaleido detected)')
        else:
            st.warning('PNG export unavailable — Install `kaleido` to enable PNG downloads')

    st.markdown('---')
    left, right = st.columns((2,1))

    with left:
        st.subheader('Delay distribution')
        if 'dispatch_delay_minutes' in df_f.columns:
            fig = px.histogram(df_f, x='dispatch_delay_minutes', nbins=80, title='Dispatch delay (minutes)')
            st.plotly_chart(fig, use_container_width=True)
            # export buttons for the histogram
            png = fig_to_png_bytes(fig)
            html = fig_to_html_bytes(fig)
            fn_ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            c1, c2 = st.columns([1,1])
            with c1:
                if png is not None:
                    st.download_button('Download histogram PNG', png, file_name=f'delay_hist_{fn_ts}.png', mime='image/png')
                else:
                    st.caption('PNG export requires `kaleido`')
            with c2:
                if html is not None:
                    st.download_button('Download histogram HTML', html, file_name=f'delay_hist_{fn_ts}.html', mime='text/html')
        else:
            st.info('No dispatch_delay_minutes column found')

        st.subheader('Rolling mean by route')
        if 'timestamp' in df_f.columns and 'route_id' in df_f.columns:
            # pick a single route to show time series
            route_choice = st.selectbox('Pick route for timeseries', sorted(df_f['route_id'].dropna().unique())[:10])
            ts = df_f[df_f['route_id'] == route_choice].sort_values('timestamp')
            # find rolling mean column if exists
            possible_cols = [c for c in df_f.columns if 'route_id_mean' in c and ('7D' in c or '30D' in c)]
            if possible_cols:
                col = possible_cols[0]
                fig2 = px.line(ts, x='timestamp', y=[col, 'dispatch_delay_minutes'], labels={'value':'minutes'}, title=f'Route {route_choice} rolling')
                st.plotly_chart(fig2, use_container_width=True)
                # export buttons for the timeseries
                png = fig_to_png_bytes(fig2)
                html = fig_to_html_bytes(fig2)
                fn_ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                c1, c2 = st.columns([1,1])
                with c1:
                    if png is not None:
                        st.download_button('Download timeseries PNG', png, file_name=f'route_{route_choice}_rolling_{fn_ts}.png', mime='image/png')
                    else:
                        st.caption('PNG export requires `kaleido`')
                with c2:
                    if html is not None:
                        st.download_button('Download timeseries HTML', html, file_name=f'route_{route_choice}_rolling_{fn_ts}.html', mime='text/html')
            else:
                st.info('No rolling route mean columns found')
        else:
            st.info('Timestamp/route_id missing - cannot show timeseries')

        # correlation heatmap
        st.subheader('Feature correlation heatmap')
        numeric_cols = df_f.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            corr = df_f[numeric_cols].corr()
            fig_corr = px.imshow(corr, text_auto=True, aspect='auto', title='Numeric feature correlation')
            st.plotly_chart(fig_corr, use_container_width=True)
            # export correlation
            png = fig_to_png_bytes(fig_corr)
            html = fig_to_html_bytes(fig_corr)
            fn_ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            c1, c2 = st.columns([1,1])
            with c1:
                if png is not None:
                    st.download_button('Download corr PNG', png, file_name=f'corr_{fn_ts}.png', mime='image/png')
                else:
                    st.caption('PNG export requires `kaleido`')
            with c2:
                if html is not None:
                    st.download_button('Download corr HTML', html, file_name=f'corr_{fn_ts}.html', mime='text/html')
        else:
            st.info('Not enough numeric features for correlation matrix')

        # small-multiples (per-route) time series
        st.subheader('Small multiples by route')
        if 'timestamp' in df_f.columns and 'route_id' in df_f.columns and numeric_cols:
            sm_feat = st.selectbox('Numeric feature for small-multiples', numeric_cols, index=0, key='sm_feat')
            max_routes = min(12, df_f['route_id'].nunique())
            n_routes = st.slider('Number of routes to show', 1, max_routes, min(6, max_routes))
            # choose top routes by count
            top_routes = df_f['route_id'].value_counts().nlargest(n_routes).index.tolist()
            sm_df = df_f[df_f['route_id'].isin(top_routes)].sort_values(['route_id','timestamp'])
            if not sm_df.empty:
                fig_sm = px.line(sm_df, x='timestamp', y=sm_feat, color='route_id', facet_col='route_id', facet_col_wrap=3, height=300 + 120 * (n_routes // 3))
                st.plotly_chart(fig_sm, use_container_width=True)
            else:
                st.info('No data for selected routes')
        else:
            st.info('Need timestamp, route_id and numeric features for small-multiples')

    with right:
        st.subheader('Top features & sample')
        st.write(df_f.select_dtypes(include=['number']).iloc[:10, :10])
        st.subheader('Preview rows')
        st.dataframe(df_f.head(200))

        # Export options for filtered dataset
        st.markdown('### Export filtered data')
        csv_bytes = df_f.to_csv(index=False).encode('utf-8')
        st.download_button('Download filtered rows (CSV)', csv_bytes, file_name='dispatch_filtered.csv', mime='text/csv')

        # summary CSV (group by route or overall)
        summary_choice = st.selectbox('Summary by', ['overall','route_id','plant_id'], index=0)
        if summary_choice == 'overall':
            summary_df = df_f.describe(include='all').reset_index()
        else:
            grp_col = summary_choice
            numeric_for_summary = df_f.select_dtypes(include=[np.number]).columns.tolist()
            summary_df = df_f.groupby(grp_col)[numeric_for_summary].agg(['mean','median','std','count'])
            # flatten columns
            summary_df.columns = ['_'.join(col).strip() for col in summary_df.columns.values]
            summary_df = summary_df.reset_index()
        summary_csv = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button('Download summary CSV', summary_csv, file_name='dispatch_summary.csv', mime='text/csv')

        # anomalies parquet download if present
        anomalies_path = Path('data/features/dispatch_features_anomalies.parquet')
        if anomalies_path.exists():
            with open(anomalies_path, 'rb') as f:
                an_bytes = f.read()
            st.download_button('Download anomalies parquet', an_bytes, file_name=anomalies_path.name, mime='application/octet-stream')

        # feature-by-route distribution
        st.subheader('Feature by route')
        if 'route_id' in df_f.columns and numeric_cols:
            feat = st.selectbox('Numeric feature', numeric_cols, index=0)
            rts = sorted(df_f['route_id'].dropna().unique())[:10]
            rt_choice = st.selectbox('Route (compare)', rts)
            fig_rt = px.box(df_f[df_f['route_id'].isin(rts)], x='route_id', y=feat, title=f'{feat} distribution across routes')
            st.plotly_chart(fig_rt, use_container_width=True)
            # export boxplot
            png = fig_to_png_bytes(fig_rt)
            html = fig_to_html_bytes(fig_rt)
            fn_ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            c1, c2 = st.columns([1,1])
            with c1:
                if png is not None:
                    st.download_button('Download boxplot PNG', png, file_name=f'box_{feat}_{fn_ts}.png', mime='image/png')
                else:
                    st.caption('PNG export requires `kaleido`')
            with c2:
                if html is not None:
                    st.download_button('Download boxplot HTML', html, file_name=f'box_{feat}_{fn_ts}.html', mime='text/html')
        else:
            st.info('Need numeric features and route_id for per-route visuals')

    st.markdown('---')
    st.subheader('Anomaly detection (IsolationForest)')
    with st.sidebar.expander('Anomaly settings'):
        contamination = st.slider('Contamination', min_value=0.001, max_value=0.2, value=0.02, step=0.001)
        n_estimators = st.slider('n_estimators', 50, 500, 100, step=10)
        run_model = st.button('Run IsolationForest')
        precompute = st.button('Precompute anomalies and save (parquet)')

    # Training controls
    st.sidebar.markdown('---')
    st.sidebar.header('Train baseline model')
    train_cont = st.sidebar.slider('Train contamination', min_value=0.001, max_value=0.2, value=0.02, step=0.001)
    train_splits = st.sidebar.slider('Time CV splits', 2, 10, 5)
    do_train = st.sidebar.button('Train baseline (IsolationForest + z-score)')

    if run_model or precompute:
        numeric_cols = df_f.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.warning('No numeric features available for model')
        else:
            X = df_f[numeric_cols].fillna(0).astype(float)
            fingerprint = compute_df_fingerprint(df_f, numeric_cols)
            X_vals = X.values
            scores, preds = cached_compute_anomalies(fingerprint, contamination, n_estimators, X_vals)
            df_f = df_f.copy()
            df_f['anomaly_score'] = scores
            df_f['anomaly'] = preds == -1
            st.write(f"Flagged {df_f['anomaly'].sum()} rows as anomalies")
            top = df_f.sort_values('anomaly_score', ascending=False).head(200)
            st.dataframe(top.head(200))
            csv = top.to_csv(index=False)
            st.download_button('Download flagged rows (CSV)', csv, file_name='dispatch_flagged.csv', mime='text/csv')
            if precompute:
                # save full results to parquet for later use
                out_path = Path('data/features/dispatch_features_anomalies.parquet')
                df_f.to_parquet(out_path, index=False)
                st.success(f'Wrote anomalies to {out_path}')
                logger.info(f'Wrote anomalies to {out_path}')

    # Run training script via subprocess when button is clicked
    # confirmation flow: require explicit confirm button to start long-running training
    if do_train:
        st.warning('Training can be long. Confirm to start the training job.')
        if st.sidebar.button('Confirm and start training'):
            # prepare paths
            reports_dir = Path('reports/models')
            reports_dir.mkdir(parents=True, exist_ok=True)
            log_path = reports_dir / 'train_run.log'
            status_path = reports_dir / 'train_status.json'

            def run_training_subprocess(cmd, log_path: pathlib.Path, status_path: pathlib.Path):
                # write status
                status = {'running': True, 'start_ts': datetime.utcnow().isoformat(), 'pid': None, 'returncode': None}
                status_path.write_text(json.dumps(status))
                with open(log_path, 'w', encoding='utf-8') as lf:
                    try:
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        status['pid'] = proc.pid
                        status_path.write_text(json.dumps(status))
                        for line in proc.stdout:
                            lf.write(line)
                            lf.flush()
                            # update status with last line
                            status['last_line'] = line.strip()
                            status_path.write_text(json.dumps(status))
                        proc.wait()
                        status['returncode'] = int(proc.returncode)
                    except Exception as e:
                        lf.write(f'ERROR: {e}\n')
                        status['error'] = str(e)
                    finally:
                        status['running'] = False
                        status['end_ts'] = datetime.utcnow().isoformat()
                        status_path.write_text(json.dumps(status))

            cmd = [sys.executable, 'src/models/train_baseline.py',
                   '--input', str(DATA_PATH),
                   '--out_dir', 'reports/models',
                   '--contamination', str(train_cont),
                   '--n_splits', str(train_splits)]

            # start thread
            thread = threading.Thread(target=run_training_subprocess, args=(cmd, log_path, status_path), daemon=True)
            thread.start()
            st.success('Training started in background; tailing logs below')

            # tail logs until finished
            placeholder = st.empty()
            while True:
                time.sleep(0.5)
                # read status
                try:
                    status = json.loads(status_path.read_text())
                except Exception:
                    status = {'running': True}
                # read last N lines of log
                if log_path.exists():
                    text = log_path.read_text(errors='ignore')
                else:
                    text = ''
                with placeholder.container():
                    st.subheader('Training log')
                    st.text_area('log', value=text[-20000:], height=400)
                    if not status.get('running', True):
                        st.success('Training finished')
                        break

            # show generated report and flagged anomalies if present
            report_path = Path('reports/models/baseline_report.json')
            flagged_path = Path('reports/models/flagged_anomalies.csv')
            if report_path.exists():
                try:
                    rep = json.loads(report_path.read_text())
                    st.subheader('Baseline report (summary)')
                    st.json({k: rep.get(k) for k in ['n_folds', 'folds']})
                    rpt_bytes = report_path.read_text().encode('utf-8')
                    st.download_button('Download baseline_report.json', rpt_bytes, file_name=report_path.name, mime='application/json')
                except Exception as e:
                    st.warning('Could not read report file: %s' % e)
            if flagged_path.exists():
                with open(flagged_path, 'rb') as f:
                    st.download_button('Download flagged anomalies CSV', f.read(), file_name=flagged_path.name, mime='text/csv')

    st.markdown('---')
    st.caption('Explorer: quick demo. Extend visuals and model features for production.')

if __name__ == '__main__':
    main()
