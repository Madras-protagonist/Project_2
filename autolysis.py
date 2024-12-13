import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

def detect_encoding(file_path):
    """Detect the file encoding for reading."""
    try:
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        return result['encoding']
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
    """Perform dynamic data analysis."""
    try:
        analysis = {
            'summary': df.describe(include='all', datetime_is_numeric=True).to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
        }

        numeric_df = df.select_dtypes(include=['number'])
        if not numeric_df.empty:
            # Add correlation only if there are sufficient numeric columns
            if numeric_df.shape[1] > 1:
                analysis['correlation'] = numeric_df.corr().to_dict()
        
        return analysis
    except Exception as e:
        raise ValueError(f"Error analyzing data: {e}")

def visualize_data(df):
    """Generate and save dynamic visualizations."""
    try:
        sns.set(style="whitegrid")
        image_files = []

        numeric_df = df.select_dtypes(include=['number'])

        # Visualizations based on data type
        for column in df.columns:
            plt.figure()
            try:
                if df[column].dtype in ['float64', 'int64']:
                    sns.histplot(df[column].dropna(), kde=True)
                    plt.title(f'Distribution of {column}')
                elif df[column].dtype == 'object' and df[column].nunique() <= 20:
                    sns.countplot(y=df[column].fillna('Missing'))
                    plt.title(f'Count of {column}')
                elif pd.api.types.is_datetime64_any_dtype(df[column]):
                    sns.lineplot(data=df, x=df[column], y=df.index)
                    plt.title(f'Time Series for {column}')
                else:
                    continue

                image_file = f'{column}_visualization.png'
                plt.savefig(image_file, dpi=300, bbox_inches='tight')
                image_files.append(image_file)
            except Exception as e:
                print(f"Visualization failed for {column}: {e}")
            finally:
                plt.close()

        # Correlation heatmap
        if not numeric_df.empty and numeric_df.shape[1] > 1:
            plt.figure(figsize=(10, 8))
            sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt='.2f')
            plt.title('Correlation Heatmap')
            heatmap_file = 'correlation_heatmap.png'
            plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
            image_files.append(heatmap_file)

            # Clustering if applicable
            if numeric_df.shape[1] > 1:
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(numeric_df.dropna())
                kmeans = KMeans(n_clusters=3, random_state=42)
                df['Cluster'] = kmeans.fit_predict(scaled_data)
                sns.pairplot(df, hue='Cluster', palette='tab10', diag_kind='kde')
                cluster_file = 'cluster_analysis.png'
                plt.savefig(cluster_file, dpi=300, bbox_inches='tight')
                image_files.append(cluster_file)

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
        f"You are an insightful data analyst and visualization expert. Based on the provided analysis summary: {analysis}, "
        f"and the associated visualizations: {', '.join(image_files)}, generate a comprehensive and engaging narrative. "
        f"Highlight key patterns, correlations, and anomalies from the data. For visualizations, create interpretative "
        f"descriptions that explain their relevance and insights. Use an accessible and intriguing tone to keep the reader engaged."
    )

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = httpx.post(API_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        narrative = response.json().get('choices', [{}])[0].get('message', {}).get('content', "Narrative generation failed.")

        markdown_content = f"# Analysis Report\n\n{narrative}\n\n"
        for image_file in image_files:
            image_name = image_file.split('.')[0].replace('_', ' ').title()
            markdown_content += f"### {image_name}\n\n![{image_name}]({image_file})\n\n"

        return markdown_content
    except httpx.HTTPStatusError as e:
        raise ConnectionError(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        raise ConnectionError(f"Request error occurred: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during narrative generation: {e}")

def main(file_path):
    try:
        df = load_data(file_path)
        analysis = analyze_data(df)
        image_files = visualize_data(df)
        narrative = generate_narrative(analysis, image_files)

        output_file = 'README.md'
        with open(output_file, 'w') as f:
            f.write(narrative)

        print(f"Analysis complete. Check {output_file} for the report.")
    except Exception as e:
        print(f"Error in main execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
