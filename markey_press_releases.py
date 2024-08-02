import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse
import ssl
import datetime
from urllib import robotparser

# Create a custom SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Custom headers
HEADERS = {
    'User-Agent': 'Educational Press Release Scraper (educational reasons only)',
    'From': 'educational reasons only',
}

async def check_robots_txt(session, base_url):
    parsed_url = urlparse(base_url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    
    async with session.get(robots_url, ssl=ssl_context) as response:
        if response.status == 200:
            print(f"robots.txt found. Content:\n{await response.text()}\n")
            return await response.text()
        else:
            print("No robots.txt found.")
            return None

def can_fetch(robots_txt, user_agent, url):
    if not robots_txt:
        return True
    
    rp = robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())
    return rp.can_fetch(user_agent, url)

async def get_soup(session, url):
    print(f"Fetching URL: {url}")
    async with session.get(url, ssl=ssl_context, headers=HEADERS) as response:
        print(f"Status code: {response.status} for {url}")
        return BeautifulSoup(await response.text(), 'html.parser')

def preserve_formatting(element):
    if not element:
        return "No content found"
    
    formatted_text = ""
    for child in element.descendants:
        if child.name == 'p':
            text = child.get_text(strip=True)
            if text:
                formatted_text += text + "\n\n"
        elif child.name == 'br':
            formatted_text += "\n"
    
    return formatted_text.strip()

async def scrape_press_release(session, url):
    soup = await get_soup(session, url)
    
    # Scrape the date
    date_elem = soup.find('div', class_='ArticleBlock__date')
    date_text = date_elem.text.strip() if date_elem else 'No date found'
    
    # Scrape the title
    title_elem = soup.find('h1', class_='Heading Heading--h2')
    title_text = title_elem.text.strip() if title_elem else 'No title found'
    
    # Scrape the main content
    content = soup.find('div', class_='RawHTML')
    if content:
        text = preserve_formatting(content)
    else:
        print(f"No content found for {url}")
        text = 'No content found'
    
    return f"Title: {title_text}\nDate: {date_text}\n\nContent:\n{text}\n\n==\n"

async def scrape_page(session, base_url, page, robots_txt):
    url = f"{base_url}{page}"
    
    if not can_fetch(robots_txt, HEADERS['User-Agent'], url):
        print(f"robots.txt disallows scraping {url}")
        return []
    
    soup = await get_soup(session, url)
    
    links = soup.find_all('a', class_='ArticleBlock__title__link')
    if not links:
        print(f"No more press releases found on page {page}. Stopping.")
        return []
    
    print(f"Found {len(links)} press release links on page {page}")
    
    tasks = []
    for link in links:
        if 'href' in link.attrs:
            full_url = urljoin(base_url, link['href'])
            if can_fetch(robots_txt, HEADERS['User-Agent'], full_url):
                tasks.append(scrape_press_release(session, full_url))
            else:
                print(f"robots.txt disallows scraping {full_url}")
    
    return await asyncio.gather(*tasks)

async def scrape_all_press_releases(base_url, start_page, filename, max_concurrent=5):
    all_releases = []
    page = start_page
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        robots_txt = await check_robots_txt(session, base_url)
        
        while True:
            page_releases = await scrape_page(session, base_url, page, robots_txt)
            if not page_releases:
                break
            all_releases.extend(page_releases)
            
            # Append after each page
            with open(filename, 'a', encoding='utf-8') as f:
                for release in page_releases:
                    f.write(release)
            
            page += 1
            print(f"Moving to page {page}")
            await asyncio.sleep(2)  # Short delay between pages
    
    return all_releases

if __name__ == "__main__":
    base_url = "https://www.markey.senate.gov/news/press-releases?pagenum_rs="
    start_page = 359  # Set your desired starting page here
    filename = "markey_press_releases_20240802_023708.txt"  # Set your existing filename here
    
    start_time = time.time()
    all_releases = asyncio.run(scrape_all_press_releases(base_url, start_page, filename))
    end_time = time.time()
    
    print(f"Total press releases scraped: {len(all_releases)}")
    print(f"Press releases appended to: {filename}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")