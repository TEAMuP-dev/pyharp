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

    def __post_init__(self):
        self.label_type = self.__class__.__name__


@dataclass
class AudioLabel(OutputLabel):
    amplitude: float = 0.0


@dataclass
class SpectrogramLabel(OutputLabel):
    frequency: float = 440.0


@dataclass
class MidiLabel(OutputLabel):
    pitch: float = 69


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
