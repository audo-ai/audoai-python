import json
from io import BufferedIOBase
from os.path import basename, isfile
from typing import Union, Callable

from audoai.common import BaseAudoClient, MalformedFile, NoiseRemovalFailed, \
    try_get_json, AudoException, InsufficientCredits
from audoai.noise_removal.wav_audio_result import WavAudioResult
from websocket import create_connection


class NoiseRemovalClient(BaseAudoClient):
    """Client to remove noise from audio files"""

    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)

    def process(
        self,
        input: Union[str, BufferedIOBase],
        input_extension: str = None,
        output_extension: str = None,
        output: str = None,
        on_update: Callable[[dict], None] = lambda x: print(x)
    ) -> WavAudioResult:
        """
        Remove non-speech noise from an audio file

        Args:
            input: A filename, binary file-object, or a URL pointing to the audio input
            input_extension: Extension (ie. ".wav") of file (only needed with file object)
            output_extension: Extension (ie. ".wav") of output file. Audio will be transcoded
            output: Optional URL to perform a PUT request with output audio
            on_update: Function called with every new dict update object while in_progress or queued
        Returns:
            result: An object containing a reference to the processed audio file
        """
        if isinstance(input, BufferedIOBase) or isfile(input):
            on_update({'state': 'uploading'})
            job_input = self.upload(input, input_extension)
        else:
            job_input = str(input)
            if not job_input.startswith("http"):
                raise TypeError(
                    "input argument must be a filename, a binary file object, or a URL"
                )
        on_update({'state': 'creating_job'})
        job_id = self.create_job(job_input, output_extension, output)
        return self.wait_for_job_id(job_id, on_update)

    def upload(
        self,
        file: Union[str, BufferedIOBase],
        input_extension: str = None,
    ) -> str:
        """
        Uploads an audio file for future processing. Returns a fileId that can be used later.

        Args:
            file: Either a filename or a file object opened in binary mode
            input_extension: Extension (ie. ".wav") of file if a file object is provided
        Returns:
            job_id: A string representing the noise removal job id
        """
        if isinstance(file, str):
            file_name = basename(file)
            file = open(file, 'rb')
            on_exit = file.close
            if input_extension is not None and not file_name.endswith('.' + input_extension.strip('.')):
                raise TypeError('Extension does not match provided file extension.')
        elif isinstance(file, BufferedIOBase):
            if input_extension is None:
                raise TypeError('Must specify input_extension when passing raw file')
            file_name = 'file.{}'.format(input_extension.strip('.'))
            on_exit = lambda: None
        else:
            raise TypeError('Unknown object passed as file argument')
        try:
            return self.request(
                'post',
                '/upload',
                files=dict(file=(file_name, file)),
                on_code={
                    422: lambda r: MalformedFile(try_get_json(r, 'detail'))
                }
            )['fileId']
        finally:
            on_exit()

    def create_job(
        self,
        input: str,
        output_extension: str = None,
        output: str = None
    ) -> str:
        """
        Create a job to remove non-speech noise from an audio file

        Args:
            input: Either a fileId from upload() or a URL of an audio file
            output_extension: Extension (ie. ".wav") of output file. Audio will be transcoded
            output: Optional URL to perform a PUT request with output audio
        Returns:
            job_id: A string representing the noise removal job id
        """
        return self.request(
            'post',
            '/remove-noise',
            json=dict(input=input, outputExtension=output_extension, output=output),
            on_code={
                400: lambda r: InsufficientCredits(try_get_json(r, 'detail'))
            }
        )['jobId']

    def get_status(self, job_id: str) -> dict:
        return self.request('get', '/remove-noise/{}/status'.format(job_id))

    def wait_for_job_id(self, job_id: str, on_update: Callable[[dict], None] = lambda x: print(x)) -> WavAudioResult:
        """
        Wait for a noise removal job id to finish and return the result
        or raise an exception if processing fails

        Args:
            job_id: Job id from create_job to monitor
            on_update: Function called with every new dict update object while in_progress or queued
        Returns:
            result: Audio result of job
        """
        wss_base = self.base_url.replace("http://", "ws://")
        wss_base = wss_base.replace("https://", "wss://")
        wss_url = wss_base + "/wss/remove-noise/{}/status".format(job_id)
        auth_header = {'x-api-key': self.api_key}
        websocket = create_connection(wss_url, header=auth_header)
        try:
            for status_str in websocket:
                try:
                    status = json.loads(status_str)
                except ValueError:
                    raise AudoException("Malformed response from server during websocket communication")
                except OSError:
                    raise AudoException("Network error while communicating to backend")

                state = status['state']
                if state in ['downloading', 'in_progress', 'queued']:
                    if on_update:
                        on_update(status)
                elif state == 'failed':
                    raise NoiseRemovalFailed(status.get('reason', ''))
                elif state == 'succeeded':
                    return WavAudioResult(self.base_url + status['downloadPath'])
                else:
                    raise AudoException("Server replied with unknown status: {}".format(status))
        finally:
            websocket.close()
