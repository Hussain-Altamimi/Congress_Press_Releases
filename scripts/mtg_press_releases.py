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
        text = child.get_text(strip=True)
        if text:
            if formatted_text:
                formatted_text += "\n\n"  # Add one paragraph spacing
            formatted_text += text
    
    return formatted_text.strip()

async def scrape_press_release(session, url):
    soup = await get_soup(session, url)
    
    # Scrape the title
    title_elem = soup.find('h2', class_='newsie-titler')
    title_text = title_elem.get_text(strip=True) if title_elem else 'No title found'
    
    # Scrape the date
    date_elem = soup.find('b')
    date_text = date_elem.get_text(strip=True) if date_elem else 'No date found'
    
    # Scrape the tags
    tags_elem = soup.find('div', id='ctl00_ctl21_CatTags')
    if tags_elem:
        tags = [tag.get_text(strip=True) for tag in tags_elem.find_all('a')]
        tags_text = ', '.join(tags)
    else:
        tags_text = 'No tags found'
    
    # Scrape the main content
    content_elem = soup.find('div', class_='newsbody')
    if content_elem:
        text = preserve_formatting(content_elem)
    else:
        print(f"No content found for {url}")
        text = 'No content found'
    
    return f"Title: {title_text}\nDate: {date_text}\nTags: {tags_text}\n\nContent:\n{text}\n\n==\n"

async def scrape_page(session, base_url, page):
    url = f"{base_url}&Page={page}"
    soup = await get_soup(session, url)
    
    links = soup.find_all('h2', class_='newsie-titler')
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
    page = 1
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"greene_press_releases_{timestamp}.txt"
    
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
    base_url = "https://greene.house.gov/news/documentquery.aspx?DocumentTypeID=27"
    start_time = time.time()
    all_releases, filename = asyncio.run(scrape_all_press_releases(base_url))
    end_time = time.time()
    print(f"Total press releases scraped: {len(all_releases)}")
    print(f"Press releases saved to: {filename}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")