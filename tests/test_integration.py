import pytest
from app import app

class TestConfirm:
# test after clicking on the confirm button, page will go to the holdings url or not
    def test_redirects_to_index_after_confirm(self, client):
        response = client.post("/holdings", data = {"name":"portfolio1","cash-amount":100000})
        assert response.status_code == 302
        assert response.location == "/holdings"

class TestAddPortfolio:
# test when I am at the holdings page, if the added portfolio's name is same with previous one
# what will happen
    def test_duplicate_portfolio_name_shows_error(self, client, store):
        client.post("/holdings", data={"name": "Portfolio1", "cash-amount": "100000"})

        response = client.post("/holdings", data={"name": "Portfolio1", "cash-amount": "50000"})

        assert response.status_code == 200
        assert b"Portfolio name already exists" in response.data
        assert len(store.get_all()) == 1

class TestPageLoading:
    # Test 1: Check that the home page (root) loads correctly
    def test_home_page_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200
        # You can also check for specific text on your home page
        assert b"Welcome" in response.data 

    # Test 2: Check that the portfolio page loads correctly
    def test_portfolio_page_loads(self, client):
        response = client.get("/portfolio")
        assert response.status_code == 200
        # Assuming your portfolio page has a title or header
        assert b"Portfolio" in response.data