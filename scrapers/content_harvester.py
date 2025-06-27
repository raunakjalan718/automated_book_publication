from playwright.sync_api import sync_playwright
import os
import time
from pathlib import Path
import re
import json
from typing import Dict, List, Optional, Any
import random
from datetime import datetime

class ContentHarvester:
    """Harvester for web content with customizable extraction patterns."""
    
    def __init__(self, screenshot_dir: str = "./screenshots", delay_range: tuple = (1, 3)):
        """
        Initialize content harvester.
        
        Args:
            screenshot_dir: Directory to store screenshots
            delay_range: Range of random delays between requests
        """
        self.screenshot_dir = screenshot_dir
        Path(self.screenshot_dir).mkdir(exist_ok=True, parents=True)
        self.delay_range = delay_range
        self.extraction_patterns = {
            "default": {
                "content_selector": ".mw-parser-output p",
                "title_selector": "h1, h2, h3",
                "next_chapter_pattern": r"next chapter|chapter\s+\d+|next"
            }
        }
    
    def _random_delay(self):
        """Apply random delay to avoid rate limiting."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
    
    def extract_page_content(self, page, pattern_key: str = "default") -> Dict[str, Any]:
        """
        Extract content from a page using specified pattern.
        
        Args:
            page: Playwright page object
            pattern_key: Key for the extraction pattern to use
            
        Returns:
            Extracted content and metadata
        """
        pattern = self.extraction_patterns.get(pattern_key, self.extraction_patterns["default"])
        
        # Extract main content
        content = page.evaluate(f'''() => {{
            const contentElements = Array.from(document.querySelectorAll('{pattern["content_selector"]}'));
            return contentElements
                .filter(el => !el.closest('.references') && !el.closest('.footnotes'))
                .map(el => el.textContent.trim())
                .join('\\n\\n');
        }}''')
        
        # Extract title
        title = page.evaluate(f'''() => {{
            const titleElements = document.querySelectorAll('{pattern["title_selector"]}');
            for (const el of titleElements) {{
                if (el.textContent.trim()) return el.textContent.trim();
            }}
            return document.title;
        }}''')
        
        # Find next chapter link
        next_link_regex = pattern["next_chapter_pattern"]
        next_link = page.evaluate(f'''() => {{
            const links = Array.from(document.querySelectorAll('a'));
            const pattern = new RegExp('{next_link_regex}', 'i');
            
            for (const link of links) {{
                if (pattern.test(link.textContent.toLowerCase())) {{
                    return link.href;
                }}
            }}
            return null;
        }}''')
        
        return {
            "content": content,
            "title": title,
            "next_url": next_link
        }
    
    def harvest_page(self, url: str, pattern_key: str = "default") -> Dict[str, Any]:
        """
        Harvest content from a single URL.
        
        Args:
            url: URL to harvest content from
            pattern_key: Key for extraction pattern
            
        Returns:
            Dictionary with harvested content and metadata
        """
        with sync_playwright() as p:
            # Use Firefox instead of Chromium to vary fingerprint
            browser = p.firefox.launch(headless=True)
            
            # Use custom viewport size
            page = browser.new_page(viewport={"width": 1100, "height": 800})
            
            # Set custom user agent
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
            })
            
            # Visit the page
            print(f"Harvesting content from: {url}")
            page.goto(url, wait_until="networkidle")
            
            # Take screenshot with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_base = re.sub(r'[^\w]', '_', url.split('/')[-1])
            screenshot_path = os.path.join(
                self.screenshot_dir, 
                f"{file_base}_{timestamp}.png"
            )
            page.screenshot(path=screenshot_path)
            
            # Extract content
            extracted = self.extract_page_content(page, pattern_key)
            
            # Extract chapter number from URL or title
            chapter_match = re.search(r'Chapter_(\d+)', url)
            chapter_num = int(chapter_match.group(1)) if chapter_match else None
            
            browser.close()
            
            return {
                "url": url,
                "title": extracted["title"],
                "content": extracted["content"],
                "screenshot_path": screenshot_path,
                "next_chapter_url": extracted["next_url"],
                "chapter_number": chapter_num,
                "timestamp": datetime.now().isoformat(),
                "harvest_id": f"harvest_{timestamp}_{file_base}"
            }
    
    def harvest_content_sequence(self, start_url: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Harvest a sequence of pages following next links.
        
        Args:
            start_url: URL to start harvesting from
            max_pages: Maximum number of pages to harvest
            
        Returns:
            List of harvested content items
        """
        harvested_items = []
        current_url = start_url
        page_count = 0
        
        while current_url and page_count < max_pages:
            # Harvest the current page
            harvested = self.harvest_page(current_url)
            harvested_items.append(harvested)
            
            # Move to next page if available
            current_url = harvested.get("next_chapter_url")
            page_count += 1
            
            # Apply random delay between requests
            if current_url:
                self._random_delay()
        
        return harvested_items
