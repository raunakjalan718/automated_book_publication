import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime
import config

class WikiSourceScraper:
    """Class for scraping content from Wikisource pages"""
    
    def __init__(self):
        self.screenshots_folder = config.SCREENSHOTS_DIR
    
    async def fetch_chapter_content(self, url=None):
        """
        Scrapes chapter content and takes a screenshot
        
        Args:
            url: The chapter URL to scrape (defaults to config URL if None)
            
        Returns:
            dict: Chapter data including title, content, and screenshot path
        """
        if not url:
            url = config.INITIAL_CHAPTER_URL
            
        # Use a unique timestamp for the screenshot filename
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        chapter_identifier = url.split('/')[-1]
        screenshot_filename = f"{chapter_identifier}_{current_time}.png"
        screenshot_path = os.path.join(self.screenshots_folder, screenshot_filename)
        
        print(f"Starting to scrape content from {url}")
        
        async with async_playwright() as playwright:
            # Launch browser
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to URL
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            # Extract chapter title
            title_element = await page.query_selector(".firstHeading")
            chapter_title = await title_element.inner_text() if title_element else "Unknown Chapter"
            
            # Extract chapter content
            content_element = await page.query_selector("#mw-content-text")
            raw_content = await content_element.inner_text() if content_element else ""
            
            # Capture screenshot
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # Clean up
            await browser.close()
            
            # Return structured data
            return {
                "title": chapter_title,
                "content": raw_content,
                "screenshot_path": screenshot_path,
                "source_url": url,
                "timestamp": current_time
            }
    
    async def get_chapter_links(self, book_num=1):
        """
        Retrieves all chapter URLs for a specific book
        
        Args:
            book_num: Book number to scrape
            
        Returns:
            list: URLs of chapters in the book
        """
        book_url = f"{config.WIKISOURCE_BASE_URL}/Book_{book_num}"
        chapter_urls = []
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            
            await page.goto(book_url)
            
            # Find all links containing "Chapter" in the href
            links = await page.query_selector_all('a[href*="/Chapter_"]')
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    full_url = f"https://en.wikisource.org{href}"
                    chapter_urls.append(full_url)
            
            await browser.close()
        
        return chapter_urls
