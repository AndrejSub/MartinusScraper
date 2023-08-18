import asyncio
import unicodedata
import random
from selectolax.parser import HTMLParser
import httpx
import json
from datetime import datetime

MAX_ACCEPTABLE_TIMEOUT = 30.0
DELAY_RANGE = (1, 7)
MAX_TRIES = 5
MIN_CATEGORIES = 2

MARTINUS_URL = "https://www.martinus.sk/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 '
                  '(KHTML, like Gecko) Version/16.1 Safari/605.1.15'
}


class Book:

    def __init__(self, title: str, description: str, price: float, available: bool, is_rated: bool, rating: int,
                 category: int):
        self.title = title
        self.description = description
        self.price = price
        self.available = available
        self.is_rated = is_rated
        self.rating = rating
        self.category = category

    def to_dict(self):
        # Converts book to dict
        return {
            "title": self.title,
            "description": self.description,
            "available": self.available,
            "price": self.price,
            "is_rated": self.is_rated,
            "rating": self.rating,
            "category": self.category,
        }


class BookParser:
    # Contains methods for extracting attributes of a book from book page.
    @staticmethod
    def get_title(book_page):
        try:
            return str(book_page.css_first('meta[property="og:title"]').attributes["content"])
        except AttributeError:
            return "undefined"

    @staticmethod
    def get_description(book_page):
        description_div = book_page.css_first('#description')

        for cookie_div in description_div.css('div.cookieconsent-optout-marketing'):
            cookie_div.decompose()

        description = description_div.css_first('.cms-article').text(deep=True)
        # adjusting description format because of bad input
        if not description:
            return ""
        description = description.replace("\n", "")
        description = description.replace("\r", " ")
        description = description.replace("\t", "")
        return description.strip()

    @staticmethod
    def get_price(book_page):
        price_element = book_page.css_first('h1.product-price__main')
        if not price_element or not price_element.text():
            return -1.0, False

        price_text = book_page.css_first('h1.product-price__main').text()
        print(price_text)
        price = unicodedata.normalize('NFKD', price_text)
        price = price.split(" ")[0]
        price = price.replace(",", ".")

        try:
            return float(price), True
        except ValueError:
            return -1.0, False

    @staticmethod
    def get_rating(book_page):
        rating_div = book_page.css_first('#star-rating')
        if rating_div and rating_div.css_first('span.text-bold'):
            rating_text = rating_div.css_first('span.text-bold').text()
            splited_rating = rating_text.split(",")
            try:
                return int(splited_rating[0]), True
            except ValueError:
                # rating is  set to -1 because book is not rated yet
                return -1, False
        else:
            return -1, False


class MartinusScraper:
    def __init__(self):
        self.books = []

    async def get_page_data(self, client, url: str, retries=0):
        # Retrieves the HTML content of the given URL.
        try:
            await asyncio.sleep(random.uniform(*DELAY_RANGE))
            resp = await client.get(url, timeout=MAX_ACCEPTABLE_TIMEOUT)
            resp.encoding = "utf-8"
            resp.raise_for_status()
            return HTMLParser(resp.text)
        except httpx.HTTPError as error:
            print(f"Error occurred when loading {url}:{error}")

            if retries < MAX_TRIES:

                print(f"retrying {retries + 1}")
                await asyncio.sleep(random.uniform(*DELAY_RANGE))
                return await self.get_page_data(client, url, retries + 1)
            else:
                print(f"loading url failed. url:  {url} ")
                return None

    async def get_single_book_page(self, book):
        book_href = book.css_first('.listing__item__title').attributes['href']
        return MARTINUS_URL + book_href

    def get_categories(self, page):
        # Scrape all available categories from main page
        categories_divs = page.css("div.mega-menu__categories")
        category_links = categories_divs[0].css("a")
        if category_links is not None:
            categories = {}
            for url in category_links:

                if not url.css("a.link--grey"):
                    text = url.text().replace("\n", "")
                    text = text.strip().lower()
                    text = text.replace(" ", "-")
                    text = text.replace(",", "")
                    categories[text] = url.attributes['href']

            print("Categories: ")
            for cat in categories:
                print(cat)

            return categories
        else:
            return None

    def get_user_input(self, categories):
        # Asks user to choose at least two categories. If provided wrong input function calls itself.
        print("Choose at least two categoreies  separated by a space. For example:beletria komiksy ")
        chosen_categories = input()
        chosen_categories = chosen_categories.split(" ")

        if len(chosen_categories) < MIN_CATEGORIES:
            print("You need to enter at least two categories")
            return self.get_user_input(categories)
        for cat in chosen_categories:
            if cat not in categories:
                print(f"You entered unknown category {cat} please try again: ")
                return self.get_user_input(categories)

        return chosen_categories

    async def get_page_count(self, client, base_url):
        page = await self.get_page_data(client, base_url)
        pages_count = page.css_first("div.btn-layout--horizontal")
        pages_count = pages_count.css('a')

        all_links = [f"{base_url}&page={page}" for page in range(1, int(pages_count[-2].text()) + 1)]
        return all_links

    async def parse_single_book(self, client, book_url, category):
        # Fetch single book
        book_page = await self.get_page_data(client, book_url)
        if book_page is None:
            title = "Undefined"
            description = "Undefined"
            price = rating = -1
            available = False
            is_rated = False
        else:
            title = BookParser.get_title(book_page)
            description = BookParser.get_description(book_page)
            price, available = BookParser.get_price(book_page)
            rating, is_rated = BookParser.get_rating(book_page)
            category = category

        return Book(title, description, price, available, is_rated, rating, category)

    async def parse_single_page(self, client, url, category):
        html = await self.get_page_data(client, url)

        if html is None:
            print(f"Failed to get HTML url: {url}")
            return
        all_books_on_page = html.css("div.listing__item")
        tasks = [self.parse_single_book(client, await self.get_single_book_page(book),
                                        category) for book in all_books_on_page]
        self.books.extend(await asyncio.gather(*tasks))

    async def parse_books(self, urls_list, category):
        async with httpx.AsyncClient(headers=HEADERS) as client:
            tasks = [self.parse_single_page(client, link, category) for link in urls_list]
            await asyncio.gather(*tasks)

    def save_to_json(self):
        json_object = json.dumps([book.to_dict() for book in self.books], ensure_ascii=False, indent=4)
        with open("output.json", "w", encoding="utf-8", ) as outfile:
            outfile.write(str(json_object))

    async def main(self):
        all_links = []
        start = datetime.now()

        async with httpx.AsyncClient(headers=HEADERS) as client:
            main_site_html = await self.get_page_data(client, MARTINUS_URL)
            categories = self.get_categories(main_site_html)
            if categories is None:
                print("Could not retrieve categories.")
                return -1

            # Getting input from user
            categories_to_scrape = self.get_user_input(categories)
            # Getting all links for scraping
            for index in range(0, len(categories_to_scrape)):
                all_links.append(await self.get_page_count(client, categories[categories_to_scrape[index]]))

        for links_index in range(0, len(all_links)):
            await self.parse_books(all_links[links_index], categories_to_scrape[links_index])

        self.save_to_json()
        print(datetime.now() - start)


if __name__ == "__main__":
    scraper = MartinusScraper()
    asyncio.run(scraper.main())
