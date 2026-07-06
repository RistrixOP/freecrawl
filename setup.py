from setuptools import setup, find_packages

setup(
    name="freecrawl",
    version="1.0.0",
    description="Open-source web scraping API with anti-bot bypass",
    author="Richard Gschwend",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "patchright>=1.49.0",
        "trafilatura>=1.12.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "httpx>=0.27.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.0.0",
        "python-multipart>=0.0.9",
        "pydantic>=2.0.0",
    ],
    entry_points={"console_scripts": ["freecrawl=freecrawl.cli:main"]},
    python_requires=">=3.10",
)
