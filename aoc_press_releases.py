import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import ssl
import datetime

# Create a custom SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def get_soup(session, url):
    print(f"Fetching URL: {url}")
    async with session.get(url, ssl=ssl_context) as response:
        print(f"Status code: {response.status} for {url}")
        return BeautifulSoup(await response.text(), 'html.parser')

def preserve_formatting(element):
    if not element:
        return "No content found"
    
    formatted_text = ""
    for child in element.find_all('p'):
        formatted_text += child.get_text(strip=True) + "\n\n"
    
    return formatted_text.strip()

async def scrape_press_release(session, url):
    soup = await get_soup(session, url)
    
    # Scrape the title
    title_elem = soup.find('h1', class_='display-4')
    title_text = title_elem.text.strip() if title_elem else 'No title found'
    
    # Scrape the date
    date_elem = soup.find('div', class_='evo-create-type')
    if date_elem:
        date_text = date_elem.find('div', class_='col-auto').text.strip()
    else:
        date_text = 'No date found'
    
    # Scrape the main content
    content = soup.find('div', class_='evo-press-release__body')
    if content:
        text = preserve_formatting(content)
    else:
        print(f"No content found for {url}")
        text = 'No content found'
    
    # Scrape the issues (if present)
    issues_elem = soup.find('span', class_='field__label', string='Issues:')
    if issues_elem:
        issues = issues_elem.find_next('span', class_='field__items').get_text(strip=True)
    else:
        issues = 'No issues found'
    
    return f"Title: {title_text}\nDate: {date_text}\nIssues: {issues}\n\nContent:\n{text}\n\n==\n"

async def scrape_page(session, base_url, page):
    url = f"{base_url}?page={page}"
    soup = await get_soup(session, url)
    
    links = soup.find_all('div', class_='h3')
    if not links:
        print(f"No more press releases found on page {page}. Stopping.")
        return []
    
    print(f"Found {len(links)} press release links on page {page}")
    
    tasks = []
    for link in links:
        a_tag = link.find('a')
        if a_tag and 'href' in a_tag.attrs:
            full_url = urljoin(base_url, a_tag['href'])
            tasks.append(scrape_press_release(session, full_url))
    
    return await asyncio.gather(*tasks)

async def scrape_all_press_releases(base_url, max_concurrent=5):
    all_releases = []
    page = 0
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ocasio_cortez_press_releases_{timestamp}.txt"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            page_releases = await scrape_page(session, base_url, page)
            if not page_releases:
                break
            all_releases.extend(page_releases)
            
            # Save after each page
            with open(filename, 'a', encoding='utf-8') as f:
                for release in page_releases:
                    f.write(release)
            
            page += 1
            print(f"Moving to page {page}")
            await asyncio.sleep(2)  # Short delay between pages
    
    return all_releases, filename

if __name__ == "__main__":
    base_url = "https://ocasio-cortez.house.gov/media/press-releases"
    start_time = time.time()
    all_releases, filename = asyncio.run(scrape_all_press_releases(base_url))
    end_time = time.time()
    print(f"Total press releases scraped: {len(all_releases)}")
    print(f"Press releases saved to: {filename}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")