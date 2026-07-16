import logging
import pytest

@pytest.fixture(scope="session", autouse=True)
def shutdown_logging_on_exit():
    yield
    # Close and release all logging file handlers to prevent ResourceWarning leaks
    logging.shutdown()
