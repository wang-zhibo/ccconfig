#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Author: gm.zhibo.wang
# E-mail: gm.zhibo.wang@gmail.com
# Date  :
# Desc  : ccconfig is a lightweight configuration management library for Python.

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='ccconfig',
    version="0.0.1",
    author='gm.zhibo.wang',
    author_email='gm.zhibo.wang@gmail.com',
    description='Lightweight configuration management library for Python',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/wang-zhibo/ccconfig',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    keywords="configuration config python settings environment ini yaml",  # 根据需要添加
    install_requires=[
        'PyYAML==6.0.1',
    ],
    project_urls={
        "Bug Reports": "https://github.com/wang-zhibo/ccconfig/issues",
        "Source": "https://github.com/wang-zhibo/ccconfig",
    },
)



