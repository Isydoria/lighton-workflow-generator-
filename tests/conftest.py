"""
Configuration pytest pour les tests
"""

import pytest


def pytest_configure(config):
    """Configuration des markers personnalisés"""
    config.addinivalue_line("markers", "paradigm: Tests pour Paradigm API")
    config.addinivalue_line("markers", "workflow: Tests pour Workflow API")
    config.addinivalue_line("markers", "files: Tests pour Files API")
    config.addinivalue_line("markers", "integration: Tests d'intégration")
    config.addinivalue_line("markers", "security: Tests de sécurité")
    config.addinivalue_line("markers", "slow: Tests lents (> 10 secondes)")


@pytest.fixture(scope="session")
def anyio_backend():
    """Backend pour tests asynchrones"""
    return "asyncio"
