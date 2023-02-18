from typing import Callable, Iterator, Literal, TypeVar, Union, Optional

from bs4 import BeautifulSoup
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass

DataItemGeneric = TypeVar("DataItemGeneric")
RequestOrData = Union["Request", DataItemGeneric]
CallbackReturn = Iterator[RequestOrData] | RequestOrData
CallbackType = Callable[["Response"], CallbackReturn]
ResponseData = str | dict


@dataclass
class Request:
    url: AnyUrl
    callback: CallbackType
    method: Literal["GET", "POST"] = "GET"
    content_type: Literal["text", "data"] = "text"
    client: Optional[str] = None


@dataclass
class Response:
    request: Request
    data: ResponseData
    parser: str = "html5lib"

    @property
    def soup(self):
        return BeautifulSoup(self.data, "html5lib")
