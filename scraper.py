"""
Web scraper for vymanga.co.
Handles fetching manga metadata, chapter lists, and page images.
"""

import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Dict, Any
import re

from models import Manga, Chapter, Page
from utils import logger, is_valid_image_url


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
        chapters = []

        # Find chapter list container
        chapter_list_div = soup.find('div', class_='list')
        if not chapter_list_div:
            logger.warning("No chapter list found")
            return chapters

        # Find all chapter links
        chapter_links = chapter_list_div.find_all('a', class_='list-group-item')

        for link in chapter_links:
            try:
                # Extract chapter number from text
                chapter_text = link.get_text(strip=True)
                chapter_match = re.search(r'Chapter\s+(\d+(?:\.\d+)?)', chapter_text, re.IGNORECASE)

                if not chapter_match:
                    continue

                chapter_number = float(chapter_match.group(1))

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
                    title=f"Chapter {chapter_number}",
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
        Scrape all pages/images from a chapter.

        Args:
            chapter: Chapter object to scrape pages for

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Scraping pages for {chapter.title}")
        soup = self._make_request(chapter.url)

        if not soup:
            return False

        try:
            # Look for the vertical view toggle button and click it
            if soup:
                view_toggle = soup.find('a', {
                    'class': 'view-control',
                    'onclick': lambda x: x and 'setView(1)' in str(x)
                })

                if view_toggle:
                    logger.info("Switching to vertical view...")
                    # Extract the onclick URL or try to simulate the click
                    onclick = view_toggle.get('onclick', '')
                    if 'setView(1)' in onclick:
                        # Try to get the vertical view URL
                        vertical_url = chapter.url
                        if '?' in vertical_url:
                            vertical_url += '&view=vertical'
                        else:
                            vertical_url += '?view=vertical'

                        soup = self._make_request(vertical_url)
                        if not soup:
                            logger.warning("Failed to switch to vertical view, continuing with current view")

            # Find all image containers
            if not soup:
                return False

            page_containers = soup.find_all('div', class_='hview')

            if not page_containers:
                logger.warning("No page containers found")
                return False

            pages_found = 0
            for i, container in enumerate(page_containers):
                try:
                    # Find image within the container
                    img = container.find('img')
                    if not img:
                        continue

                    # Get image URL
                    img_url = img.get('data-src') or img.get('src')
                    if not img_url:
                        continue

                    # Validate image URL
                    if not is_valid_image_url(img_url):
                        continue

                    # Handle relative URLs
                    if img_url.startswith('/'):
                        img_url = urljoin(self.base_url, img_url)
                    elif not img_url.startswith('http'):
                        img_url = urljoin(chapter.url, img_url)

                    # Add page to chapter
                    page = chapter.add_page(img_url, i + 1)
                    pages_found += 1

                except Exception as e:
                    logger.warning(f"Error parsing page {i + 1}: {e}")
                    continue

            logger.info(f"Found {pages_found} pages for {chapter.title}")
            return pages_found > 0

        except Exception as e:
            logger.error(f"Error scraping chapter pages: {e}")
            return False

    def scrape_manga_with_chapters(self, manga_url: str) -> Optional[Manga]:
        """
        Scrape complete manga including all chapters and pages.

        Args:
            manga_url: URL of the manga page

        Returns:
            Complete Manga object or None if failed
        """
        logger.info(f"Starting complete scrape of: {manga_url}")

        # First scrape basic manga info
        manga = self.scrape_manga_info(manga_url)
        if not manga:
            return None

        # Then scrape all chapters
        logger.info(f"Scraping {len(manga.chapters)} chapters...")
        for i, chapter in enumerate(manga.chapters):
            logger.info(f"Scraping chapter {i + 1}/{len(manga.chapters)}: {chapter.title}")
            success = self.scrape_chapter_pages(chapter)

            if not success:
                logger.warning(f"Failed to scrape pages for {chapter.title}")

            # Add small delay between chapters to be respectful
            if i < len(manga.chapters) - 1:
                time.sleep(1)

        logger.info(f"Completed scraping manga: {manga.title}")
        return manga

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