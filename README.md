# [Salton](https://en.wikipedia.org/wiki/Gerard_Salton) - Information Retrieval System

🚧 <img src="https://img.shields.io/badge/under%20construction-FF8C00" /> <img src="https://img.shields.io/badge/beta-blue"/> 🚧

## Project description

This repository contains the evolution of the Information Retrieval project. It's a vertical search engine built upon a corpus of documents sourced from CORE (COnnecting REpositories), a public repository of open-access research papers. 
The goal is to provide a more refined search experience than CORE [portal](https://core.ac.uk).
It uses the [Okapi BM25](https://en.wikipedia.org/wiki/Okapi_BM25) ranking function to estimate the relevance of documents.
End users can formulate queries based on a defined language, results are presented in order of relevance with title, score, and abstract.


## Architecture

<img src="assets/diagram.png" alt="diagram" width="600"/>

## Running the project

### Prerequisites
- `python` >= 3.8
- `pip`

### Install (dev mode)
```bash
git clone https://github.com/stefanoghinelli/salton.git
cd salton

pip install -e .
```

### Install NLTK data
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('omw-1.4')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
```

### Setup environment
```bash
sh setup_scripts/01.prepare_environment.sh
```

## Usage

```bash
# Show commands
salton --help

# Fetch papers from source
salton fetch -l 100

# Preprocess papers
salton preprocess

# Build index
salton index

# Search for papers
salton search -q "your query" -l 10

# View statistics
salton stats

# Run benchmakrs
salton benchmark
```

### Command details
1. `fetch`: downloads papers from CORE
   - `-l, --limit`: number of papers to fetch (default: 100)

2. `preprocess`: preprocesses downloaded papers
   - Extracts text from PDFs
   - Performs tokenization and lemmatization
   - Applies word sense disambiguation (if enabled)
   - `--wsd`: Enable word sense disambiguation (off by default)

3. `index`: builds the search index

4. `search`: search for papers
   - `-q, --query`: search query
   - `-l, --limit`: number of results to show (default: 10)

5. `stats`: shows statistics

6. `benchmark`: runs benchmarks (experimental feature)
   - `--save/--no-save`: save results to file (default: save)
   - `--detailed/--simple`: show detailed results (default: simple)

> [!WARNING]
> The word sense disambiguation computes similarity between word senses and compares each term against multiple context. This quadratic operation can be highly time consuming.

## Evaluation

### Setup benchmarks
To run benchmarks, you'll need aset of test queries in the `evaluation` directory:
   - `query_natural_lang.txt`: natural language queries
   - `query_benchmark.txt`: structured queries
   - `query_relevance.txt`: relevance data

### Benchmark metrics
The system evaluates search results using:

- **Precision**: fraction of retrieved documents that are relevant
- **Recall**: fraction of relevant documents that are retrieved
- **NDCG**: measures ranking quality considering position
- **MAP**: mean of average precision scores

## Results

```
==================================================
  Results for: cloud computing
==================================================

1. Title: Distributed service orchestration: eventually consistent cloud operation and integration
   Score: 20.3674
   Abstract: Both researchers and industry players are facing the same obstacles...

2. Title: Middleware platform for distributed applications incorporating robots, sensors and the cloud
   Score: 20.3317
   Abstract: Cyber-physical systems in the factory of the future...

3. Title: Service-Oriented Multigranular Optical Network Architecture for Clouds
   Score: 18.0107
   Abstract: This paper presents a novel service-oriented network architecture...
```