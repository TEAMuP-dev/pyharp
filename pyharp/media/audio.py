from pathlib import Path

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


def save_audio(signal, output_audio_path=None):
    """
    Saves audio to a specified path using audiotools (Descript).

    Args:
        signal (audiotools.AudioSignal): wrapped audio signal.
        output_audio_path (str): the filepath to use to save the audio.

    Returns:
        output_audio_path (str): the filepath of the saved audio.
    """

    assert isinstance(signal, audiotools.AudioSignal), "Default loading only supports instances of audiotools.AudioSignal."

    if output_audio_path is None:
        output_dir = Path("_outputs")
        output_dir.mkdir(exist_ok=True)
        output_audio_path = output_dir / "output.wav"
        output_audio_path = output_audio_path.absolute().__str__()

    signal.write(output_audio_path)

    return signal.path_to_file