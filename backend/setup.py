from setuptools import setup, find_packages

setup(
    name="bearme-coffee-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.27.0",
        "python-multipart>=0.0.9",
        "openpyxl>=3.1.2",
        "PyMySQL>=1.1.0",
        "pydantic>=2.6.0",
        "pydantic-settings>=2.2.0",
    ],
)