#! python3

"""
amazon_scraper.py - scrape product-related data from amazon.com (US version)
and save them in a CSV file for further processing and analysis.

Usage:
    py amazon_scraper.py
    >>> Search amazon.com: <your_desired_product>
    
You will be asked to enter what kinda product you want to search for.
from there, your data will be delivered to you as a CSV file located relative to the amazon_scraper.py location 
    >>> "..\amazon_CSV_files\<product_name>.csv"

scraped data includes:
    - Product title.
    - Price of the product.
    - Reviewers ratings.
    - Number of reviews.
    - Product page URL.
    - Product image URL.
    - Is the product sponsored?
    - Product ASIN: "Amazon Standard Identification Number".

The process to find the product details is as follows:
    First: The first page gets downloaded and parsed to determine the total available pages to download and scrape.
    Second: If there is more than one page, the other pages get downloaded first and the `Response` from the `request` is saved in a list to parse later.
        - The script will run normally if only one page is found.
    Third: After all pages get downloaded, we proceed to parse all the details from all pages.
    In the end, the scraped data gets saved into a CSV file with the search term as the name of the file.

    The script will show two informative, nice-looking progress bars.
    The first progress bar is for downloading web pages and the second progress bar is for scraping data.
"""

from tqdm import tqdm
from bs4 import BeautifulSoup
import pandas as pd
import requests
import random
import time
import os

# A list of 1000 User-Agents for the request headers
with open(r".\user_agents.txt", "r") as user_agent_text_file:
    list_of_user_agents = [user_agent.strip() for user_agent in user_agent_text_file]


def create_amazon_url(product_name: str) -> str:
    """Create an amazon.com URL (US version) with the `product_name` attached to it. return an amazon.com `URL`"""
    return f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}"


def add_page_number_to_url(product_url: str, page_number: int=1) -> str:
    """Add a `page_number` at the end of the current amazon.com URL to find more pages about the searched product. return modified `URL`"""
    return product_url + f"&page={page_number}"


def randomize_user_agent_header() -> dict[str, str]:
    """Provide a header for the HTTP request with a randomized User-Agent string.

    This helps the scraper to go undercover and avoid the firewall of amazon.com
    
    return the request's `header`
    """
    request_header = {
    "User-Agent": random.choice(list_of_user_agents),  # randomized User-Agent
    "Accept-Language": "en-GB,en;q=0.5",
    "Accept-Encoding": "br, gzip, deflate",
    "Accept": "test/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referrer": "https://www.google.com",  # this can be randomized
    "DNT": "1"  # Do Not Track!
    }
    return request_header


def request_web_page_content(product_url: str) -> requests.Response:
    """Download the content of a web page from a given `URL`, return a `response` object"""
    web_page_response = requests.get(product_url, headers=randomize_user_agent_header())
    web_page_response.raise_for_status()
    return web_page_response


def get_html_document(web_page_response: requests.Response) -> BeautifulSoup:
    """Create a BeautifulSoup object from the downloaded web page. return a `BeautifulSoup` object """
    html_document = BeautifulSoup(web_page_response.text, "html.parser")
    return html_document


def find_all_products_in_web_page(html_document: BeautifulSoup):
    """Locate all products from the `HTML document`, It will find all `div` tags that contain the details about the product.
    
    return `ResultSet`
    """
    products_list = html_document.find_all("div", {"data-component-type": "s-search-result"})
    return products_list


def parse_product_info(product_html_tag) -> list:
    """Locate specific details from a given product. 
    
    details include:
    - Product title.
    - Price of the product.
    - Reviewers ratings.
    - Number of reviews.
    - Product page URL.
    - Product image URL.
    - Is the product sponsored? (Yes/No)
    - Product ASIN: "Amazon Standard Identification Number".
    """
    try:
        product_title = product_html_tag.find(class_="a-text-normal").text
    except AttributeError:
        product_title = ""

    try:
        product_price = product_html_tag.find(class_='a-price-whole').text[:-1].replace(',','')  # remove the dollar sign $ from the price.
    except AttributeError:
        product_price = 0
    
    try:
        reviewers_ratings = product_html_tag.find("span", "a-icon-alt").text
    except AttributeError:
        reviewers_ratings = ""

    try:
        number_of_reviews = product_html_tag.find("span", "a-size-base s-underline-text").text.replace(',','')
    except AttributeError:
        number_of_reviews = 0

    try:
        product_page_url = f"https://amazon.com{product_html_tag.find(class_='a-link-normal s-no-outline').get('href')}"
    except:
        product_page_url = ""
        
    try:
        # The size of the image thumbnail is 3x bigger than the normal thumbnail.
        product_image_url = product_html_tag.find("img", class_="s-image").get("srcset").split()[-2] 
    except:
        product_image_url = ""

    sponsored_product = "Yes" if product_html_tag.select_one("span:-soup-contains('Sponsored')") else "No"

    # ASIN: Amazon Standard Identification Number
    product_ASIN = product_html_tag['data-asin']

    return [product_title, product_price, reviewers_ratings, number_of_reviews, product_page_url, product_image_url, sponsored_product, product_ASIN]


