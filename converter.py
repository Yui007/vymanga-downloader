"""
Image conversion utilities for manga.
Converts downloaded images to PDF and CBZ formats.
"""

import os
from typing import List, Optional, Tuple
from pathlib import Path
import zipfile
from PIL import Image
import tempfile

from models import Chapter, Manga
from utils import logger, ensure_directory, format_bytes


class MangaConverter:
    """Handles conversion of manga images to various formats."""

    def __init__(self, quality: str = "high"):
        """
        Initialize the converter.

        Args:
            quality: Image quality for conversion (high, medium, low)
        """
        self.quality = quality
        self.quality_settings = {
            'high': {'jpeg_quality': 100, 'resize_factor': 1.0},
            'medium': {'jpeg_quality': 85, 'resize_factor': 0.8},
            'low': {'jpeg_quality': 75, 'resize_factor': 0.6}
        }

    def convert_chapter_to_pdf(self, chapter: Chapter, output_path: Optional[str] = None) -> bool:
        """
        Convert a chapter's images to PDF format.

        Args:
            chapter: Chapter object with downloaded images
            output_path: Output path for the PDF (optional)

        Returns:
            True if conversion successful, False otherwise
        """
        if not chapter.download_path or not os.path.exists(chapter.download_path):
            logger.error(f"Chapter download path not found: {chapter.download_path}")
            return False

        # Find all image files in the chapter directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_files = []

        for file_path in Path(chapter.download_path).iterdir():
            if file_path.suffix.lower() in image_extensions and file_path.is_file():
                image_files.append(str(file_path))

        if not image_files:
            logger.warning(f"No image files found in {chapter.download_path}")
            return False

        # Sort images by filename (assuming they follow page_001.jpg pattern)
        image_files.sort()

        # Set output path
        if not output_path:
            output_path = os.path.join(chapter.download_path, f"{chapter.chapter_folder_name}.pdf")

        try:
            logger.info(f"Converting {len(image_files)} images to PDF: {output_path}")

            # Open first image to get dimensions
            first_image = Image.open(image_files[0])
            width, height = first_image.size

            # Create PDF with appropriate size
            pdf_images = []
            for image_path in image_files:
                try:
                    img = Image.open(image_path)

                    # Convert to RGB if necessary (PDF requires RGB)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Resize if needed
                    settings = self.quality_settings[self.quality]
                    if settings['resize_factor'] != 1.0:
                        new_width = int(width * settings['resize_factor'])
                        new_height = int(height * settings['resize_factor'])
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    pdf_images.append(img)

                except Exception as e:
                    logger.warning(f"Error processing image {image_path}: {e}")
                    continue

            if not pdf_images:
                logger.error("No valid images found for PDF conversion")
                return False

            # Save as PDF
            settings = self.quality_settings[self.quality]
            pdf_images[0].save(
                output_path,
                save_all=True,
                append_images=pdf_images[1:],
                quality=settings['jpeg_quality']
            )

            # Close all images
            for img in pdf_images:
                img.close()

            file_size = os.path.getsize(output_path)
            logger.info(f"PDF created successfully: {output_path} ({format_bytes(file_size)})")

            return True

        except Exception as e:
            logger.error(f"Error converting chapter to PDF: {e}")
            return False

    def convert_chapter_to_cbz(self, chapter: Chapter, output_path: Optional[str] = None) -> bool:
        """
        Convert a chapter's images to CBZ format (ZIP archive).

        Args:
            chapter: Chapter object with downloaded images
            output_path: Output path for the CBZ (optional)

        Returns:
            True if conversion successful, False otherwise
        """
        if not chapter.download_path or not os.path.exists(chapter.download_path):
            logger.error(f"Chapter download path not found: {chapter.download_path}")
            return False

        # Find all image files in the chapter directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_files = []

        for file_path in Path(chapter.download_path).iterdir():
            if file_path.suffix.lower() in image_extensions and file_path.is_file():
                image_files.append(str(file_path))

        if not image_files:
            logger.warning(f"No image files found in {chapter.download_path}")
            return False

        # Sort images by filename
        image_files.sort()

        # Set output path
        if not output_path:
            output_path = os.path.join(chapter.download_path, f"{chapter.chapter_folder_name}.cbz")

        try:
            logger.info(f"Converting {len(image_files)} images to CBZ: {output_path}")

            # Create CBZ (ZIP) file
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
                for image_path in image_files:
                    try:
                        # Add file to archive with just the filename (no path)
                        filename = os.path.basename(image_path)
                        cbz_file.write(image_path, filename)
                        logger.debug(f"Added to CBZ: {filename}")

                    except Exception as e:
                        logger.warning(f"Error adding {image_path} to CBZ: {e}")
                        continue

            file_size = os.path.getsize(output_path)
            logger.info(f"CBZ created successfully: {output_path} ({format_bytes(file_size)})")

            return True

        except Exception as e:
            logger.error(f"Error converting chapter to CBZ: {e}")
            return False

    def convert_manga_to_pdf(self, manga: Manga, output_path: Optional[str] = None,
                           chapter_range: Optional[Tuple[float, float]] = None) -> bool:
        """
        Convert entire manga or chapter range to a single PDF.

        Args:
            manga: Manga object with downloaded chapters
            output_path: Output path for the PDF (optional)
            chapter_range: Tuple of (start_chapter, end_chapter) to convert (optional)

        Returns:
            True if conversion successful, False otherwise
        """
        if not manga.download_path or not os.path.exists(manga.download_path):
            logger.error(f"Manga download path not found: {manga.download_path}")
            return False

        # Filter chapters if range specified
        chapters_to_convert = manga.chapters
        if chapter_range:
            chapters_to_convert = manga.get_chapters_in_range(chapter_range[0], chapter_range[1])

        if not chapters_to_convert:
            logger.warning("No chapters found to convert")
            return False

        # Set output path
        if not output_path:
            range_str = f"_Chapters_{chapter_range[0]}-{chapter_range[1]}" if chapter_range else ""
            output_path = os.path.join(manga.download_path, f"{manga.title}{range_str}.pdf")

        try:
            logger.info(f"Converting manga to PDF: {output_path}")

            # Collect all images from all chapters
            all_images = []
            for chapter in chapters_to_convert:
                if not chapter.download_path or not os.path.exists(chapter.download_path):
                    logger.warning(f"Chapter path not found: {chapter.title}")
                    continue

                # Find image files in chapter directory
                image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                chapter_images = []

                for file_path in sorted(Path(chapter.download_path).iterdir()):
                    if file_path.suffix.lower() in image_extensions and file_path.is_file():
                        chapter_images.append(str(file_path))

                if chapter_images:
                    all_images.extend(chapter_images)
                    logger.debug(f"Added {len(chapter_images)} images from {chapter.title}")

            if not all_images:
                logger.error("No images found for PDF conversion")
                return False

            logger.info(f"Converting {len(all_images)} images from {len(chapters_to_convert)} chapters")

            # Open first image to get dimensions
            first_image = Image.open(all_images[0])
            width, height = first_image.size

            # Create PDF images list
            pdf_images = []
            for image_path in all_images:
                try:
                    img = Image.open(image_path)

                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Resize if needed
                    settings = self.quality_settings[self.quality]
                    if settings['resize_factor'] != 1.0:
                        new_width = int(width * settings['resize_factor'])
                        new_height = int(height * settings['resize_factor'])
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    pdf_images.append(img)

                except Exception as e:
                    logger.warning(f"Error processing image {image_path}: {e}")
                    continue

            if not pdf_images:
                logger.error("No valid images found for PDF conversion")
                return False

            # Save as PDF
            settings = self.quality_settings[self.quality]
            pdf_images[0].save(
                output_path,
                save_all=True,
                append_images=pdf_images[1:],
                quality=settings['jpeg_quality']
            )

            # Close all images
            for img in pdf_images:
                img.close()

            file_size = os.path.getsize(output_path)
            logger.info(f"Manga PDF created successfully: {output_path} ({format_bytes(file_size)})")

            return True

        except Exception as e:
            logger.error(f"Error converting manga to PDF: {e}")
            return False

    def convert_manga_to_cbz(self, manga: Manga, output_path: Optional[str] = None,
                           chapter_range: Optional[Tuple[float, float]] = None) -> bool:
        """
        Convert entire manga or chapter range to CBZ format.

        Args:
            manga: Manga object with downloaded chapters
            output_path: Output path for the CBZ (optional)
            chapter_range: Tuple of (start_chapter, end_chapter) to convert (optional)

        Returns:
            True if conversion successful, False otherwise
        """
        if not manga.download_path or not os.path.exists(manga.download_path):
            logger.error(f"Manga download path not found: {manga.download_path}")
            return False

        # Filter chapters if range specified
        chapters_to_convert = manga.chapters
        if chapter_range:
            chapters_to_convert = manga.get_chapters_in_range(chapter_range[0], chapter_range[1])

        if not chapters_to_convert:
            logger.warning("No chapters found to convert")
            return False

        # Set output path
        if not output_path:
            range_str = f"_Chapters_{chapter_range[0]}-{chapter_range[1]}" if chapter_range else ""
            output_path = os.path.join(manga.download_path, f"{manga.title}{range_str}.cbz")

        try:
            logger.info(f"Converting manga to CBZ: {output_path}")

            # Collect all images from all chapters
            all_images = []
            for chapter in chapters_to_convert:
                if not chapter.download_path or not os.path.exists(chapter.download_path):
                    logger.warning(f"Chapter path not found: {chapter.title}")
                    continue

                # Find image files in chapter directory
                image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

                for file_path in sorted(Path(chapter.download_path).iterdir()):
                    if file_path.suffix.lower() in image_extensions and file_path.is_file():
                        all_images.append(str(file_path))

            if not all_images:
                logger.error("No images found for CBZ conversion")
                return False

            logger.info(f"Converting {len(all_images)} images from {len(chapters_to_convert)} chapters")

            # Create CBZ (ZIP) file
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
                for image_path in all_images:
                    try:
                        # Add file to archive with just the filename (no path)
                        filename = os.path.basename(image_path)
                        cbz_file.write(image_path, filename)
                        logger.debug(f"Added to CBZ: {filename}")

                    except Exception as e:
                        logger.warning(f"Error adding {image_path} to CBZ: {e}")
                        continue

            file_size = os.path.getsize(output_path)
            logger.info(f"Manga CBZ created successfully: {output_path} ({format_bytes(file_size)})")

            return True

        except Exception as e:
            logger.error(f"Error converting manga to CBZ: {e}")
            return False

    def optimize_images(self, directory_path: str, quality: Optional[str] = None) -> bool:
        """
        Optimize images in a directory for size reduction.

        Args:
            directory_path: Path to directory containing images
            quality: Quality setting to use (optional, uses instance setting if not provided)

        Returns:
            True if optimization successful, False otherwise
        """
        if not os.path.exists(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return False

        quality_to_use = quality or self.quality
        settings = self.quality_settings[quality_to_use]

        try:
            logger.info(f"Optimizing images in {directory_path} with {quality_to_use} quality")

            image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
            optimized_count = 0
            total_size_before = 0
            total_size_after = 0

            for file_path in Path(directory_path).rglob('*'):
                if file_path.suffix.lower() in image_extensions and file_path.is_file():
                    try:
                        original_size = file_path.stat().st_size
                        total_size_before += original_size

                        # Open and optimize image
                        with Image.open(file_path) as img:
                            # Convert to RGB if necessary
                            if img.mode not in ('RGB', 'L'):
                                img = img.convert('RGB')

                            # Resize if needed
                            if settings['resize_factor'] != 1.0:
                                width, height = img.size
                                new_width = int(width * settings['resize_factor'])
                                new_height = int(height * settings['resize_factor'])
                                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                            # Save optimized image
                            if file_path.suffix.lower() in {'.jpg', '.jpeg'}:
                                img.save(file_path, 'JPEG', quality=settings['jpeg_quality'], optimize=True)
                            else:
                                img.save(file_path, optimize=True)

                        new_size = file_path.stat().st_size
                        total_size_after += new_size
                        optimized_count += 1

                        logger.debug(f"Optimized {file_path.name}: {format_bytes(original_size)} -> {format_bytes(new_size)}")

                    except Exception as e:
                        logger.warning(f"Error optimizing {file_path}: {e}")
                        continue

            if optimized_count > 0:
                size_reduction = total_size_before - total_size_after
                logger.info(f"Optimized {optimized_count} images, saved {format_bytes(size_reduction)}")
                return True
            else:
                logger.warning("No images were optimized")
                return False

        except Exception as e:
            logger.error(f"Error optimizing images: {e}")
            return False