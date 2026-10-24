from pathlib import Path

import pytest

from corpus.generate import generate


@pytest.fixture(scope="session")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("corpus")
    generate(out)
    return out
