"""Test configuration and fixtures."""
import pytest
from app.core.scanner import Scanner
from app.core.patcher import Patcher
from app.core.validator import Validator

@pytest.fixture
def scanner():
    return Scanner()

@pytest.fixture
def patcher():
    return Patcher()

@pytest.fixture
def validator():
    return Validator()
