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


def load_data(file_path):
    """Load CSV data with encoding detection."""
    try:
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        encoding = result['encoding']
        return pd.read_csv(file_path, encoding=encoding)
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


def analyze_data(df):
    """Perform dynamic data analysis."""
    try:
        analysis = {
            'summary': df.describe(include='all', datetime_is_numeric=True).to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
        }
        # Add correlation only if numeric columns are present
        numeric_df = df.select_dtypes(include=['number'])
        if not numeric_df.empty:
            analysis['correlation'] = numeric_df.corr().to_dict()
        return analysis
    except Exception as e:
        print(f"Error analyzing data: {e}")
        sys.exit(1)


def visualize_data(df):
    """Generate and save dynamic visualizations."""
    try:
        sns.set(style="whitegrid")
        image_files = []

        numeric_df = df.select_dtypes(include=['number'])

        for column in df.columns:
            plt.figure()
            if df[column].dtype in ['float64', 'int64']:
                sns.histplot(df[column].dropna(), kde=True)
                plt.title(f'Distribution of {column}')
            elif df[column].dtype == 'object':
                sns.countplot(y=df[column].fillna('Missing'))
                plt.title(f'Count of {column}')
            elif pd.api.types.is_datetime64_any_dtype(df[column]):
                sns.lineplot(data=df, x=df[column], y=df.index)
                plt.title(f'Time Series for {column}')
            else:
                plt.close()
                continue

            image_file = f'{column}_visualization.png'
            plt.savefig(image_file, dpi=300, bbox_inches='tight')
            plt.close()
            image_files.append(image_file)

        # Correlation heatmap
        if not numeric_df.empty:
            plt.figure(figsize=(10, 8))
            sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt='.2f')
            plt.title('Correlation Heatmap')
            heatmap_file = 'correlation_heatmap.png'
            plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
            plt.close()
            image_files.append(heatmap_file)

        # Cluster analysis
        if numeric_df.shape[1] > 1:
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_df.dropna())
            kmeans = KMeans(n_clusters=3, random_state=42)
            clusters = kmeans.fit_predict(scaled_data)
            df['Cluster'] = clusters
            plt.figure()
            sns.pairplot(df, hue='Cluster', palette='tab10', diag_kind='kde')
            cluster_file = 'cluster_analysis.png'
            plt.savefig(cluster_file, dpi=300, bbox_inches='tight')
            plt.close()
            image_files.append(cluster_file)

        # Possible data distributions
        for column in numeric_df.columns:
            plt.figure()
            sns.boxplot(x=df[column])
            plt.title(f'Boxplot of {column}')
            boxplot_file = f'{column}_boxplot.png'
            plt.savefig(boxplot_file, dpi=300, bbox_inches='tight')
            plt.close()
            image_files.append(boxplot_file)

        if not image_files:
            print("No suitable columns for visualization.")

        return image_files
    except Exception as e:
        print(f"Error visualizing data: {e}")
        sys.exit(1)


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
        f"You are an analyst. Based on the following data summary: {analysis}, "
        f"and these visualizations: {', '.join(image_files)}, "
        f"create a detailed and insightful analysis with a narrative that highlights key findings "
        f"and integrates visual context effectively."
    )

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = httpx.post(API_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        narrative = response.json()['choices'][0]['message']['content']

        markdown_content = f"# Analysis Report\n\n{narrative}\n\n"
        for image_file in image_files:
            image_name = image_file.split('.')[0].replace('_', ' ').title()
            markdown_content += f"### {image_name}\n\n"
            markdown_content += f"![{image_name}]({image_file})\n\n"

        return markdown_content
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        print(f"Request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return "Narrative generation failed due to an error."


def main(file_path):
    try:
        df = load_data(file_path)
        analysis = analyze_data(df)
        image_files = visualize_data(df)
        narrative = generate_narrative(analysis, image_files)

        with open('README.md', 'w') as f:
            f.write(narrative)

        print("Analysis complete. Check README.md for the report.")
    except Exception as e:
        print(f"Error in main execution: {e}")


if _name_ == "_main_":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
