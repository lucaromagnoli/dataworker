from contextlib import nullcontext as does_not_raise
from functools import partial, wraps

import pytest
from bs4 import BeautifulSoup
from pydantic import HttpUrl, ValidationError

from dataservice.models import Request, Response
from tests.unit.conftest import ToyClient


@pytest.fixture
def dummy_callback() -> None:
    def inner():
        pass

    return inner


@pytest.fixture
def valid_url():
    return "https://example.com/"


@pytest.fixture
def valid_request(valid_url, dummy_callback):
    return Request(url=valid_url, callback=dummy_callback, client=ToyClient())


@pytest.fixture
def valid_data_request(valid_url, dummy_callback):
    return Request(
        url=valid_url, callback=dummy_callback, client=ToyClient(), content_type="json"
    )


def test_request_creation(valid_url, dummy_callback):
    request = Request(url=valid_url, callback=dummy_callback, client=ToyClient())
    assert request.url == valid_url
    assert request.callback == dummy_callback
    assert request.method == "GET"
    assert request.headers is None
    assert request.params is None
    assert request.form_data is None
    assert request.json_data is None
    assert request.content_type == "text"
    assert isinstance(request.client, ToyClient)


def test_request_optional_fields(valid_url, dummy_callback):
    headers = {"User-Agent": "pytest"}
    params = {"q": "test"}
    data = {"key": "value"}
    json_data = {"json_key": "json_value"}
    request = Request(
        url=valid_url,
        callback=dummy_callback,
        method="POST",
        headers=headers,
        params=params,
        form_data=data,
        json_data=json_data,
        content_type="json",
        client=ToyClient(),
    )
    assert request.method == "POST"
    assert request.headers == headers
    assert request.params == params
    assert request.form_data == data
    assert request.json_data == json_data
    assert request.content_type == "json"
    assert isinstance(request.client, ToyClient)


def test_response_creation(valid_request, valid_url):
    data = "<html></html>"
    response = Response(request=valid_request, text=data, url=valid_url)
    assert response.request == valid_request
    assert response.text == data


def test_response_html_property(valid_request, valid_url):
    html_string = "<html><body><p>Hello, world!</p></body></html>"
    response = Response(request=valid_request, text=html_string, url=valid_url)
    assert isinstance(response.html, BeautifulSoup)
    assert response.html.find("p").text == "Hello, world!"


def test_response_html_property_with_json_content_type(valid_data_request, valid_url):
    json_data = {"key": "value"}
    response = Response(request=valid_data_request, data=json_data, url=valid_url)
    with pytest.raises(
        ValueError,
        match="Cannot create BeautifulSoup object when the Request content type is JSON.",
    ):
        _ = response.html


@pytest.mark.parametrize(
    "url, method, content_type, headers, params, form_data, json_data, client, context",
    [
        (
            "http://example.com",
            "GET",
            "text",
            None,
            None,
            None,
            None,
            ToyClient(),
            does_not_raise(),
        ),
        (
            "http://example.com",
            "GET",
            "text",
            None,
            None,
            {"key": "value"},
            None,
            ToyClient(),
            pytest.raises(ValidationError),
        ),
        (
            "http://example.com",
            "POST",
            "text",
            None,
            None,
            {"key": "value"},
            None,
            ToyClient(),
            does_not_raise(),
        ),
        (
            "http://example.com",
            "POST",
            "text",
            None,
            None,
            None,
            {"key": "value"},
            ToyClient(),
            does_not_raise(),
        ),
        (
            "http://example.com",
            "POST",
            "text",
            None,
            None,
            None,
            None,
            "TestClient",
            pytest.raises(ValidationError),
        ),
        (
            "http://example.com",
            "POST",
            "json",
            None,
            None,
            None,
            None,
            "TestClient",
            pytest.raises(ValidationError),
        ),
    ],
)
def test_request_validation(
    url, method, content_type, headers, params, form_data, json_data, client, context
):
    with context:
        request = Request(
            url=url,
            callback=lambda x: x,
            method=method,
            content_type=content_type,
            headers=headers,
            params=params,
            form_data=form_data,
            json_data=json_data,
            client=client,
        )
        assert request


def test_ser_model_valid_request():
    request = Request(
        url="http://example.com",
        callback=lambda x: x,
        method="GET",
        client=lambda x: x,
    )
    serialized = request.ser_model()
    assert serialized["url"] == "http://example.com/"
    assert serialized["callback"] == "function"
    assert serialized["client"] == "function"
    assert serialized["method"] == "GET"


