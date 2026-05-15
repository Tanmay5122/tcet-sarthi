"""Base scraper - abstract class for all scrapers"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, source: str, timeout: int = 30, retry_count: int = 3):
        self.source = source
        self.timeout = timeout
        self.retry_count = retry_count
        self.opportunities = []
        
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """Scrape data from source. Return list of opportunity dicts."""
        pass
    
    @abstractmethod
    def parse(self, raw_data) -> List[Dict]:
        """Parse raw data into opportunity dictionaries."""
        pass
    
    def validate(self, opp: Dict) -> bool:
        """Validate opportunity has required fields"""
        required = ['title', 'organization', 'deadline', 'source_url']
        return all(field in opp and opp[field] for field in required)
    
    def generate_hash(self, title: str, org: str, deadline: datetime) -> str:
        """Generate MD5 hash for deduplication"""
        key = f"{title.lower().strip()}|{org.lower().strip()}|{deadline.strftime('%Y-%m-%d')}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def run(self) -> List[Dict]:
        """Main execution flow"""
        try:
            logger.info(f"Scraping {self.source}...")
            raw_data = self.scrape()
            
            opportunities = self.parse(raw_data)
            
            # Validate + add hash
            valid_opps = []
            for opp in opportunities:
                if self.validate(opp):
                    opp['source_hash'] = self.generate_hash(
                        opp['title'], 
                        opp['organization'], 
                        opp['deadline']
                    )
                    opp['source'] = self.source
                    valid_opps.append(opp)
            
            logger.info(f"✓ Scraped {len(valid_opps)} opportunities from {self.source}")
            return valid_opps
            
        except Exception as e:
            logger.error(f"✗ Scraper error: {e}")
            return []
        