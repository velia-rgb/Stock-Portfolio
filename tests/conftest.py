import uuid
import pytest
from app import app as flask_instance
from models import create_user, create_portfolio_db

@pytest.fixture
def app():
    """Provides the Flask app instance."""
    flask_instance.config.update({
        "TESTING": True,
    })
    yield flask_instance

@pytest.fixture
def client(app):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def test_user():
    username = f"testuser_{uuid.uuid4().hex}"
    password = "testpass"
    user = create_user(username, password)
    create_portfolio_db(user.id, f"{username}'s Portfolio", 10000.0)
    return {"username": username, "password": password, "id": user.id}

@pytest.fixture
def logged_in_client(client, test_user):
    response = client.post("/login", data={
        "username": test_user["username"],
        "password": test_user["password"],
    })
    assert response.status_code == 302
    return client

