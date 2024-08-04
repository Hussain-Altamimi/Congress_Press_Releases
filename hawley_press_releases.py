import time
import re
from urllib.parse import urljoin
import datetime
import os
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# PIA SOCKS5 proxy settings
PIA_SERVERS = [
    "proxy-us-atlanta.privateinternetaccess.com",
    "proxy-us-california.privateinternetaccess.com",
    "proxy-us-chicago.privateinternetaccess.com",
    "proxy-us-dallas.privateinternetaccess.com",
    "proxy-us-denver.privateinternetaccess.com",
    "proxy-us-florida.privateinternetaccess.com",
    "proxy-us-houston.privateinternetaccess.com",
    "proxy-us-lasvegas.privateinternetaccess.com",
    "proxy-us-newyorkcity.privateinternetaccess.com",
    "proxy-us-seattle.privateinternetaccess.com",
    "proxy-us-siliconvalley.privateinternetaccess.com",
    "proxy-us-washingtondc.privateinternetaccess.com",
    "proxy-us-baltimore.privateinternetaccess.com",
    "proxy-us-boston.privateinternetaccess.com",
    "proxy-us-charlotte.privateinternetaccess.com",
    "proxy-us-detroit.privateinternetaccess.com",
    "proxy-us-honolulu.privateinternetaccess.com",
    "proxy-us-indianapolis.privateinternetaccess.com",
    "proxy-us-losangeles.privateinternetaccess.com",
    "proxy-us-miami.privateinternetaccess.com",
    "proxy-us-minneapolis.privateinternet.com",
]

# PIA credentials
PIA_USERNAME = os.getenv("PIA_USERNAME", "")
PIA_PASSWORD = os.getenv("PIA_PASSWORD", "")

def get_random_pia_proxy():
    server = random.choice(PIA_SERVERS)
    return f"{server}:1080"

def setup_driver(use_proxy=False):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if use_proxy:
        proxy = get_random_pia_proxy()
        options.add_argument(f'--proxy-server=socks5://{PIA_USERNAME}:{PIA_PASSWORD}@{proxy}')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def extract_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    content_div = soup.select_one('div.et_pb_post_content')
    if content_div:
        # Remove empty paragraphs and unnecessary whitespace
        for p in content_div.find_all('p'):
            if p.text.strip() == '':
                p.decompose()
        content = content_div.get_text(separator='\n', strip=True)
        return content
    return "No content found"

def scrape_press_release(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find title
        title_elem = soup.find('h1', class_='entry-title')
        title_text = title_elem.text.strip() if title_elem else 'No title found'

        # Find date
        date_elem = soup.find('span', class_='published')
        date_text = date_elem.text.strip() if date_elem else 'No date found'

        # Extract content
        content = extract_content(driver.page_source)
        if content == "No content found":
            print(f"No content found for {url}")

        return f"Title: {title_text}\nDate: {date_text}\n\nContent:\n{content}\n\n==\n"
    except TimeoutException:
        print(f"Timeout occurred while loading {url}")
        return f"Error: Timeout occurred while loading {url}\n\n==\n"
    except NoSuchElementException as e:
        print(f"Element not found on {url}: {e}")
        return f"Error: Element not found on {url}\n\n==\n"
    except Exception as e:
        print(f"An error occurred while scraping {url}: {e}")
        return f"Error: An error occurred while scraping {url}\n\n==\n"

def scrape_page(driver, base_url, page):
    url = f"{base_url}/page/{page}/?et_blog" if page > 1 else base_url
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        press_release_elements = soup.find_all('article', class_='et_pb_post')

        if not press_release_elements:
            print(f"No press releases found on page {page}. This might be the last page.")
            return []

        print(f"Found {len(press_release_elements)} press release elements on page {page}")

        releases = []
        for element in press_release_elements:
            title_elem = element.find('h2', class_='entry-title')
            if title_elem and title_elem.a:
                link = title_elem.a['href']
                full_url = urljoin(base_url, link)
                releases.append(scrape_press_release(driver, full_url))

        return releases
    except TimeoutException:
        print(f"Timeout occurred while loading page {page}")
        return []
    except Exception as e:
        print(f"An error occurred while scraping page {page}: {e}")
        return []

def scrape_all_press_releases(base_url, start_page, end_page, filename, use_proxy=False):
    all_releases = []
    driver = setup_driver(use_proxy)
    empty_pages = 0

    try:
        for page in range(start_page, end_page + 1):
            page_releases = scrape_page(driver, base_url, page)
            if not page_releases:
                empty_pages += 1
                if empty_pages >= 3:  # Stop if we encounter 3 consecutive empty pages
                    print(f"No more press releases found after 3 consecutive empty pages. Stopping.")
                    break
            else:
                empty_pages = 0  # Reset the counter if we find releases
                all_releases.extend(page_releases)

                with open(filename, 'a', encoding='utf-8') as f:
                    for release in page_releases:
                        f.write(release)

            print(f"Completed page {page}")
            time.sleep(2)  # Short delay between pages
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    finally:
        driver.quit()

    return all_releases

if __name__ == "__main__":
    base_url = "https://www.hawley.senate.gov/press-releases"
    start_page = 1
    end_page = 92  # Set to the last known page number
    filename = f"hawley_press_releases_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    start_time = time.time()

    use_proxy = False  # Set this to True if you want to use the proxy
    all_releases = scrape_all_press_releases(base_url, start_page, end_page, filename, use_proxy=use_proxy)
    print(f"Total press releases scraped: {len(all_releases)}")

    end_time = time.time()
    print(f"Press releases appended to: {filename}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")