def total_pages(html_page: BeautifulSoup) -> int:
    """Find the total number of web pages for the requested product, return the `total pages available` to scrape.

    When only one web page is found, `return 1`, which is the first downloaded web page.
    """
    try:
        total_pages_available = html_page.find("span", class_="s-pagination-item s-pagination-disabled").text
    except AttributeError:
        return 1  # return 1 which it's the first page.
    return int(total_pages_available)


def product_data_to_csv(list_of_product_data: list, csv_file_location: str, csv_file_name: str) -> None:
    """Save scraped data to a `CSV` file using the panda module"""
    df = pd.DataFrame(list_of_product_data, columns=["Product title", "Price", "Reviewers ratings", "Number of reviews", "Page URL", "Image URL", "Sponsored", "ASIN number"])
    os.makedirs(csv_file_location, exist_ok=True)
    csv_file = csv_file_location + "\\" + csv_file_name
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        # will create a new CSV file if it doesn't exist or overwrite the existing one!
        df.to_csv(f, index=False)
        

def main(product_name: str, csv_file_location: str, csv_file_name: str) -> None:

    responses_list = []  # store the webpage response to iterate over them to fetch the data.
    list_of_product_data = []  # [list of [lists]] to store the product details into a CSV file.
    try_download_other_pages = 3  # handle failure to download web pages other than the first web page, up to 3 times.
    
    # --------------------------------------------------------------------
    # The first request. This section is to determine the number of pages that are available to download.
    product_url = create_amazon_url(product_name)  # create an amazon.com URL out of the product name
    try:
        web_page_response = request_web_page_content(product_url)
    except requests.exceptions.HTTPError as http_error:
        # Errors may occur like: "503 Server Error" or "404 Client Error"
        print(f"something went wrong with the first request, shutting down the scraping process...\nERROR: {http_error}")
        return None
    html_document = get_html_document(web_page_response)
    total_pages_available = total_pages(html_document)
    # --------------------------------------------------------------------

    print()  # for spacing the output in the command line
    # A progress bar to reflect the downloading process.
    requests_pbar = tqdm(total=total_pages_available, colour="#fc5b12", ascii=" ▇", bar_format="{percentage:.0f}%|{bar}|Estimated time: {remaining}| Downloading page number: {n_fmt}/{total_fmt} web pages")
    
    # Requests the remaining pages with a progress bar to display status.
    for current_page_number in range(1, total_pages_available + 1):
        if current_page_number == 1:
            # add the first downloaded page to the responses_list and there is no need to re-request the first page again.
            responses_list.append(web_page_response)
            requests_pbar.update(1)
            continue

        else:
            current_page_url = add_page_number_to_url(product_url, current_page_number)  # attach the page number to the URL
            try:
                web_page_response = request_web_page_content(current_page_url)
                requests_pbar.update(1)
                time.sleep(2)  # ZzZzZzZzZzZz
            except requests.exceptions.HTTPError as http_error:
                # Errors may occur like: "503 Server Error" or "404 Client Error"
                try_download_other_pages -= 1
                print(f"ERROR: {http_error}")
                if try_download_other_pages == 0:
                    break  # move on to parse data instead of trying more URLs to save time. ¯\_(ツ)_/¯
                else:
                    continue  # failed to download the current page, try up to 3 other pages.

            responses_list.append(web_page_response)

    requests_pbar.bar_format = "{percentage:.0f}%|{bar}|Overall time: {elapsed}| Total pages downloaded: " + str(len(responses_list))  # progress result
    requests_pbar.close()
    
    # A progress bar to reflect the data extraction process.
    responses_pbar = tqdm(total=len(responses_list), colour="#ff9900", ascii=" ▇", bar_format="{percentage:.0f}%|{bar}|Extracting data from page: {n_fmt}/{total_fmt} web pages.")
    
    # loop through the responses_list and create a BeautifulSoup object.
    for current_web_page_response in responses_list:
        html_document = get_html_document(current_web_page_response)
        list_of_product_tags = find_all_products_in_web_page(html_document)

        # parse the information about the product and save it in a list.
        for current_product_tag in list_of_product_tags:
            product_info = parse_product_info(current_product_tag)
            list_of_product_data.append(product_info)

        responses_pbar.update(1)

    responses_pbar.close()
    print()  # for spacing the output in the command line

    # save the parsed data in a CSV file for further processing and analysis.
    if len(list_of_product_data) != 0:
        product_data_to_csv(list_of_product_data, csv_file_location, csv_file_name)
        print(f"Product data saved to a CSV file.")
    else:
        print("Nothing to save here!")
        return None


if __name__ == "__main__":
    while True:
        product_name = input("Search amazon.com: ")
        if product_name.isspace() or product_name == "":
            continue
        else:
            break
    product_name = product_name.strip()  # remove the leading and trailing whitespaces from the product_name.
    # so the CSV file name doesn't include a space like in "sony cameras .csv"
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ^ 
    FILE_LOCATION = fr"..\amazon_CSV_files"
    FILE_NAME = f"{product_name}.csv"
    print("Fetching data, Please wait...", flush=True)
    main(product_name, FILE_LOCATION, FILE_NAME)