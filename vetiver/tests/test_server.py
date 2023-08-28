from vetiver import mock, VetiverModel, VetiverAPI
from pydantic import BaseModel, conint
from fastapi.testclient import TestClient
import numpy as np
import pytest
import sys

np.random.seed(500)


@pytest.fixture
def vetiver_model():
    X, y = mock.get_mock_data()
    model = mock.get_mock_model().fit(X, y)
    v = VetiverModel(
        model=model,
        prototype_data=X,
        model_name="my_model",
        versioned=None,
        description="A regression model for testing purposes",
    )
    return v


@pytest.fixture
def client(vetiver_model):
    app = VetiverAPI(vetiver_model)

    return TestClient(app.app)


@pytest.fixture
def complex_prototype_model():
    class CustomPrototype(BaseModel):
        B: conint(gt=42)
        C: conint(gt=42)
        D: conint(gt=42)

    X, y = mock.get_mock_data()
    model = mock.get_mock_model().fit(X, y)
    v = VetiverModel(
        model=model,
        prototype_data=CustomPrototype.model_construct(),
        model_name="my_model",
        versioned=None,
        description="A regression model for testing purposes",
    )
    # dont actually want to make predictions, just for looking at schema
    app = VetiverAPI(v, check_prototype=False)

    return TestClient(app.app)


def test_get_ping(client):
    response = client.get("/ping")
    assert response.status_code == 200, response.text
    assert response.json() == {"ping": "pong"}


def test_get_docs(client):
    response = client.get("/__docs__")
    assert response.status_code == 200, response.text


def test_get_metadata(client):
    response = client.get("/metadata")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "user": {},
        "version": None,
        "url": None,
        "required_pkgs": ["scikit-learn"],
        "python_version": list(sys.version_info),  # JSON will return a list
    }


def test_get_prototype(client):
    response = client.get("/prototype")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "properties": {
            "B": {"default": 88, "title": "B", "type": "integer"},
            "C": {"default": 67, "title": "C", "type": "integer"},
            "D": {"default": 28, "title": "D", "type": "integer"},
        },
        "title": "prototype",
        "type": "object",
    }


def test_complex_prototype(complex_prototype_model):
    response = complex_prototype_model.get("/prototype")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "properties": {
            "B": {"exclusiveMinimum": 42, "title": "B", "type": "integer"},
            "C": {"exclusiveMinimum": 42, "title": "C", "type": "integer"},
            "D": {"exclusiveMinimum": 42, "title": "D", "type": "integer"},
        },
        "required": ["B", "C", "D"],
        "title": "CustomPrototype",
        "type": "object",
    }
