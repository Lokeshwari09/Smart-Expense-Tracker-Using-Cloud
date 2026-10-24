import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import app as tracker  # noqa: E402


@pytest.fixture()
def client():
    tracker.init_db()
    return tracker.app.test_client()


def add(client, **kw):
    return client.post("/api/expenses", json=kw)


def test_health(client):
    assert client.get("/health").get_json()["status"] == "ok"


def test_auto_category():
    assert tracker.auto_category("Swiggy dinner") == "Food"
    assert tracker.auto_category("Uber to office") == "Transport"
    assert tracker.auto_category("random thing") == "Other"


def test_add_list_delete(client):
    r = add(client, description="Netflix", amount=649)
    assert r.status_code == 201 and r.get_json()["category"] == "Entertainment"
    items = client.get("/api/expenses").get_json()
    assert any(i["description"] == "Netflix" for i in items)
    assert client.delete(f"/api/expenses/{r.get_json()['id']}").status_code == 200
    assert client.delete("/api/expenses/999999").status_code == 404


def test_validation(client):
    assert add(client, description="x", amount="abc").status_code == 400
    assert add(client, description="", amount=10).status_code == 400
    assert add(client, description="x", amount=-5).status_code == 400
    assert add(client, description="x", amount=5, spent_on="bad").status_code == 400


def test_summary_and_budget_alert(client):
    assert client.post("/api/budget", json={"budget": 100}).status_code == 200
    add(client, description="Big shopping amazon", amount=500)
    s = client.get("/api/summary").get_json()
    assert s["budget"] == 100 and s["total"] >= 500
    assert s["alert"].startswith("Over budget")
    assert any(c["category"] == "Shopping" for c in s["by_category"])


def test_csv_and_backup(client):
    csv_text = client.get("/api/export.csv").get_data(as_text=True)
    assert csv_text.startswith("id,description,amount,category,spent_on")
    assert "disabled" in client.post("/api/backup").get_json()["result"]
