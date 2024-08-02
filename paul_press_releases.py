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
    seen_texts = set()
    for child in element.find_all(['p', 'div', 'span', 'strong', 'em', 'a']):
        text = child.get_text(strip=True)
        if text and text not in seen_texts:
            seen_texts.add(text)
            if formatted_text:
                formatted_text += "\n\n"  # Add one paragraph spacing
            formatted_text += text
    
    return formatted_text.strip()

async def scrape_press_release(session, url):
    soup = await get_soup(session, url)
    
    # Scrape the title
    title_elem = soup.find('h1', style='font-weight: 400; text-align: center;')
    title_text = title_elem.get_text(strip=True) if title_elem else 'No title found'
    
    # Scrape the date
    date_elem = soup.find_all('p', style='font-weight: 400; text-align: right;')
    date_text = date_elem[1].get_text(strip=True) if len(date_elem) > 1 else 'No date found'
    
    # Scrape the main content
    content_elem = soup.find('div', class_='et_pb_text_inner')
    if content_elem:
        text = preserve_formatting(content_elem)
    else:
        print(f"No content found for {url}")
        text = 'No content found'
    
    return f"Title: {title_text}\nDate: {date_text}\n\nContent:\n{text}\n\n==\n"

async def scrape_page(session, base_url, page_url):
    soup = await get_soup(session, page_url)
    
    links = soup.find_all('h2', class_='entry-title')
    if not links:
        print(f"No more press releases found on {page_url}. Stopping.")
        return [], None
    
    print(f"Found {len(links)} press release links on {page_url}")
    
    tasks = []
    for link in links:
        a_tag = link.find('a')
        if a_tag and 'href' in a_tag.attrs:
            full_url = urljoin(base_url, a_tag['href'])
            tasks.append(scrape_press_release(session, full_url))
    
    next_page_tag = soup.find('a', class_='nextpostslink')
    next_page_url = urljoin(base_url, next_page_tag['href']) if next_page_tag else None
    
    return await asyncio.gather(*tasks), next_page_url

async def scrape_all_press_releases(base_url):
    all_releases = []
    page_url = base_url
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rand_paul_press_releases_{timestamp}.txt"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        while page_url:
            page_releases, page_url = await scrape_page(session, base_url, page_url)
            if not page_releases:
                break
            all_releases.extend(page_releases)
            
            # Save after each page
            with open(filename, 'a', encoding='utf-8') as f:
                for release in page_releases:
                    f.write(release + '\n\n')
            
            print(f"Moving to next page: {page_url}")
            await asyncio.sleep(2)  # Short delay between pages
    
    return all_releases, filename

if __name__ == "__main__":
    base_url = "https://www.paul.senate.gov/news/"
    start_time = time.time()
    all_releases, filename = asyncio.run(scrape_all_press_releases(base_url))
    end_time = time.time()
    print(f"Total press releases scraped: {len(all_releases)}")
    print(f"Press releases saved to: {filename}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")