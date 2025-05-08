# [salton](https://en.wikipedia.org/wiki/Gerard_Salton)

🚧 <img src="https://img.shields.io/badge/under%20construction-FF8C00" /> <img src="https://img.shields.io/badge/beta-blue"/> 🚧

## Project description

This repository contains the evolution of the Information Retrieval project. It's a vertical search engine built upon a corpus of documents sourced from CORE (COnnecting REpositories), a public repository of open-access research papers. 
The goal is to provide a more refined search experience than CORE [portal](https://core.ac.uk).
It uses the [Okapi BM25](https://en.wikipedia.org/wiki/Okapi_BM25) ranking function to estimate the relevance of documents.
End users can formulate queries based on a defined language, results are presented in order of relevance with title, score, and abstract.


## Architecture

<img src="assets/diagram.png" alt="diagram" width="600"/>

## Running the project

This project runs using python 3 and pip. To install it as a Python package, do the followings:

1. Clone the repository and change directory

```bash
$ git clone https://github.com/stefanoghinelli/salton.git
$ cd salton
```

2. Install using pip

```bash
$ pip install -e .
```

3. Install NLTK data

```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('omw-1.4')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
```

On macOS you might have this

```python
[nltk_data] Error loading punkt: <urlopen error [SSL:
[nltk_data]     CERTIFICATE_VERIFY_FAILED] certificate verify failed:
[nltk_data]     unable to get local issuer certificate (_ssl.c:1124)>
```

Resolvable with

```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

4. Setup environment

```bash
$ sh setup_scripts/01.prepare_environment.sh
```

## Command details

```bash
Usage: salton [OPTIONS] COMMAND [ARGS]...

  Salton: A thematic information retrieval system

Options:
  --help  Show this and exit

Commands:
  fetch       Fetch papers from CORE repository
  preprocess  Preprocess fetched papers
  index       Build the index
  search      Search papers
  stats       Show statistics
  benchmark   Run benchmarks (experimental)
```

### Usage

The project builds salton locally for command line running.

To fetch papers (100 by default):

```bash
$ salton fetch -l [number of papers]
```

E.g.:

```bash
$ salton fetch -l 500
```

To proprocess papers:

```bash
$ salton preprocess [--wsd]
```

`--wsd`: enables word sense disambiguation (off by default)

> [!NOTE]
> The word sense disambiguation computes similarity between word senses and compares each term against multiple context. This quadratic operation can be highly time consuming.

To build the index:

```bash
$ salton index
```

To search for papers:

```bash
$ salton search -q "[your query]" -l [number of results]
```

E.g.:

```bash
$ salton search -q "cloud computing" -l 10
```

To view some statistics:

```bash
$ salton stats

Index statistics:
• Documents indexed: 8
• Unique terms: 3510
• Index size: 1.58 MB

Data statistics:
• Raw papers: 0
• Processed papers: 0

Benchmark statistics:
• Available query sets: 0
```

## Evaluation

### Setup benchmarks
To run benchmarks, you'll need aset of test queries in the `evaluation` directory:
   - `query_natural_lang.txt`: natural language queries
   - `query_natural_lang.txt`: natural language queries
   - `query_benchmark.txt`: structured queries
   - `query_relevance.txt`: relevance data

### Benchmark metrics
The currently supported metrics are precision, recall, NDCG, MAP.

To run benchmarks:

```bash
$ salton benchmark [--save/--no-save] [--detailed/--simple]
```

`--save/--no-save`: saves results to file (default: save)

`--detailed/--simple`: shows detailed results (default: simple)


## Results

```bash
$ salton search -q "cloud computing" -l 3

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
