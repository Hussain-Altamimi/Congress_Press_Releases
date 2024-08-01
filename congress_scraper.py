import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import ssl

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
    formatted_text = ""
    for child in element.children:
        if child.name == 'p':
            formatted_text += child.get_text(strip=True) + "\n\n"
        elif child.name == 'ul':
            for li in child.find_all('li'):
                formatted_text += "• " + li.get_text(strip=True) + "\n"
            formatted_text += "\n"
        elif child.name == 'ol':
            for i, li in enumerate(child.find_all('li'), 1):
                formatted_text += f"{i}. " + li.get_text(strip=True) + "\n"
            formatted_text += "\n"
        elif child.name == 'br':
            formatted_text += "\n"
        elif child.name == 'div' and 'media-item' in child.get('class', []):
            formatted_text += "[Embedded media content]\n\n"
        elif child.string and child.string.strip():
            formatted_text += child.string.strip() + "\n"
    
    while "\n\n\n" in formatted_text:
        formatted_text = formatted_text.replace("\n\n\n", "\n\n")
    
    return formatted_text.strip()

async def scrape_press_release(session, url):
    soup = await get_soup(session, url)
    
    title_div = soup.find('div', class_='block--pocan-evo-custom-62-page-title')
    if title_div:
        title = title_div.find('h1', class_='display-4')
        title_text = title.text.strip() if title else 'No title found'
    else:
        title_text = 'No title found'
    
    meta_div = soup.find('div', class_='evo-create-type')
    if meta_div:
        date = meta_div.find('div', class_='col-auto')
        date_text = date.text.strip() if date else 'No date found'
        pr_tag = meta_div.find_all('div', class_='col-auto')[1].text.strip() if len(meta_div.find_all('div', class_='col-auto')) > 1 else 'No PR tag found'
    else:
        date_text = 'No date found'
        pr_tag = 'No PR tag found'
    
    content = soup.find('div', class_='evo-press-release__body')
    if content:
        text = preserve_formatting(content)
    else:
        print(f"No content found for {url}")
        text = 'No content found'
    
    return f"Title: {title_text}\nDate: {date_text}\nPR Tag: {pr_tag}\n\nContent:\n{text}\n\n==\n"

async def scrape_page(session, base_url, page):
    url = f"{base_url}?page={page}"
    soup = await get_soup(session, url)
    
    links = soup.find_all('a', class_='btn-primary', string='Read More')
    if not links:
        print(f"No more press releases found on page {page}. Stopping.")
        return []
    
    print(f"Found {len(links)} press release links on page {page}")
    
    tasks = []
    for link in links:
        full_url = urljoin(base_url, link['href'])
        tasks.append(scrape_press_release(session, full_url))
    
    return await asyncio.gather(*tasks)

async def scrape_all_press_releases(base_url, max_concurrent=5):
    all_releases = []
    page = 0
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            page_releases = await scrape_page(session, base_url, page)
            if not page_releases:
                break
            all_releases.extend(page_releases)
            
            # Save after each page
            with open('press_releases.txt', 'a', encoding='utf-8') as f:
                for release in page_releases:
                    f.write(release)
            
            page += 1
            print(f"Moving to page {page}")
            await asyncio.sleep(2)  # Short delay between pages
    
    return all_releases

if __name__ == "__main__":
    base_url = "https://pocan.house.gov/media-center"
    start_time = time.time()
    all_releases = asyncio.run(scrape_all_press_releases(base_url))
    end_time = time.time()
    print(f"Total press releases scraped: {len(all_releases)}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")