def test_ser_model_post_request_with_form_data():
    request = Request(
        url="http://example.com",
        callback=lambda x: x,
        method="POST",
        form_data={"key": "value"},
        client=lambda x: x,
    )
    serialized = request.ser_model()
    assert serialized["url"] == "http://example.com/"
    assert serialized["callback"] == "function"
    assert serialized["client"] == "function"
    assert serialized["method"] == "POST"
    assert serialized["form_data"] == {"key": "value"}


def test_ser_model_post_request_with_json_data():
    request = Request(
        url="http://example.com",
        callback=lambda x: x,
        method="POST",
        json_data={"key": "value"},
        client=lambda x: x,
    )
    serialized = request.ser_model()
    assert serialized["url"] == "http://example.com/"
    assert serialized["callback"] == "function"
    assert serialized["client"] == "function"
    assert serialized["method"] == "POST"
    assert serialized["json_data"] == {"key": "value"}


def test_ser_model_invalid_post_request():
    with pytest.raises(ValidationError):
        Request(
            url="http://example.com",
            callback=lambda x: x,
            method="POST",
            client=lambda x: x,
        )


def test_ser_model_invalid_get_request():
    with pytest.raises(ValidationError):
        Request(
            url="http://example.com",
            callback=lambda x: x,
            method="GET",
            form_data={"key": "value"},
            client=lambda x: x,
        )


def sample_callback(response, _):
    return response


def wrapped_callback(response):
    @wraps
    def inner(_):
        return response

    return inner


class ClassBasedCallback:
    def __call__(self, response):
        return response


@pytest.mark.parametrize(
    "callback, expected",
    [
        (sample_callback, "sample_callback"),
        (lambda x: x, "<lambda>"),
        (partial(sample_callback, 1), "sample_callback"),
        (wrapped_callback(sample_callback), "inner"),
        (ClassBasedCallback(), "ClassBasedCallback"),
    ],
)
def test_callback_name(callback, expected):
    request = Request(
        url="http://example.com",
        callback=callback,
        client=lambda x: x,
        method="GET",
        content_type="text",
    )
    assert request.callback_name == expected


def test_response_headers_property(valid_request, valid_url):
    headers = {"Content-Type": "text/html"}
    response = Response(request=valid_request, text="", url=valid_url, headers=headers)
    assert response.headers == headers


@pytest.mark.parametrize(
    "method, params, form_data, json_data, expected_key",
    [
        (
            "GET",
            {"key1": "value1"},
            None,
            None,
            "GET https://example.com/ {'key1': 'value1'}",
        ),
        (
            "POST",
            None,
            {"key1": "value1"},
            None,
            "POST https://example.com/ {'key1': 'value1'}",
        ),
        (
            "POST",
            None,
            None,
            {"key1": "value1"},
            "POST https://example.com/ {'key1': 'value1'}",
        ),
        ("GET", None, None, None, "GET https://example.com/"),
    ],
)
def test_request_unique_key(method, params, form_data, json_data, expected_key):
    request = Request(
        url="https://example.com",
        method=method,
        params=params,
        form_data=form_data,
        json_data=json_data,
        callback=lambda x: x,
        client=lambda x: x,
    )
    assert request.unique_key == expected_key


@pytest.mark.parametrize(
    "req, expected",
    [
        (
            Request(
                url="https://example.com",
                method="GET",
                params={"key1": "value1", "key2": "value2"},
                callback=lambda x: x,
                client=lambda x: x,
            ),
            HttpUrl("https://example.com?key1=value1&key2=value2"),
        ),
        (
            Request(
                url="https://example.com/",
                method="GET",
                params={"key1": "value1", "key2": "value2"},
                callback=lambda x: x,
                client=lambda x: x,
            ),
            HttpUrl("https://example.com?key1=value1&key2=value2"),
        ),
        (
            Request(
                url="https://example.com?key1=value1&key2=value2",
                method="GET",
                callback=lambda x: x,
                client=lambda x: x,
            ),
            HttpUrl("https://example.com?key1=value1&key2=value2"),
        ),
        (
            Request(
                url="https://example.com/",
                method="GET",
                callback=lambda x: x,
                client=lambda x: x,
            ),
            HttpUrl("https://example.com/"),
        ),
    ],
)
def test_request_url_encoded(req, expected):
    assert req.url_encoded == expected
