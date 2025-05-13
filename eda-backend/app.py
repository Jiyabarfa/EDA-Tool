from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re
from zipfile import ZipFile

app = Flask(__name__)
CORS(app)

os.makedirs("media/plots", exist_ok=True)

# sanitize filenames
def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?"<>|: ]+', '_', name)

@app.route('/media/plots/<path:filename>')
def serve_plot(filename):
    return send_from_directory('media/plots', filename)

@app.route('/media/plots/all.zip')
def download_all():
    try:
        zip_path = 'media/plots/all.zip'
        with ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk('media/plots'):
                for file in files:
                    if file.endswith('.png'):
                        zipf.write(os.path.join(root, file), arcname=file)
        return send_from_directory('media/plots', 'all.zip', as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        df = pd.read_csv(file)
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

        data_summary = {
            'columns': df.columns.tolist(),
            'shape': df.shape,
            'summary': df.describe(include='all').fillna('').to_dict(),
            'value_counts': {
                col: df[col].value_counts().head(5).to_dict()
                for col in df.select_dtypes(include=['object', 'category']).columns
                if col != 'name' and 'name' not in col
            }
        }

        plot_paths = []

        cat_cols = [c for c in df.select_dtypes(include=['object', 'category']).columns
                    if c != 'name' and 'name' not in c]
        for col in cat_cols:
            counts = df[col].dropna().value_counts()
            if counts.empty:
                continue
            clean = sanitize(col)

            if counts.size <= 5:
                plt.figure(figsize=(6,6))
                counts.plot(kind='pie', autopct='%1.1f%%')
                plt.title(f'Pie: {col}')
                plt.ylabel('')
                plt.tight_layout()
                fname = f'{clean}_pie.png'
                fpath = os.path.join('media/plots', fname)
                plt.savefig(fpath)
                plt.close()
                plot_paths.append({'title': f'Pie: {col}', 'url': f'/media/plots/{fname}'})
            else:
                plt.figure(figsize=(6,4))
                counts.plot(kind='bar')
                plt.title(f'Bar: {col}')
                plt.xlabel(col)
                plt.ylabel('Count')
                plt.tight_layout()
                fname = f'{clean}_bar.png'
                fpath = os.path.join('media/plots', fname)
                plt.savefig(fpath)
                plt.close()
                plot_paths.append({'title': f'Bar: {col}', 'url': f'/media/plots/{fname}'})

        num_cols = [c for c in df.select_dtypes(include=['number']).columns
                    if not c.startswith('unnamed')]
        for col in num_cols:
            series = df[col].dropna()
            if series.nunique() < 2:
                continue
            clean = sanitize(col)
            plt.figure(figsize=(6,4))
            series.plot(kind='hist', bins=20)
            plt.title(f'Histogram: {col}')
            plt.xlabel(col)
            plt.ylabel('Frequency')
            plt.tight_layout()
            fname = f'{clean}_hist.png'
            fpath = os.path.join('media/plots', fname)
            plt.savefig(fpath)
            plt.close()
            plot_paths.append({'title': f'Histogram: {col}', 'url': f'/media/plots/{fname}'})

                    # Generate textual summary
        null_counts = df.isnull().sum()
        top_nulls = null_counts[null_counts > 0].sort_values(ascending=False).head(3)
        top_nulls_text = ", ".join([f"{col} ({cnt} nulls)" for col, cnt in top_nulls.items()]) or "None"

        top_freq = {}
        for col in df.select_dtypes(include=['object', 'category']):
            if col != 'name' and 'name' not in col:
                most_common = df[col].value_counts().idxmax()
                top_freq[col] = most_common

        freq_text = ", ".join([f"{col}: {val}" for col, val in top_freq.items()]) or "None"

        summary_text = (
            f"📊 Dataset contains {df.shape[0]} rows and {df.shape[1]} columns.\n"
            f"🧱 Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}.\n"
            f"🔍 Top frequent values: {freq_text}.\n"
            f"❗ Columns with most missing values: {top_nulls_text}."
        )


        return jsonify({'data_summary': data_summary, 'summary_text': summary_text, 'plots': plot_paths})


    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)