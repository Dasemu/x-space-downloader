from setuptools import setup, find_packages

setup(
    name="x-space-downloader",
    version="0.1.0",
    description="Download X (Twitter) Space recordings as MP4 replays or MP3 audio",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Dasemu/x-space-downloader",
    author="Dario Sevilla",
    license="MIT",
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
