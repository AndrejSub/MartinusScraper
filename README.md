# Martinus_Scraper
**Overview**
The Martinus Scraper is a script designed to scrape book details from the Martinus.sk website. The script fetches data about books from specified categories and stores the data in JSON format.

**Features**
Asynchronous scraping for faster data collection.
User can choose multiple categories to scrape.
Data for each book includes: title, description, price, availability, rating, and category.
Output is saved to a JSON file named output.json.

**Dependencies**
asyncio: Provides asynchronous code execution.
unicodedata: Unicode character database operations.
random: Generating random numbers.
selectolax: Fast HTML parser.
httpx: Asynchronous HTTP client.
json: JSON encoder and decoder.
datetime: Basic date and time types.

**To install dependencies, use:**
pip install asyncio unicodedata random selectolax httpx json datetime

**Classes and Main Functions**
Book: A class representing a single book and its attributes.
BookParser: Contains static methods for extracting attributes of a book from its webpage.
MartinusScraper: Main class that manages the scraping process. Functions include fetching page data, parsing individual books/pages, and saving the results to a JSON file.
if __name__ == "__main__": The script's entry point.
How to Run

**To run the scraper, follow these steps:**
Ensure you have all the required dependencies installed.
Navigate to the directory containing the script.
Run the script using Python: python <script_name>.py

When prompted, choose at least two categories separated by a space (e.g., beletria komiksy). 
Wait for the scraping process to complete. Once finished, the data will be saved in output.json in the same directory.

**Note**
This scraper relies on the structure of the Martinus.sk website. If the website undergoes changes, the script might stop working as expected and may need adjustments. 
Always respect the terms of service and **robots.txt** file of the website when scraping.

