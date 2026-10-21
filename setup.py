from setuptools import setup, find_packages

setup(
    name="context-aware-test-migration",
    version="1.0.0",
    description="Context-Aware LLM Framework for Automated Test Script Generation and Cross-Framework Migration",
    author="Anand Rawat",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flask>=3.0.0",
        "requests>=2.31.0",
        "playwright>=1.40.0",
        "selenium>=4.15.0",
        "pytest>=8.0.0",
        "scipy>=1.11.0",
        "numpy>=1.24.0",
    ],
    python_requires=">=3.10",
)
