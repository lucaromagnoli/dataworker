"""Simple example of scraping books from a website with pagination argument."""

import argparse
import json
import logging
from datetime import datetime
from functools import partial
from pprint import pprint
from urllib.parse import urljoin

from dataservice import DataService, HttpXClient, Pipeline, Request, Response
from examples.logging_config import setup_logging

logger = logging.getLogger("books_scraper")
setup_logging()


def parse_books(response: Response, pagination: bool = True):
    articles = response.soup.find_all("article", {"class": "product_pod"})
    yield {
        "url": response.request.url,
        "title": response.soup.title.text,
        "articles": len(articles),
    }
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=HttpXClient())
    if pagination:
        yield from parse_pagination(response)


def parse_pagination(response):
    next_page = response.soup.find("li", {"class": "next"})
    if next_page is not None:
        next_page_url = urljoin(response.request.url, next_page.a["href"])
        yield Request(url=next_page_url, callback=parse_books, client=HttpXClient())


def parse_book_details(response: Response):
    title = response.soup.find("h1").text
    price = response.soup.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


def process_currency(results: list[dict]):
    for result in results:
        result["currency"] = "£"
        result["price"] = result["price"].replace("£", "")
    return results


def add_time_stamp(results: list[dict]):
    for result in results:
        result["timestamp"] = datetime.now().isoformat()
    return results


def write_to_file(results: list[dict], group_name: str):
    with open(f"books_{group_name}.json", "w") as f:
        json.dump(results, f, indent=4)
    logger.info("Results written to books.json")


def main(args):
    start_requests = iter(
        [
            Request(
                url="https://books.toscrape.com/index.html",
                callback=partial(parse_books, pagination=args.pagination),
                client=HttpXClient(),
            )
        ]
    )
    data_service = DataService(start_requests)
    pipeline = (
        Pipeline()
        .add_step(add_time_stamp)
        .add_final_step(
            [
                partial(write_to_file, group_name="books1"),
            ]
        )
    )
    data = pipeline._run(data_service)
    pprint(data)
    print(len(data))
    # pipeline = Pipeline(data_service)
    # for group_name, group in pipeline.group_by(type):
    #     with group as group_pipeline:
    #         group_pipeline.add_step(process_currency).add_final_step(
    #             [partial(write_to_file, group_name=group_name)]
    #         )
    # data = [item async for item in data_service]
    # with Pipeline(data) as pipeline:
    #     pipeline.add_leaves([write_to_file])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape books from a website.")
    parser.add_argument(
        "--pagination",
        action="store_true",
        help="Enable pagination.",
        default=False,
    )
    main(args=parser.parse_args())
    # asyncio.run(main(args=parser.parse_args()))
