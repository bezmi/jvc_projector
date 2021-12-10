import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jvc_projector_remote",
    version="0.1.0",
    author="bezmi",
    description="A small package to control jvc projectors over IP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bezmi/jvc_projector",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
