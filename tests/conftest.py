import pytest
from app import app as flask_instance  # Rename the import to avoid confusion

@pytest.fixture
def app():
    """Provides the Flask app instance."""
    flask_instance.config.update({
        "TESTING": True,
    })
    yield flask_instance

@pytest.fixture
def client(app):
    # This provides the test client for making requests
    return app.test_client()

@pytest.fixture
def client(app):
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

