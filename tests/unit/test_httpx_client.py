import pytest
from httpx import HTTPError, HTTPStatusError
from httpx import Response as HttpXResponse
from httpx import TimeoutException as HTTPXTimeoutException
from pytest_httpx import HTTPXMock

from dataservice.clients import HttpXClient
from dataservice.exceptions import (
    DataServiceException,
    RetryableException,
    TimeoutException,
)
from dataservice.models import Request


@pytest.fixture
def httpx_client():
    return HttpXClient()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, data, text, content_type, expected_data, expected_text",
    [
        pytest.param(
            "https://example.com/",
            {"key": "value"},
            None,
            "json",
            {"key": "value"},
            '{"key": "value"}',
            id="JSON response",
        ),
        pytest.param(
            "https://example.com/",
            None,
            "This is a text response",
            "text",
            None,
            "This is a text response",
            id="Text response",
        ),
    ],
)
async def test_httpx_client_get_request(
    httpx_mock,
    httpx_client,
    url,
    data,
    text,
    content_type,
    expected_text,
    expected_data,
):
    request_url = "https://example.com/?q=test"
    params = {"q": "test"}
    httpx_mock.add_response(url=request_url, json=data, text=text, method="GET")
    request = Request(
        url=url,
        method="GET",
        params=params,
        callback=lambda x: x,
        content_type=content_type,
        client=HttpXClient,
    )
    response = await httpx_client.make_request(request)
    assert response.text == expected_text
    assert response.data == expected_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, form_data, json_data, content_type, expected",
    [
        pytest.param(
            "https://example.com/",
            {"key": "value"},
            {"json": ["data"]},
            "json",
            {"key": "value"},
            id="JSON response",
        ),
    ],
)
async def test_httpx_client_post_request(
    httpx_mock, httpx_client, url, form_data, json_data, content_type, expected
):
    request_url = "https://example.com/"
    json_resp = {"response": "example"}
    httpx_mock.add_response(url=request_url, json=json_resp, method="POST")
    request = Request(
        url="https://example.com",
        method="POST",
        form_data=form_data,
        json_data=json_data,
        callback=lambda x: x,
        content_type=content_type,
        client=HttpXClient,
    )
    response = await httpx_client.make_request(request)
    assert response.data == json_resp


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client_exception, expected_exception",
    [
        pytest.param(
            HTTPStatusError(
                "Error", request=None, response=HttpXResponse(status_code=404)
            ),
            DataServiceException,
            id="404",
        ),
        pytest.param(
            HTTPStatusError(
                "Error", request=None, response=HttpXResponse(status_code=500)
            ),
            RetryableException,
            id="505 Retryable",
        ),
        pytest.param(
            HTTPStatusError(
                "Too Many Requests",
                request=None,
                response=HttpXResponse(status_code=429),
            ),
            RetryableException,
            id="429 Retryable",
        ),
        pytest.param(
            HTTPXTimeoutException("Timeout"),
            TimeoutException,
            id="Timeout. Dont Retry",
        ),
        pytest.param(
            HTTPError("Error"),
            DataServiceException,
            id="Error. Dont retry",
        ),
    ],
)
async def test_httpx_client_make_request_exceptions(
    httpx_client, httpx_mock: HTTPXMock, client_exception: HTTPError, expected_exception
):
    request = Request(
        url="https://example.com",
        callback=lambda x: x,
        client=HttpXClient,
    )
    httpx_mock.add_exception(exception=client_exception)
    with pytest.raises(expected_exception):
        await httpx_client.make_request(request)


@pytest.mark.asyncio
async def test_follow_redirects(httpx_mock, httpx_client):
    httpx_mock.add_response(
        url="https://example.com/",
        status_code=301,
        headers={"Location": "https://example.com/redirected"},
    )
    httpx_mock.add_response(
        url="https://example.com/redirected",
        status_code=200,
    )
    request = Request(
        url="https://example.com",
        callback=lambda x: x,
        client=HttpXClient,
    )
    response = await httpx_client.make_request(request)
    assert response.request.url == "https://example.com/"
    assert response.url == "https://example.com/redirected"
    assert response.status_code == 200
