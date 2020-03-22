#!/bin/env python3

from setuptools import setup, find_packages

setup(
    name='nmp',
    version='0.0.1',
    author='RainMark',
    author_email='rain.by.zhou@gmail.com',
    description='Network Multistage Pxxxx/Net Manager Project',
    url='https://github.com/Project-Nmp/nmp',
    classifiers=[
        'Operating System :: Unix',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
    ],

    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires = [
        'werkzeug==0.16.1',
        'pysnooper>=0.3.0',
        'requests>=2.23.0',
        'flask-restplus >= 0.13.0',
    ],

    entry_points={
        'console_scripts':[
            'nmp = nmp.main:main'
        ]
    },
)
