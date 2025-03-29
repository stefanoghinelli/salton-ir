from setuptools import setup, find_packages

setup(
    name="salton",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "Whoosh==2.7.4",
        "nltk==3.8.1",
        "pdftotext==3.0.0",
        "lxml==4.9.3",
        "requests==2.31.0",
        "click==8.1.7",
    ],
    entry_points={
        'console_scripts': [
            'salton=src.cli:main',
        ],
    },
    python_requires=">=3.8",
)