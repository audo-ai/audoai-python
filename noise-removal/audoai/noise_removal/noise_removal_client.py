import json
from io import BufferedIOBase
from os.path import basename
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
        file: Union[str, BufferedIOBase],
        input_extension: str = None,
        output_extension: str = '.wav',
        on_update: Callable[[dict], None] = lambda _: None
    ):
        """
        Remove non-speech noise from an audio file

        Args:
            file: Either a filename or a file object opened in binary mode
            input_extension: Extension (ie. ".wav") of file if a file object is provided
            output_extension: Extension (ie. ".wav") of output file. Audio will be transcoded
            on_update: Function called with every new dict update object while in_progress or queued
        Returns:
            result: An object containing a reference to the processed audio file
        """
        job_id = self.create_job(file, input_extension, output_extension)
        return self.wait_for_job_id(job_id, on_update)

    def create_job(
        self,
        file: Union[str, BufferedIOBase],
        input_extension: str = None,
        output_extension: str = '.wav'
    ) -> str:
        """
        Create a job to remove non-speech noise from an audio file

        Args:
            file: Either a filename or a file object opened in binary mode
            input_extension: Extension (ie. ".wav") of file if a file object is provided
            output_extension: Extension (ie. ".wav") of output file. Audio will be transcoded
        Returns:
            job_id: A string representing the noise removal job id
        """
        if isinstance(file, str):
            file_name = basename(file)
            file = open(file, 'rb')
            on_exit = file.close
            if input_extension is not None and not file_name.endswith('.' + input_extension.strip('.')):
                raise ValueError('Extension does not match provided file extension.')
        elif isinstance(file, BufferedIOBase):
            file_name = 'file.{}'.format(input_extension.strip('.'))
            on_exit = lambda: None
        else:
            raise TypeError('Unknown object passed as file argument')
        try:
            return self.request(
                'post',
                '/remove-noise',
                files=dict(file=(file_name, file)),
                on_code={
                    422: lambda r: MalformedFile(try_get_json(r, 'detail')),
                    400: lambda r: InsufficientCredits(try_get_json(r, 'detail'))
                },
                params={'output_ext': output_extension}
            )['jobId']
        finally:
            on_exit()

    def get_status(self, job_id: str) -> dict:
        return self.request('get', '/remove-noise/{}/status'.format(job_id))

    def wait_for_job_id(self, job_id: str, on_update: Callable[[dict], None] = lambda _: None) -> WavAudioResult:
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
                if state in ['in_progress', 'queued']:
                    on_update(status)
                elif state == 'failed':
                    raise NoiseRemovalFailed(status.get('reason', ''))
                elif state == 'succeeded':
                    return WavAudioResult(self.base_url + status['processedPath'])
                else:
                    raise AudoException("Server replied with unknown status: {}".format(status))
        finally:
            websocket.close()
