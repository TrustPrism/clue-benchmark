import pytest

from clue_benchmark import Config, generate


@pytest.fixture(scope="session")
def case():
    result = generate(Config(), 42)
    assert result["status"] == "ok"
    return result["case"]
