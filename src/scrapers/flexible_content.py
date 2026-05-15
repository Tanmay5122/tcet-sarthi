"""
FlexibleContent - Universal scraping model
Captures raw + parsed data from any website
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class FlexibleContent:
    """Generic data container for scraped content"""
    
    def __init__(self, source: str, url: str):
        self.source = source
        self.url = url
        self.scraped_at = datetime.now()
        
        # Raw content
        self.raw_html = None
        self.raw_text = None
        
        # Parsed data (flexible)
        self.data = {}
        
        # Metadata
        self.metadata = {
            'title': None,
            'description': None,
            'images': [],
            'links': [],
            'tables': [],
            'forms': [],
        }
    
    def extract_text(self, html: str) -> str:
        """Extract all text from HTML"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script/style
        for tag in soup(['script', 'style']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        return ' '.join(text.split())
    
    def extract_links(self, html: str) -> List[Dict]:
        """Extract all links"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Make absolute URL if relative
            if href and not href.startswith('http'):
                from urllib.parse import urljoin
                href = urljoin(self.url, href)
            
            if href and text:
                links.append({
                    'text': text[:200],
                    'url': href,
                    'title': link.get('title', '')
                })
        
        return links
    
    def extract_images(self, html: str) -> List[Dict]:
        """Extract all images"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            
            # Make absolute URL
            if src and not src.startswith('http'):
                from urllib.parse import urljoin
                src = urljoin(self.url, src)
            
            if src:
                images.append({
                    'src': src,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                })
        
        return images
    
    def extract_tables(self, html: str) -> List[List[Dict]]:
        """Extract all table data"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        tables = []
        for table in soup.find_all('table'):
            rows = []
            
            # Get headers
            headers = []
            for th in table.find_all('th'):
                headers.append(th.get_text(strip=True))
            
            # Get rows
            for tr in table.find_all('tr'):
                if tr.find('th'):
                    continue  # Skip header row
                
                cells = []
                for td in tr.find_all('td'):
                    cells.append(td.get_text(strip=True))
                
                if cells:
                    if headers:
                        row_dict = dict(zip(headers, cells))
                    else:
                        row_dict = {'col_' + str(i): cell for i, cell in enumerate(cells)}
                    
                    rows.append(row_dict)
            
            if rows:
                tables.append(rows)
        
        return tables
    
    def extract_forms(self, html: str) -> List[Dict]:
        """Extract all form information"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        forms = []
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET').upper(),
                'fields': []
            }
            
            for field in form.find_all(['input', 'select', 'textarea']):
                field_info = {
                    'name': field.get('name', ''),
                    'type': field.get('type', 'text'),
                    'label': None,
                }
                form_data['fields'].append(field_info)
            
            if form_data['fields']:
                forms.append(form_data)
        
        return forms
    
    def extract_metadata(self, html: str) -> Dict:
        """Extract page metadata"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        meta = {
            'title': soup.title.string if soup.title else None,
            'h1': [],
            'h2': [],
            'paragraphs': [],
        }
        
        # Extract headers
        for h1 in soup.find_all('h1'):
            meta['h1'].append(h1.get_text(strip=True)[:200])
        
        for h2 in soup.find_all('h2'):
            meta['h2'].append(h2.get_text(strip=True)[:200])
        
        # Extract first 5 paragraphs
        for p in soup.find_all('p')[:5]:
            text = p.get_text(strip=True)
            if len(text) > 20:
                meta['paragraphs'].append(text[:500])
        
        return meta
    
    def process(self, html: str):
        """Process HTML and extract all data"""
        self.raw_html = html
        self.raw_text = self.extract_text(html)
        
        self.metadata = self.extract_metadata(html)
        self.metadata['images'] = self.extract_images(html)
        self.metadata['links'] = self.extract_links(html)
        self.metadata['tables'] = self.extract_tables(html)
        self.metadata['forms'] = self.extract_forms(html)
        
        self.data = {
            'raw_text': self.raw_text[:5000],  # First 5000 chars
            'metadata': self.metadata,
            'statistics': {
                'text_length': len(self.raw_text),
                'links_count': len(self.metadata['links']),
                'images_count': len(self.metadata['images']),
                'tables_count': len(self.metadata['tables']),
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'source': self.source,
            'url': self.url,
            'scraped_at': self.scraped_at.isoformat(),
            'data': self.data,
            'metadata': self.metadata,
        }
    
    def __repr__(self):
        return f"<FlexibleContent source={self.source} url={self.url[:50]}>"