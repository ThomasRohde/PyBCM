from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pybcm",
    version="0.1.10",
    description="A Business Capability Modeler built with Python and ttkbootstrap",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="https://github.com/yourusername/pybcm",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "bcm": [
            "static/*",
            "templates/*",
            "*.ico",
            "*.html",
            "*.md"
        ]
    },
    install_requires=[
        "ttkbootstrap>=1.10.1",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "pydantic-ai[logfire]>=0.0.15",
        "jinja2>=3.1.5",
        "python-pptx>=1.0.2",
        "markdown>=3.7",
        "tkinterweb>=3.24.8",
        "fastapi>=0.115.6",
        "uvicorn[standard]>=0.34.0",
        "openpyxl>=3.1.5",
        "pandas>=2.2.3",
        "logfire[sqlite3]>=2.11.0",
        "tkhtmlview>=0.3.1",
    ],
    entry_points={
        "console_scripts": [
            "bcm=bcm:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.11",
)
