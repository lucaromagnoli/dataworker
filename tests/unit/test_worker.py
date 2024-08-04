from dataclasses import dataclass

import pytest

from dataservice.models import Request, Response
from dataservice.worker import DataWorker
from tests.unit.clients import ToyClient


@dataclass
class Foo:
    parsed: str


@pytest.fixture
def config():
    return {"max_workers": 1, "deduplication": False, "deduplication_keys": ["url"]}


request_with_data_callback = Request(
    url="http://example.com",
    callback=lambda x: {"parsed": "data"},
    client=ToyClient(),
)

request_with_dataclass_callback = Request(
    url="http://example.com",
    callback=lambda x: Foo(parsed="data"),
    client=ToyClient(),
)


request_with_iterator_callback = Request(
    url="http://example.com",
    callback=lambda x: iter(
        Request(
            url="http://example.com",
            client=ToyClient(),
            callback=lambda x: {"parsed": "data"},
        )
    ),
    client=ToyClient(),
)


@pytest.fixture
def data_worker_with_params(request, toy_client, config):
    if "requests" not in request.param:
        request.param["requests"] = [request_with_data_callback]

    request.param["config"] = {**config, **(request.param.get("config") or {})}
    return DataWorker(
        requests=request.param["requests"], config=request.param["config"]
    )


@pytest.fixture
def data_worker(config):
    return DataWorker(requests=[request_with_data_callback], config=config)


@pytest.fixture
def queue_item(request):
    return request.param


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requests, expected",
    [
        ([request_with_data_callback], {"parsed": "data"}),
        ([request_with_dataclass_callback], Foo(parsed="data")),
    ],
)
async def test_data_worker_handles_request_correctly(requests, expected, config):
    data_worker = DataWorker(requests, config)
    await data_worker.fetch()
    assert data_worker.get_data_item() == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("data_worker_with_params", [{"requests": []}], indirect=True)
async def test_data_worker_handles_empty_queue(data_worker_with_params):
    with pytest.raises(ValueError, match="No requests to process"):
        await data_worker_with_params.fetch()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params, queue_item",
    [
        (
            {},
            request_with_data_callback,
        )
    ],
    indirect=True,
)
async def test_handles_queue_item_puts_dict_in_data_queue(
    data_worker_with_params, queue_item
):
    await data_worker_with_params._handle_queue_item(queue_item)
    assert not data_worker_with_params.has_no_more_data()
    assert data_worker_with_params.get_data_item() == {"parsed": "data"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params, queue_item",
    [({}, request_with_iterator_callback)],
    indirect=True,
)
async def test_handles_queue_item_puts_request_in_work_queue(
    data_worker_with_params, queue_item
):
    await data_worker_with_params._handle_queue_item(queue_item)
    assert data_worker_with_params._work_queue.get_nowait() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params",
    [{}],
    indirect=True,
)
async def test_handles_queue_item_raises_value_error_for_unknown_type(
    data_worker_with_params, mocker
):
    with pytest.raises(ValueError, match="Unknown item type <class 'int'>"):
        await data_worker_with_params._handle_queue_item(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params",
    [{"requests": [request_with_data_callback]}],
    indirect=True,
)
async def test_is_duplicate_request_returns_false_for_new_request(
    data_worker_with_params,
):
    request = Request(
        url="http://example.com", client=ToyClient(), callback=lambda x: x
    )
    assert not data_worker_with_params._is_duplicate_request(request)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config, expected",
    [
        ({"deduplication": True, "max_workers": 1, "deduplication_keys": ["url"]}, 1),
        ({"deduplication": False, "max_workers": 1, "deduplication_keys": ["url"]}, 2),
    ],
)
async def test_deduplication(config, expected, mocker):
    mocked_handle_request = mocker.patch(
        "dataservice.worker.DataWorker._handle_request",
        side_effect=[
            Response(request=request_with_data_callback, data={"parsed": "data"}),
            Response(request=request_with_data_callback, data={"parsed": "data"}),
        ],
    )
    data_worker = DataWorker(
        requests=[request_with_data_callback, request_with_data_callback], config=config
    )
    await data_worker.fetch()
    assert mocked_handle_request.call_count == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect, expected_response, expected_call_count",
    [
        (
            [
                Response(
                    request=request_with_data_callback, data=None, status_code=500
                ),
                Response(
                    request=request_with_data_callback, data=None, status_code=500
                ),
                Response(request=request_with_data_callback, data={"parsed": "data"}),
            ],
            Response(request=request_with_data_callback, data={"parsed": "data"}),
            3,
        ),
        (
            [
                Response(
                    request=request_with_data_callback, data=None, status_code=500
                ),
                Response(
                    request=request_with_data_callback, data=None, status_code=500
                ),
                Response(
                    request=request_with_data_callback, data=None, status_code=500
                ),
            ],
            Response(request=request_with_data_callback, data=None, status_code=500),
            3,
        ),
    ],
)
async def test__handle_request(
    data_worker, mocker, side_effect, expected_response, expected_call_count
):
    mocked_make_request = mocker.patch(
        "dataservice.worker.DataWorker._make_request",
        side_effect=side_effect,
    )
    response = await data_worker._handle_request(request_with_data_callback)
    assert response == expected_response
    assert mocked_make_request.call_count == expected_call_count