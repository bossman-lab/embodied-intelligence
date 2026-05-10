"""Setup script for video2robot"""

from setuptools import setup, find_packages

setup(
    name="video2robot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.0",
        "torch>=2.0.0",
        "joblib>=1.3.0",
        "scipy>=1.10.0",
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "video2robot=video2robot.cli:main",
        ]
    },
    python_requires=">=3.10",
)

