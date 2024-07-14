import pytest
from pydantic import AnyUrl
from bs4 import BeautifulSoup
from models import Request, Response


@pytest.fixture
def dummy_callback() -> None:
    def inner():
        pass

    return inner


@pytest.fixture
def valid_url():
    return "https://example.com"


@pytest.fixture
def valid_request(valid_url, dummy_callback):
    return Request(url=valid_url, callback=dummy_callback)


def test_request_creation(valid_url, dummy_callback):
    request = Request(url=valid_url, callback=dummy_callback)
    assert request.url == AnyUrl(valid_url)
    assert request.callback == dummy_callback
    assert request.method == "GET"
    assert request.headers is None
    assert request.params is None
    assert request.data is None
    assert request.json is None
    assert request.content_type == "text"
    assert request.client is None


def test_request_optional_fields(valid_url, dummy_callback):
    headers = {"User-Agent": "pytest"}
    params = {"q": "test"}
    data = {"key": "value"}
    json_data = {"json_key": "json_value"}
    client = "test_client"
    request = Request(
        url=valid_url,
        callback=dummy_callback,
        method="POST",
        headers=headers,
        params=params,
        data=data,
        json=json_data,
        content_type="json",
        client=client,
    )
    assert request.method == "POST"
    assert request.headers == headers
    assert request.params == params
    assert request.data == data
    assert request.json == json_data
    assert request.content_type == "json"
    assert request.client == client


def test_response_creation(valid_request):
    data = "<html></html>"
    response = Response(request=valid_request, data=data)
    assert response.request == valid_request
    assert response.data == data


def test_response_soup_property(valid_request):
    html_data = "<html><body><p>Hello, world!</p></body></html>"
    response = Response(request=valid_request, data=html_data)
    assert isinstance(response.soup, BeautifulSoup)
    assert response.soup.find("p").text == "Hello, world!"


def test_response_soup_property_with_dict(valid_request):
    json_data = {"key": "value"}
    response = Response(request=valid_request, data=json_data)
    with pytest.raises(Warning, match="Cannot create BeautifulSoup from dict."):
        _ = response.soup
