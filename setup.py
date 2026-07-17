from setuptools import setup, find_packages

setup(
    name="x-space-downloader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "yt-dlp>=2024.0.0",
        "click>=8.0.0",
        "requests>=2.31.0",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "x-space-dl=src.main:cli",
        ],
    },
    python_requires=">=3.8",
)
