from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as ver:
    version_info = ver.read().strip()

setup(
    name='cinverman',
    version=version_info,
    author="",
    author_email="",
    description='CinCan Version Manager: a tool for listing available CinCan tools, their versions and possible updates.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/cincan/cincan-registry",
    packages=['cinverman'],
    install_requires=['docker>=4.1'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['cinverman=cinverman.__main__:main'],
    },
    python_requires='>=3.6',
)
