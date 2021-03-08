# Audo AI Python Libraries

*Python client libraries for Audo AI APIs*

This repo holds a simple Python client to access Audo AI's APIs. Currently, our only
API is noise removal.

## Usage

Pass your API key to the client constructor (like `NoiseRemovalClient(...)`) and you are good to go:
```python
from audoai.noise_removal import NoiseRemovalClient

noise_removal = NoiseRemovalClient(api_key="abc123")
result = noise_removal.process('my-audio.wav')
print(result.url)
result.save('cleaned-audio.wav')
```

## Installation

Install via PyPI:

```console
pip3 install --upgrade audoai-noise-removal
```

## Contact

We are always open to feedback, suggestions, and improvements. Feel free to reach out
to us [info@audo.ai](mailto:info@audo.ai) or submit an issue/pull-request.
