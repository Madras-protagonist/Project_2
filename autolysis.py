import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"


def detect_encoding(file_path):
    """Detect the file encoding for reading."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(1024)  # Read only a small chunk for detection
        return 'utf-8'  # Assuming UTF-8 for simplicity
    except Exception as e:
        raise ValueError(f"Encoding detection failed: {e}")


def load_data(file_path):
    """Load CSV data with automatic encoding detection."""
    try:
        encoding = detect_encoding(file_path)
        df = pd.read_csv(file_path, encoding=encoding)
        if df.empty:
            raise ValueError("Dataset is empty.")
        return df
    except Exception as e:
        raise ValueError(f"Error loading data: {e}")


def analyze_data(df):
    """Perform basic data analysis."""
    try:
        analysis = {
            'summary': df.describe(include='all', datetime_is_numeric=True).to_dict(),
            'missing_values': df.isnull().sum().to_dict()
        }
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.shape[1] > 1:
            analysis['correlation'] = numeric_df.corr().to_dict()
        return analysis
    except Exception as e:
        raise ValueError(f"Error analyzing data: {e}")


def visualize_data(df):
    """Generate simple visualizations."""
    try:
        sns.set(style="whitegrid")
        image_files = []

        # Generate histogram for each numeric column
        numeric_df = df.select_dtypes(include=['number'])
        for column in numeric_df.columns:
            plt.figure()
            sns.histplot(df[column].dropna(), kde=True, bins=20)
            plt.title(f'Distribution of {column}')
            image_file = f'{column}_histogram.png'
            plt.savefig(image_file, dpi=300, bbox_inches='tight')
            image_files.append(image_file)
            plt.close()

        # Generate correlation heatmap
        if numeric_df.shape[1] > 1:
            plt.figure(figsize=(8, 6))
            sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt='.2f')
            plt.title('Correlation Heatmap')
            heatmap_file = 'correlation_heatmap.png'
            plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
            image_files.append(heatmap_file)
            plt.close()

        return image_files
    except Exception as e:
        raise ValueError(f"Error visualizing data: {e}")


def generate_narrative(analysis, image_files):
    """Generate narrative using LLM."""
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        raise EnvironmentError("AIPROXY_TOKEN environment variable is not set.")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    prompt = (
        f"You are an insightful data analyst. Based on the analysis summary: {analysis}, "
        f"and visualizations: {', '.join(image_files)}, provide a concise and engaging narrative. "
        f"Highlight key patterns, correlations, and any insights derived from the data."
    )

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = httpx.post(API_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        return response.json().get('choices', [{}])[0].get('message', {}).get('content', "Narrative generation failed.")
    except Exception as e:
        raise RuntimeError(f"Error generating narrative: {e}")


def main(file_path):
    try:
        df = load_data(file_path)
        analysis = analyze_data(df)
        image_files = visualize_data(df)
        narrative = generate_narrative(analysis, image_files)

        output_file = 'README.md'
        with open(output_file, 'w') as f:
            f.write(f"# Analysis Report\n\n{narrative}\n")
            for image_file in image_files:
                f.write(f"\n![{image_file}]({image_file})\n")

        print(f"Analysis complete. Check {output_file} for the report.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simplified_analysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
