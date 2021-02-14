from io import BufferedIOBase
from os.path import basename
from time import sleep
from typing import Union

from audoai.common import BaseAudoClient, MalformedFile, NoiseRemovalFailed, \
    try_get_json, AudoException
from audoai.noise_removal.wav_audio_result import WavAudioResult


class NoiseRemovalClient(BaseAudoClient):
    """Client to remove noise from audio files"""
    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)

    def process(self, file: Union[str, BufferedIOBase], extension: str = None, poll_interval: float = 0.5):
        """
        Remove non-speech noise from an audio file

        Args:
            file: Either a filename or a file object opened in binary mode
            extension: Extension (ie. ".wav") of file if a file object is provided
        Returns:
            result: An object containing a reference to the processed audio file
        """
        job_id = self.create_job(file, extension)
        return self.wait_for_job_id(job_id, poll_interval)

    def create_job(self, file: Union[str, BufferedIOBase], extension: str = None) -> str:
        """
        Create a job to remove non-speech noise from an audio file

        Args:
            file: Either a filename or a file object opened in binary mode
            extension: Extension (ie. ".wav") of file if a file object is provided
        Returns:
            job_id: A string representing the noise removal job id
        """
        if isinstance(file, str):
            file_name = basename(file)
            file = open(file, 'rb')
            on_exit = file.close
            if extension is not None and not file_name.endswith('.' + extension.strip('.')):
                raise ValueError('Extension does not match provided file extension.')
        elif isinstance(file, BufferedIOBase):
            file_name = 'file.{}'.format(extension.strip('.'))
            on_exit = lambda: None
        else:
            raise TypeError('Unknown object passed as file argument')
        try:
            return self.request(
                'post',
                '/remove-noise',
                files=dict(file=(file_name, file)),
                on_code={
                    422: lambda r: MalformedFile(try_get_json(r, 'detail'))
                }
            )['jobId']
        finally:
            on_exit()

    def get_status(self, job_id: str) -> dict:
        return self.request('get', '/remove-noise/{}/status'.format(job_id))

    def wait_for_job_id(self, job_id: str, poll_interval: float = 0.5) -> WavAudioResult:
        """
        Wait for a noise removal job id to finish and return the result
        or raise an exception if processing fails

        Args:
            job_id: Job id from create_job to monitor
            poll_interval: How long in seconds to wait before checking for updates
        Returns:
            result: Audio result of job
        """
        while True:
            status = self.get_status(job_id)
            state = status['state']
            if state in ['in_progress', 'queued']:
                sleep(poll_interval)
            elif state == 'failed':
                raise NoiseRemovalFailed(status.get('reason', ''))
            elif state == 'succeeded':
                return WavAudioResult(status['processedUrl'])
            else:
                raise AudoException("Server replied with unknown status: {}".format(status))
