import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import asyncio
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import networkx as nx
from sklearn.neighbors import kneighbors_graph

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

def load_data(file_path):
    """Load CSV data with automatic encoding detection."""
    try:
        return pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

def analyze_data(df):
    """Perform dynamic data analysis."""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        return {
            'summary': df.describe(include='all', datetime_is_numeric=True).to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'correlation': numeric_df.corr().to_dict() if not numeric_df.empty else None
        }
    except Exception as e:
        print(f"Error analyzing data: {e}")
        sys.exit(1)

def visualize_data(df):
    """Generate and save dynamic visualizations."""
    try:
        sns.set(style="whitegrid")
        image_files = []

        numeric_df = df.select_dtypes(include=['number'])

        # Generate numeric distributions
        for column in numeric_df.columns:
            plt.figure()
            sns.histplot(numeric_df[column].dropna(), kde=True)
            plt.title(f'Distribution of {column}')
            image_file = f'{column}_distribution.png'
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

        # Clustering visualization
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

        # Network construction and clustering
        if numeric_df.shape[1] > 1:
            adjacency_matrix = kneighbors_graph(numeric_df.dropna(), n_neighbors=5, mode='connectivity', include_self=False)
            G = nx.from_scipy_sparse_matrix(adjacency_matrix)
            clustering = nx.community.greedy_modularity_communities(G)
            modularity_file = 'network_clustering.png'
            plt.figure()
            pos = nx.spring_layout(G)
            nx.draw(G, pos, with_labels=False, node_size=50, node_color='blue', edge_color='gray')
            for i, community in enumerate(clustering):
                nx.draw_networkx_nodes(G, pos, nodelist=list(community), node_color=plt.cm.tab10(i / len(clustering)))
            plt.title('Network Construction and Clustering')
            plt.savefig(modularity_file, dpi=300, bbox_inches='tight')
            plt.close()
            image_files.append(modularity_file)

        return image_files
    except Exception as e:
        print(f"Error visualizing data: {e}")
        sys.exit(1)

def generate_dynamic_prompt(analysis, image_files):
    """Construct a dynamic prompt based on the analysis and visualizations."""
    prompt = """
        You are a data analyst telling a compelling story.
        Here is the dataset's summary:
        {summary}

        These are the missing values:
        {missing_values}

        If applicable, here is the correlation analysis:
        {correlation}

        Visualizations include:
        {visualizations}

        Create a beautifully written narrative that feels like a story,
        starting with an introduction about the dataset, diving into key findings,
        and concluding with insightful takeaways.
    """.format(
        summary=analysis['summary'],
        missing_values=analysis['missing_values'],
        correlation=analysis.get('correlation', 'No correlation data available'),
        visualizations=', '.join(image_files)
    )
    return prompt

async def generate_narrative(analysis, image_files):
    """Generate a narrative using the LLM."""
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        raise EnvironmentError("AIPROXY_TOKEN environment variable is not set.")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    prompt = generate_dynamic_prompt(analysis, image_files)

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            narrative = response.json()['choices'][0]['message']['content']

            markdown_content = f"# Analysis Report\n\n{narrative}\n\n"
            for image_file in image_files:
                image_name = image_file.split('.')[0].replace('_', ' ').title()
                markdown_content += f"### {image_name}\n\n![{image_name}]({image_file})\n\n"

            return markdown_content
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
        except httpx.RequestError as e:
            print(f"Request error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    return "Narrative generation failed due to an error."

def save_report(markdown_content):
    """Save the generated narrative as a Markdown file."""
    try:
        with open('README.md', 'w') as f:
            f.write(markdown_content)
    except Exception as e:
        print(f"Error saving report: {e}")

def main(file_path):
    try:
        df = load_data(file_path)
        analysis = analyze_data(df)
        image_files = visualize_data(df)
        narrative = asyncio.run(generate_narrative(analysis, image_files))
        save_report(narrative)
        print("Analysis complete. Check README.md for the report.")
    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
