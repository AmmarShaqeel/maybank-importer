from setuptools import setup, find_packages

setup(
    name="maybank_importer",
    version="0.1.0",
    description="An importer for Maybank card PDF statements",
    author="Ammar Shaqeel",
    url="https://github.com/ammarshaqeew/maybank-importer",
    packages=find_packages(),
    install_requires=[
        "beancount>=3.0.0",
        "python-dateutil>=2.8.0",
        "beangulp>=0.2.0",
    ],
    python_requires=">=3.7",
    keywords="beancount, finance, accounting, pdf, import",
)
