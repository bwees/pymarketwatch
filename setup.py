import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="pymarketwatch",
    version="1.4.0",
    description="API to interact with MarketWatch's Stock Market Game API",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/bwees/pymarketwatch",
    author="bwees",
    author_email="brandonwees@gmail.com",
    license="Apache 2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["pymarketwatch"],
    include_package_data=True,
    install_requires=["beautifulsoup4", "requests"]
)
