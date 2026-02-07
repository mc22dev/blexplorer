import pytest
from blescanner.tools.audio_analyzer.audio_analyzer import AudioAnalyzerScreen, SpectrumGraph

def test_audio_analyzer_instantiation():
    screen = AudioAnalyzerScreen()
    assert screen.name == ""
    assert not screen.is_running

def test_spectrum_graph_instantiation():
    graph = SpectrumGraph()
    assert graph.is_log_x
    assert graph.is_log_y
