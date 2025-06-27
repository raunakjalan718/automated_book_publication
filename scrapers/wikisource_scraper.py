from playwright.sync_api import sync_playwright
import os
import time
from pathlib import Path
import re
from typing import Dict, List, Optional
from config import SCREENSHOTS_DIR, WIKISOURCE_BASE_URL, INITIAL_CHAPTER_URL

class WikiSourceScraper:
    """Scraper for wiki source content."""
    
    def __init__(self):
        """Initialize the scraper with directory for screenshots."""
        self.screenshots_dir = SCREENSHOTS_DIR
        Path(self.screenshots_dir).mkdir(exist_ok=True, parents=True)
        
    def extract_chapter_content(self, page) -> str:
        """Extract the main text content from the page."""
        content = page.evaluate('''() => {
            const mainContent = document.querySelector('.mw-parser-output');
            if (!mainContent) return '';
            
            // Get paragraphs but exclude notes or references
            const paragraphs = Array.from(mainContent.querySelectorAll('p'))
                .filter(p => !p.closest('.references') && !p.closest('.footnotes'));
            
            return paragraphs.map(p => p.textContent.trim()).join('\\n\\n');
        }''')
        
        return content
    
    def find_next_chapter_link(self, page) -> Optional[str]:
        """Locate the link to the next chapter if available."""
        next_link = page.evaluate('''() => {
            // Look for navigation patterns
            const navLinks = document.querySelectorAll('a');
            for (const link of navLinks) {
                const text = link.textContent.toLowerCase();
                if (text.includes('next chapter') || 
                    text.includes('chapter') && text.includes('next') ||
                    text === 'next' ||
                    text.match(/chapter\\s+\\d+/i)) {
                    return link.href;
                }
            }
            return null;
        }''')
        
        return next_link
    
    def get_chapter_title(self, page) -> str:
        """Extract the chapter title from the page."""
        title = page.evaluate('''() => {
            const headings = document.querySelectorAll('h1, h2, h3');
            for (const heading of headings) {
                if (heading.textContent.trim().length > 0) {
                    return heading.textContent.trim();
                }
            }
            return document.title;
        }''')
        
        return title
    
    def scrape_chapter(self, url: str) -> Dict:
        """Scrape a single chapter and return its content and metadata."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            print(f"Scraping page: {url}")
            page.goto(url)
            time.sleep(2)  # Allow page to fully load
            
            # Take screenshot
            screenshot_path = os.path.join(
                self.screenshots_dir, 
                f"chapter_{int(time.time())}.png"
            )
            page.screenshot(path=screenshot_path)
            
            # Extract chapter information
            title = self.get_chapter_title(page)
            content = self.extract_chapter_content(page)
            next_chapter_url = self.find_next_chapter_link(page)
            
            # Extract chapter number from URL or title
            chapter_match = re.search(r'Chapter_(\d+)', url)
            chapter_num = int(chapter_match.group(1)) if chapter_match else None
            
            browser.close()
            
            return {
                "url": url,
                "title": title,
                "content": content,
                "screenshot_path": screenshot_path,
                "next_chapter_url": next_chapter_url,
                "chapter_number": chapter_num
            }
    
    def scrape_book(self, start_url: str = None) -> List[Dict]:
        """Scrape all chapters of a book starting from the given URL."""
        if start_url is None:
            start_url = INITIAL_CHAPTER_URL
            
        chapters = []
        current_url = start_url
        
        while current_url:
            chapter_data = self.scrape_chapter(current_url)
            chapters.append(chapter_data)
            
            # Move to next chapter if available
            current_url = chapter_data.get("next_chapter_url")
            
            # Add delay between requests
            if current_url:
                time.sleep(1.5)  # Be respectful to the server
        
        return chapters
