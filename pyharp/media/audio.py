from .utils import *

import audiotools


__all__ = [
    'load_audio',
    'save_audio'
]

def load_audio(input_audio_path):
    """
    Loads audio at a specified path using audiotools (Descript).

    Args:
        input_audio_path (str): the audio filepath to load.

    Returns:
        signal (audiotools.AudioSignal): wrapped audio signal.
    """

    signal = audiotools.AudioSignal(input_audio_path)

    return signal

def save_audio(signal, output_audio_path=None, include_timestamp=False) -> str:
    """
    Saves audio to a specified path using audiotools (Descript).

    Args:
        signal (audiotools.AudioSignal): wrapped audio signal.
        output_audio_path (str): the filepath to use to save the audio.
        include_timestamp (bool): whether to include a timestamp in the filename.

    Returns:
        output_audio_path (str): the filepath of the saved audio.
    """

    assert isinstance(signal, audiotools.AudioSignal), \
        "Default loading only supports instances of audiotools.AudioSignal."

    if output_audio_path is None:
        output_audio_path = get_default_path(ext=".wav")

    if include_timestamp:
        output_audio_path = add_timestamp_to_path(output_audio_path)

    signal.write(output_audio_path)

    return output_audio_path
