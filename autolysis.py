import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

def load_data(file_path):
    """Load CSV data with encoding detection."""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result['encoding']
    return pd.read_csv(file_path, encoding=encoding)

def analyze_data(df):
    """Perform basic data analysis."""
    numeric_df = df.select_dtypes(include=['number'])  # Select only numeric columns
    analysis = {
        'summary': df.describe(include='all').to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'correlation': numeric_df.corr().to_dict()  # Compute correlation only on numeric columns
    }
    return analysis

def visualize_data(df):
    """Generate and save visualizations."""
    sns.set(style="whitegrid")
    numeric_columns = df.select_dtypes(include=['number']).columns
    image_files = []
    for column in numeric_columns:
        plt.figure()
        sns.histplot(df[column].dropna(), kde=True)
        plt.title(f'Distribution of {column}')
        image_file = f'{column}_distribution.png'
        plt.savefig(image_file, dpi=300, bbox_inches='tight')  # Ensure high-quality saving
        plt.close()
        image_files.append(image_file)

    for image_file in image_files:
        if not os.path.exists(image_file):
            print(f"Error: {image_file} not found!")

    return image_files

    

def generate_narrative(analysis, image_files):
    """Generate narrative using LLM."""
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        raise EnvironmentError("AIPROXY_TOKEN environment variable is not set.")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    prompt = f"Provide a detailed analysis based on the following data summary: {analysis}"
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
    df = load_data(file_path)
    analysis = analyze_data(df)
    image_files = visualize_data(df)
    narrative = generate_narrative(analysis, image_files)
    with open('README.md', 'w') as f:
        f.write(narrative)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
