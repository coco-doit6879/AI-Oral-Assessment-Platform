import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from engine import Engine, canonical_words, inputs, word_chunks


def test_engine_uses_torch_default_parallelism(monkeypatch, tmp_path):
    # A minimal torch adapter deliberately has no thread-setting API.
    torch = SimpleNamespace(load=lambda *args, **kwargs: {})
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setenv("GOPT_ASSETS", str(tmp_path))
    monkeypatch.setattr("engine.phone_inventory", lambda path: ({}, {}, {}))
    monkeypatch.setattr("engine.read_lexicon", lambda path: {})
    (tmp_path / "training_phones.json").write_text(json.dumps({str(i): i for i in range(39)}))
    (tmp_path / "manifest.json").write_text(json.dumps({"gopt_revision": "test"}))
    (tmp_path / "gopt_model.py").write_text(
        "class GOPT:\n"
        "    def __init__(self, **kwargs): pass\n"
        "    def load_state_dict(self, state, strict): assert strict\n"
        "    def eval(self): self.evaluating = True\n")
    engine = Engine()
    assert engine.torch is torch and engine.model.evaluating


def test_normalization_matches_training_and_does_not_normalize_padding():
    features = np.full((2, 84), 7.248)
    padded, phones = inputs(features, [4, 12])
    np.testing.assert_allclose(padded[0, :2], 1, rtol=1e-5)
    assert np.count_nonzero(padded[0, 2:]) == 0
    assert phones[0, :3].tolist() == [4, 12, -1]


@pytest.mark.parametrize("features,phones", [(np.zeros((51, 84)), [1] * 51),
    (np.full((1, 84), np.nan), [1]), (np.zeros((1, 78)), [1]), (np.zeros((1, 84)), [39])])
def test_invalid_model_inputs_rejected(features, phones):
    with pytest.raises(ValueError):
        inputs(features, phones)


def test_long_answers_keep_every_word_and_respect_phone_context():
    lexicon = {"HELLO": ["HH", "AH0", "L", "OW1"], "WORLD": ["W", "ER1", "L", "D"]}
    words = ["HELLO", "WORLD"] * 30
    chunks = word_chunks(words, lexicon)
    assert [word for chunk in chunks for word in chunk] == words
    assert len(chunks) == 5
    assert all(sum(len(lexicon[word]) for word in chunk) <= 50 for chunk in chunks)


def test_unknown_words_and_mixed_language_are_not_silently_dropped():
    lexicon = {"HELLO": ["HH"], "I'M": ["AY1", "M"]}
    assert canonical_words("Hello, I’m!", lexicon) == ["HELLO", "I'M"]
    for transcript in ("hello 12", "hello unknown", "xin chào", ""):
        with pytest.raises(ValueError):
            canonical_words(transcript, lexicon)
