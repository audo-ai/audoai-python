import os
import wave
from io import BytesIO, BufferedIOBase
from tempfile import NamedTemporaryFile

import pytest
from audoai.noise_removal import NoiseRemovalClient


@pytest.fixture()
def noise_removal() -> NoiseRemovalClient:
    api_key = os.environ['AUDO_API_KEY']
    base_url = os.environ['AUDO_BASE_URL']
    noise_removal = NoiseRemovalClient(api_key, base_url)
    return noise_removal


@pytest.fixture()
def silence_fileobject() -> BufferedIOBase:
    channels = 1
    sample_rate = 44100
    seconds = 4.0
    wav_data = BytesIO(bytes())
    with wave.open(wav_data, "wb") as wf:
        wf.setparams((1, channels, sample_rate, 0, "NONE", "not compressed"))
        wf.writeframes(b"\0" * int(sample_rate * seconds * channels))
    wav_data.seek(0)
    return wav_data


def test_process_fileobject(
    noise_removal: NoiseRemovalClient,
    silence_fileobject: BufferedIOBase
):
    output = noise_removal.process(silence_fileobject, "wav", output_extension="mp3")
    assert output.url
    with NamedTemporaryFile(suffix=".mp3") as temp:
        output.save(temp.name)

    # Invalid extension
    with pytest.raises(ValueError):
        with NamedTemporaryFile(suffix=".wav") as temp:
            output.save(temp.name)


def test_process_filename(
    noise_removal: NoiseRemovalClient,
    silence_fileobject: BufferedIOBase
):
    with NamedTemporaryFile(suffix=".wav") as temp:
        temp.write(silence_fileobject.read())
        output = noise_removal.process(temp.name)
    assert output.url


def test_process_url(
    noise_removal: NoiseRemovalClient
):
    input_url = "http://dl5.webmfiles.org/big-buck-bunny_trailer.webm"
    output = noise_removal.process(input_url, output_extension="mp4")
    assert output.url


def test_process_invalid(
    noise_removal: NoiseRemovalClient,
    silence_fileobject: BufferedIOBase
):
    with pytest.raises((OSError, TypeError)):
        noise_removal.process('invalid-arg')
