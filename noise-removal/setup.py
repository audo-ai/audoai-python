from setuptools import setup

setup(
    name='audoai-noise-removal',
    version='1.1.0',
    description='Python client for Audo AI noise removal APIs',
    url='https://github.com/audo-ai/audoai-python',
    author='Audo AI',
    author_email='info@audo.ai',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='audoai',
    packages=['audoai.noise_removal'],
    install_requires=[
        'audoai-common>=0.2.0',
        'websocket_client'
    ],
    extras_require={
        'test': ['pytest']
    }
)
