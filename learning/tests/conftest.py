import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def set_env():
    os.environ["NEBIUS_API_KEY"] = "test-dummy"
