"""
TCET Flexible Scraper - Captures ALL content from website
No hard-coded selectors - extracts everything
FIXED: Removed FlexibleContent dependency
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time
import json
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)

TCET_URL = [
    'https://tcetcercd.in/',
    'https://tcetcercd.in/about',
    'https://tcetcercd.in/innovation',
    'https://tcetcercd.in/industry-internship',
    'https://tcetcercd.in/innovation/problems',
    'https://tcetcercd.in/#news',
]


class TCETFlexibleScraper:
    """Flexible TCET scraper - adaptive content extraction"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.urls = TCET_URL  # List of URLs now
        self.driver = None
        self.content = []
    
    def setup_driver(self) -> bool:
        """Initialize Selenium WebDriver"""
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            logger.info("✓ Chrome driver initialized")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to init driver: {e}")
            return False
    
    def scrape_page(self, url: str) -> Optional[str]:
        """Fetch page HTML"""
        try:
            logger.info(f"Fetching {url}...")
            self.driver.get(url)
            
            # Wait for body to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(2)  # Wait for JS rendering
            
            html = self.driver.page_source
            logger.info(f"✓ Fetched {len(html)} bytes")
            return html
            
        except Exception as e:
            logger.error(f"✗ Fetch error: {e}")
            return None
    
    def extract_page_sections(self, html: str) -> List[Dict]:
        """Extract major page sections"""
        soup = BeautifulSoup(html, 'html.parser')
        sections = []
        
        # Find major containers
        for section_tag in soup.find_all(['section', 'article', 'div'], 
                                         class_=lambda x: x and any(word in str(x).lower() 
                                         for word in ['section', 'container', 'content', 'wrapper'])):
            section_text = section_tag.get_text(strip=True)
            if len(section_text) > 100:  # Only meaningful sections
                sections.append({
                    'tag': section_tag.name,
                    'classes': section_tag.get('class', []),
                    'text': section_text[:1000],
                    'html_snippet': str(section_tag)[:500]
                })
        
        return sections
    
    def extract_structured_data(self, html: str) -> List[Dict]:
        """Extract any structured data (JSON-LD, microdata)"""
        soup = BeautifulSoup(html, 'html.parser')
        structured = []
        
        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured.append({'type': 'json-ld', 'data': data})
            except:
                pass
        
        return structured
    
    def extract_navigation(self, html: str, base_url: str) -> List[Dict]:
        """Extract navigation links"""
        soup = BeautifulSoup(html, 'html.parser')
        nav_items = []
        
        # Find nav elements
        for nav in soup.find_all(['nav', 'header']):
            for link in nav.find_all('a'):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and not href.startswith('http'):
                    href = urljoin(base_url, href)
                
                if href and text:
                    nav_items.append({
                        'text': text,
                        'url': href,
                        'type': 'nav'
                    })
        
        return nav_items
    
    def extract_all_links(self, html: str, base_url: str) -> Dict:
        """Extract all links with categorization"""
        soup = BeautifulSoup(html, 'html.parser')
        all_links = {}
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            
            if not href or not text or len(text) < 2:
                continue
            
            # Make absolute
            if not href.startswith('http') and not href.startswith('mailto'):
                href = urljoin(base_url, href)
            
            # Categorize by domain
            if 'mailto' in href:
                category = 'email'
            elif href.startswith('http'):
                domain = urlparse(href).netloc
                category = domain
            else:
                category = 'relative'
            
            if category not in all_links:
                all_links[category] = []
            
            all_links[category].append({
                'text': text[:100],
                'url': href,
            })
        
        return all_links
    
    def extract_contact_info(self, html: str) -> Dict:
        """Extract contact information"""
        soup = BeautifulSoup(html, 'html.parser')
        contact = {
            'emails': [],
            'phones': [],
            'addresses': [],
        }
        
        # Find emails
        text = soup.get_text()
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        contact['emails'] = list(set(emails))
        
        # Find phone numbers (Indian format)
        phones = re.findall(r'(\+91|0)[- ]?[6-9]\d{4}[- ]?\d{4}', text)
        contact['phones'] = list(set(phones))
        
        # Find addresses (look for keywords)
        for text_block in soup.find_all(['p', 'span', 'div']):
            t = text_block.get_text(strip=True)
            if any(word in t.lower() for word in ['address', 'location', 'mumbai', 'thane']):
                if len(t) > 20 and len(t) < 500:
                    contact['addresses'].append(t)
        
        return contact
    
    def extract_metadata(self, html: str, url: str) -> Dict:
        """Extract page metadata"""
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata = {
            'title': soup.title.string if soup.title else 'Unknown',
            'h1': [h.get_text(strip=True) for h in soup.find_all('h1')],
            'h2': [h.get_text(strip=True) for h in soup.find_all('h2')],
            'paragraphs': [p.get_text(strip=True) for p in soup.find_all('p')],
            'images': [],
            'links': [],
            'tables': [],
            'forms': [],
            'images_count': 0,
            'links_count': 0,
            'tables_count': 0,
            'forms_count': 0,
        }
        
        # Images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                if not src.startswith('http'):
                    src = urljoin(url, src)
                metadata['images'].append({
                    'src': src,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })
        metadata['images_count'] = len(metadata['images'])
        
        # Links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            if href and text:
                if not href.startswith('http'):
                    href = urljoin(url, href)
                metadata['links'].append({
                    'text': text[:100],
                    'url': href
                })
        metadata['links_count'] = len(metadata['links'])
        
        # Tables
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cols = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cols:
                    rows.append(cols)
            if rows:
                metadata['tables'].append(rows)
        metadata['tables_count'] = len(metadata['tables'])
        
        # Forms
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET'),
                'inputs': []
            }
            for inp in form.find_all(['input', 'textarea', 'select']):
                form_data['inputs'].append({
                    'name': inp.get('name', ''),
                    'type': inp.get('type', ''),
                })
            metadata['forms'].append(form_data)
        metadata['forms_count'] = len(metadata['forms'])
        
        return metadata
    
    def process_page(self, url: str) -> Dict:
        """Process single page and return data"""
        html = self.scrape_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        page_data = {
            'source': 'TCET',
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'metadata': self.extract_metadata(html, url),
            'data': {
                'raw_text': soup.get_text(strip=True)[:5000],
                'sections': self.extract_page_sections(html),
                'navigation': self.extract_navigation(html, url),
                'all_links': self.extract_all_links(html, url),
                'contact_info': self.extract_contact_info(html),
                'structured_data': self.extract_structured_data(html)
            }
        }
        
        return page_data
    
    def run(self) -> List[Dict]:
        """Main scraper execution - scrape ALL URLs"""
        if not self.setup_driver():
            return []
        
        try:
            results = []
            
            # Loop through all URLs
            for url in self.urls:
                print(f"\n📍 Scraping: {url}")
                
                page_data = self.process_page(url)
                if not page_data:
                    print(f"⚠️  Failed to scrape {url}")
                    continue
                
                results.append(page_data)
                print(f"✓ {url} extracted")
                
                time.sleep(1)  # Delay between requests
            
            logger.info(f"✓ Extracted {len(results)} TCET pages")
            return results
            
        except Exception as e:
            logger.error(f"✗ Scraper error: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()


def scrape_tcet() -> List[Dict]:
    """Quick function to scrape TCET"""
    scraper = TCETFlexibleScraper(headless=True)
    return scraper.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("TCET FLEXIBLE SCRAPER - ALL PAGES")
    print("="*60)
    print(f"Pages to scrape: {len(TCET_URL)}")
    for url in TCET_URL:
        print(f"  • {url}")
    
    results = scrape_tcet()
    
    if results:
        print(f"\n" + "="*60)
        print(f"✓ Scraped {len(results)} pages successfully")
        print("="*60)
        
        for i, data in enumerate(results, 1):
            print(f"\n{i}. {data['url']}")
            print(f"   Title: {data['metadata'].get('title')}")
            print(f"   Images: {data['metadata'].get('images_count', 0)}")
            print(f"   Links: {data['metadata'].get('links_count', 0)}")
            print(f"   Tables: {data['metadata'].get('tables_count', 0)}")
            print(f"   Emails: {len(data['data'].get('contact_info', {}).get('emails', []))}")
        
        # Save to file for inspection
        with open('tcet_scraped_all_pages.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n✓ Full data saved to: tcet_scraped_all_pages.json")
    else:
        print("✗ Scraping failed")