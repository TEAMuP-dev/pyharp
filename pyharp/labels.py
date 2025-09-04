from dataclasses import dataclass, field
from typing import List, Union, Dict


__all__ = [
    'OutputLabel',
    'AudioLabel',
    'SpectrogramLabel',
    'MidiLabel',
    'LabelList'
]

@dataclass
class OutputLabel:
    t: float
    label: str
    duration: float = 0.0
    description: str = None
    color: int = 0
    link: str = None

    def __post_init__(self):
        self.label_type = self.__class__.__name__

    @staticmethod
    def hex_color_to_int(hex, a=0.5):
        return (round(a * 255) << 24) + int(hex.strip('#'), 16)

    @staticmethod
    def rgb_color_to_int(r, g, b, a=0.5):
        return (round(a * 255) << 24) + (r << 16) + (g << 8) + b

@dataclass
class AudioLabel(OutputLabel):
    amplitude: float = None

@dataclass
class SpectrogramLabel(OutputLabel):
    frequency: float = None

@dataclass
class MidiLabel(OutputLabel):
    pitch: float = None

LabelUnion = Union[AudioLabel, SpectrogramLabel, MidiLabel, OutputLabel]

@dataclass
class LabelList:
    meta: Dict[str, str] = field(default_factory = dict)
    labels: List[LabelUnion] = field(default_factory = list)

    def __post_init__(self):
        # Add meta._type to match Gradio components
        # (e.g., for gr.File meta._type = "gradio.FileData")
        self.meta = {
            "_type": f"pyharp.{self.__class__.__name__}"
        }

    def append(self, label):
        self.labels.append(label)
