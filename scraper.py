"""
Web scraper for vymanga.co.
Handles fetching manga metadata, chapter lists, and page images.
"""

import requests
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Dict, Any
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import Manga, Chapter, Page
from utils import logger, is_valid_image_url

# Try to import playwright, fallback to requests if not available
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Chapter image scraping may not work properly.")


class VymangaScraper:
    """Scraper for vymanga.co manga website."""

    def __init__(self, base_url: str = "https://vymanga.co"):
        """
        Initialize the scraper.

        Args:
            base_url: Base URL for vymanga.co
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _make_request(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Make HTTP request with retries.

        Args:
            url: URL to request
            retries: Number of retry attempts

        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(retries):
            try:
                logger.debug(f"Making request to: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Handle adult content warning on first visit
                if "closeWarningContent" in response.text and attempt == 0:
                    logger.info("Handling adult content warning...")
                    # Try to accept the warning
                    soup = BeautifulSoup(response.text, 'html.parser')
                    accept_button = soup.find('button', {
                        'class': 'btn btn-primary',
                        'onclick': lambda x: x and 'closeWarningContent' in str(x)
                    })

                    if accept_button:
                        # Extract the onclick URL or try to simulate the click
                        onclick = accept_button.get('onclick', '')
                        if 'closeWarningContent();saveWarning()' in onclick:
                            # Try to post to accept the warning
                            warning_response = self.session.post(
                                url,
                                data={'accept_warning': '1'},
                                timeout=10
                            )
                            if warning_response.status_code == 200:
                                response = warning_response

                return BeautifulSoup(response.text, 'html.parser')

            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None

    def scrape_manga_info(self, manga_url: str) -> Optional[Manga]:
        """
        Scrape manga information from the given URL.

        Args:
            manga_url: URL of the manga page

        Returns:
            Manga object with scraped information or None if failed
        """
        logger.info(f"Scraping manga info from: {manga_url}")
        soup = self._make_request(manga_url)

        if not soup:
            return None

        try:
            # Extract basic information
            manga = Manga(
                title="",
                url=manga_url,
                author="",
                status="",
                genres=[],
                summary="",
                cover_url=""
            )

            # Extract title
            title_elem = soup.find('h1', class_='title')
            if title_elem:
                manga.title = title_elem.get_text(strip=True)

            # Extract cover image
            cover_div = soup.find('div', class_='img-manga')
            if cover_div:
                cover_img = cover_div.find('img')
                if cover_img and cover_img.get('src'):
                    manga.cover_url = urljoin(manga_url, cover_img['src'])

            # Extract metadata from col-md-7 div
            info_div = soup.find('div', class_='col-md-7')
            if info_div:
                # Extract author
                author_elem = info_div.find('a', href=re.compile(r'/author/'))
                if author_elem:
                    manga.author = author_elem.get_text(strip=True)

                # Extract status
                status_elem = info_div.find('span', class_='text-ongoing')
                if status_elem:
                    manga.status = status_elem.get_text(strip=True)

                # Extract genres
                genre_badges = info_div.find_all('a', class_='badge')
                for badge in genre_badges:
                    genre_text = badge.get_text(strip=True)
                    if genre_text:
                        manga.genres.append(genre_text)

            # Extract summary
            summary_elem = soup.find('p', class_='content')
            if summary_elem:
                manga.summary = summary_elem.get_text(strip=True)

            # Extract chapters
            chapters = self._scrape_chapter_list(soup, manga_url)
            manga.chapters = chapters

            logger.info(f"Successfully scraped manga: {manga.title} ({len(chapters)} chapters)")
            return manga

        except Exception as e:
            logger.error(f"Error scraping manga info: {e}")
            return None

    def _scrape_chapter_list(self, soup: BeautifulSoup, manga_url: str) -> List[Chapter]:
        """
        Scrape chapter list from the manga page.

        Args:
            soup: BeautifulSoup object of the manga page
            manga_url: Base manga URL

        Returns:
            List of Chapter objects
        """
        
        # Find chapter list container
        chapter_list_div = soup.find('div', class_='list')
        if not chapter_list_div:
            logger.warning("No chapter list found")

        # Find all chapter links
        if chapter_list_div:
            chapter_links = chapter_list_div.find_all('a', class_='list-group-item')
        else:
            chapter_links = soup.select('a[id^=chapter-]')
        
        if not chapter_links:
            logger.warning("No chapters found")
            return []
        
        chapters = []
        for link in reversed(chapter_links): # from old to new
            try:
                # Extract chapter number from id
                chapter_match = re.findall(r'chapter-(\d+(?:\.\d+)?)', link.get('id'))
                if chapter_match:
                    chapter_number = float(chapter_match[0])
                else:
                    # Fallback to last number
                    chapter_number = 0.0 if not chapters else chapters[-1].number + 0.001

                # Extract chapter title - everything after "Chapter X.X : "
                chapter_text = link.get_text(strip=True)
                title_match = re.search(r'Chapter\s+\d+(?:\.\d+)?\s*:\s*(.+)', chapter_text, re.IGNORECASE)
                if title_match:
                    full_title = title_match.group(1).strip()

                    # If the title starts with "Ch X.X :", remove it to avoid duplication
                    ch_prefix_match = re.match(r'Ch\s+\d+(?:\.\d+)?\s*:\s*(.+)', full_title, re.IGNORECASE)
                    if ch_prefix_match:
                        chapter_title = ch_prefix_match.group(1).strip()
                    else:
                        chapter_title = full_title
                else:
                    # Fallback to default title if no title found
                    chapter_title = f"Chapter {chapter_number}"

                # Extract chapter URL
                chapter_url = link.get('href')
                if not chapter_url:
                    continue

                # Handle relative URLs
                if chapter_url.startswith('/'):
                    chapter_url = urljoin(self.base_url, chapter_url)
                elif not chapter_url.startswith('http'):
                    chapter_url = urljoin(manga_url, chapter_url)

                # Extract date if available
                date_elem = link.find('p', class_='text-right')
                published_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # Try to parse relative dates like "7 hours ago"
                    if 'ago' in date_text.lower():
                        published_date = None  # For now, skip parsing relative dates

                chapter = Chapter(
                    title=chapter_title,
                    number=chapter_number,
                    url=chapter_url,
                    published_date=published_date
                )

                chapters.append(chapter)

            except Exception as e:
                logger.warning(f"Error parsing chapter: {e}")
                continue

        # Sort chapters by number (ascending)
        chapters.sort(key=lambda x: x.number)
        logger.info(f"Found {len(chapters)} chapters")
        return chapters

    def scrape_chapter_pages(self, chapter: Chapter) -> bool:
        """
        Scrape all pages/images from a chapter using Playwright.

        Args:
            chapter: Chapter object to scrape pages for

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Scraping pages for {chapter.title}")

        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available. Cannot scrape chapter images.")
            logger.info("Install playwright: pip install playwright")
            logger.info("Then run: playwright install")
            return False

        try:
            # Import here to ensure it's available
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Go to chapter URL
                logger.debug(f"Loading chapter URL: {chapter.url}")
                page.goto(chapter.url, wait_until="domcontentloaded")
                time.sleep(3)

                # Click "Change To Vertical View" button
                try:
                    view_toggle = page.query_selector("a.view-control")
                    if view_toggle:
                        view_toggle.click()
                        time.sleep(2)
                        logger.debug("Switched to vertical view")
                except Exception as e:
                    logger.debug(f"Could not click vertical view button: {e}")

                # Grab all images inside #main_reader
                image_elements = page.query_selector_all("#main_reader img")
                logger.info(f"Found {len(image_elements)} images")

                if not image_elements:
                    logger.warning("No images found in chapter")
                    browser.close()
                    return False

                pages_found = 0
                for idx, img in enumerate(image_elements, start=1):
                    try:
                        # Get image URL from data-src or src attribute
                        img_url = img.get_attribute("data-src") or img.get_attribute("src")

                        logger.debug(f"Image {idx}: {img_url}")

                        # Skip loading gifs and invalid URLs
                        if not img_url:
                            logger.debug(f"Skipping image {idx}: empty URL")
                            continue

                        if "loading.gif" in img_url:
                            logger.debug(f"Skipping image {idx}: loading gif")
                            continue

                        # Validate image URL
                        is_valid = is_valid_image_url(img_url)
                        logger.debug(f"Image {idx} validation result: {is_valid}")

                        if not is_valid:
                            logger.debug(f"Skipping image {idx}: invalid image URL")
                            continue

                        # Handle relative URLs
                        if img_url.startswith('/'):
                            img_url = urljoin(self.base_url, img_url)
                        elif not img_url.startswith('http'):
                            img_url = urljoin(chapter.url, img_url)

                        # Add page to chapter
                        page_obj = chapter.add_page(img_url, idx)
                        pages_found += 1
                        logger.debug(f"Added page {idx}: {img_url}")

                    except Exception as e:
                        logger.warning(f"Error processing image {idx}: {e}")
                        continue

                browser.close()
                logger.info(f"Successfully scraped {pages_found} pages for {chapter.title}")
                return pages_found > 0

        except Exception as e:
            logger.error(f"Error scraping chapter pages with Playwright: {e}")
            return False

    def scrape_manga_with_chapters(self, manga_url: str, max_workers: int = 3) -> Optional[Manga]:
        """
        Scrape complete manga including all chapters and pages using parallel processing.

        Args:
            manga_url: URL of the manga page
            max_workers: Maximum number of concurrent chapter scrapers

        Returns:
            Complete Manga object or None if failed
        """
        logger.info(f"Starting complete scrape of: {manga_url}")

        # First scrape basic manga info
        manga = self.scrape_manga_info(manga_url)
        if not manga:
            return None

        # Then scrape all chapters in parallel
        total_chapters = len(manga.chapters)
        logger.info(f"Scraping {total_chapters} chapters using {max_workers} parallel workers...")

        successful_chapters = 0
        failed_chapters = []

        # Use ThreadPoolExecutor for parallel chapter scraping
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chapter scraping tasks
            future_to_chapter = {
                executor.submit(self.scrape_chapter_pages, chapter): chapter
                for chapter in manga.chapters
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_chapter):
                chapter = future_to_chapter[future]
                try:
                    success = future.result()
                    if success:
                        successful_chapters += 1
                        logger.info(f"✓ Completed: {chapter.title}")
                    else:
                        failed_chapters.append(chapter.title)
                        logger.warning(f"✗ Failed: {chapter.title}")

                except Exception as e:
                    failed_chapters.append(chapter.title)
                    logger.error(f"✗ Error scraping {chapter.title}: {e}")

        # Log summary
        logger.info(f"Chapter scraping completed: {successful_chapters}/{total_chapters} successful")
        if failed_chapters:
            logger.warning(f"Failed chapters: {', '.join(failed_chapters)}")

        logger.info(f"Completed scraping manga: {manga.title}")
        return manga

    def scrape_selected_chapters(self, chapters: List[Chapter], max_workers: int = 3) -> bool:
        """
        Scrape pages for selected chapters only using parallel processing.

        Args:
            chapters: List of Chapter objects to scrape pages for
            max_workers: Maximum number of concurrent chapter scrapers

        Returns:
            True if all chapters were scraped successfully, False otherwise
        """
        if not chapters:
            logger.warning("No chapters provided for scraping")
            return False

        logger.info(f"Scraping {len(chapters)} selected chapters using {max_workers} parallel workers...")

        successful_chapters = 0
        failed_chapters = []

        # Use ThreadPoolExecutor for parallel chapter scraping
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chapter scraping tasks
            future_to_chapter = {
                executor.submit(self.scrape_chapter_pages, chapter): chapter
                for chapter in chapters
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_chapter):
                chapter = future_to_chapter[future]
                try:
                    success = future.result()
                    if success:
                        successful_chapters += 1
                        logger.info(f"✓ Completed: {chapter.title}")
                    else:
                        failed_chapters.append(chapter.title)
                        logger.warning(f"✗ Failed: {chapter.title}")

                except Exception as e:
                    failed_chapters.append(chapter.title)
                    logger.error(f"✗ Error scraping {chapter.title}: {e}")

        # Log summary
        logger.info(f"Chapter scraping completed: {successful_chapters}/{len(chapters)} successful")
        if failed_chapters:
            logger.warning(f"Failed chapters: {', '.join(failed_chapters)}")

        return len(failed_chapters) == 0

    def search_manga(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for manga by title.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of manga search results
        """
        logger.info(f"Searching for: {query}")

        # Note: vymanga.co doesn't seem to have a search API
        # This is a placeholder for future implementation
        logger.warning("Search functionality not implemented for vymanga.co")
        return []
