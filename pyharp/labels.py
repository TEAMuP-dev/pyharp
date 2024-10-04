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

    def __post_init__(self):
        self.label_type = self.__class__.__name__

    def set_color(self, r, g, b, a):
        self.color = (a << 24) + (r << 16) + (g << 8) + b
        print(f"Color: {self.color}")


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
        # (e.g. for gr.File meta._type = "gradio.FileData")
        self.meta = {
            "_type": f"pyharp.{self.__class__.__name__}"
        }

    def append(self, label):
        self.labels.append(label)

    def __iter__(self):
        return iter(self.labels)

    def __getitem__(self, item):
        return self.labels[item]

    def __len__(self):
        return len(self.labels)