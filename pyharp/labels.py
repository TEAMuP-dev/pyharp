from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


__all__ = [
    'OutputLabel',
    'AudioLabel',
    'MidiLabel',
    'LabelList'
]

@dataclass
class OutputLabel:
    t: float
    label: str
    duration: float = 0.0
    description: Optional[str] = None
    color: int = 0
    link: Optional[str] = None

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
    amplitude: Optional[float] = None

@dataclass
class MidiLabel(OutputLabel):
    pitch: Optional[float] = None

LabelUnion = Union[AudioLabel, MidiLabel, OutputLabel]

@dataclass
class LabelList:
    meta: Dict[str, str] = field(default_factory = dict)
    labels: List[LabelUnion] = field(default_factory = list)

    def __post_init__(self):
        # Anything the caller put in meta is kept, with _type added to match Gradio
        # components (e.g., for gr.File meta._type = "gradio.FileData"). Set last, so
        # that it cannot be overwritten: HARP reads it to tell the output apart.
        self.meta = {
            **self.meta,
            "_type": f"pyharp.{self.__class__.__name__}"
        }

    def append(self, label):
        self.labels.append(label)
