"""
Document Formatting Services Module

This module provides functionality for extracting and formatting document content from HTML and other formats.
It includes utilities for cleaning text, extracting metadata, and reformatting documents into different output formats.

Functions:
    extract_title: Extracts document title from HTML
    extract_primary_image: Extracts main image URL from HTML 
    extract_publisher: Extracts publisher info from HTML/URL
    extract_full_text: Extracts main text content from HTML
    normalize_whitespace: Normalizes whitespace in text
    tag_visible: Checks if HTML element should be visible
    remove_html_tags: Strips HTML tags from text
    remove_non_ascii: Removes non-ASCII characters
    clean_text: Cleans and normalizes text content
    extract_thumbnail: Extracts thumbnail image URL
    reformat_document_to_markdown: Converts document to Markdown
    reformat_document_to_html: Converts document to HTML
"""

import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse
from backend.schemas import DefaultIcons
from pydantic import HttpUrl, AnyUrl

def extract_title(soup: BeautifulSoup, document_id: str) -> str:
    """
    Extracts the title from HTML content.

    Args:
        soup (BeautifulSoup): Parsed HTML content
        document_id (str): Fallback document ID if no title found

    Returns:
        str: Extracted title or default title with document ID
    """
    title = soup.title.string if soup.title else None
    if not title:
        title = f"Untitled Document {document_id}"
        meta_title = soup.find('meta', attrs={'property': 'og:title'})
        if meta_title:
            title = meta_title.get('content', title)
    return title


def extract_primary_image(soup: BeautifulSoup) -> str:
    """
    Extracts the primary image URL from HTML content.

    Args:
        soup (BeautifulSoup): Parsed HTML content

    Returns:
        str: URL of primary image or default icon URL
    """
    default_image_url = DefaultIcons.ARTICLE_ICON_SVG
    image = soup.find('meta', property='og:image')
    if image and image.get('content'):
        return image['content']
    image = soup.find('img')
    if image and image.get('src'):
        return image['src']
    return default_image_url  # Return a default image URL if no image is found


def extract_publisher(soup: BeautifulSoup, url: str) -> str:
    """
    Extracts publisher information from HTML content or URL.

    Args:
        soup (BeautifulSoup): Parsed HTML content
        url (str): Source URL

    Returns:
        str: Publisher name or domain name or empty string
    """
    publisher = soup.find('meta', property='og:site_name')
    if publisher and publisher.get('content'):
        return publisher['content']
    
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain:
            return domain.replace("www.", "")
    except Exception:
        pass
    
    return ''


def extract_full_text(soup: BeautifulSoup) -> str:
    """
    Extracts main text content from HTML.

    Args:
        soup (BeautifulSoup): Parsed HTML content

    Returns:
        str: Extracted text content with preserved spacing
    """
    # Remove unwanted tags:
    for tag in soup.find_all(['script', 'style', 'meta', 'noscript']):
        tag.extract()
    
    # Attempt to find the main document element based on common HTML structures.
    # You may need to adjust the tag name and class name based on the specific HTML structure of the pages you're working with.
    document_element = soup.find('div', {'class': 'document-content'})
    if document_element:
        return document_element.get_text(' ', strip=True)  # Use a space as the separator for text in different elements, and strip leading/trailing whitespace.

    # If the main document element wasn't found, fall back to extracting all text.
    return soup.get_text(' ', strip=True)

def normalize_whitespace(text: str) -> str:
    """
    Normalizes whitespace in text by collapsing multiple spaces.

    Args:
        text (str): Input text

    Returns:
        str: Text with normalized whitespace
    """
    return ' '.join(text.split())

from bs4 import Comment

def tag_visible(element):
    """
    Determines if an HTML element should be visible in output.

    Args:
        element: BeautifulSoup element

    Returns:
        bool: True if element should be visible, False otherwise
    """
    # Check if the element itself is in the list of non-visible tags
    if hasattr(element, 'name'):
        if element.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False

    # Exclude comments
    if isinstance(element, Comment):
        return False

    return True

def remove_html_tags(text):
    """
    Removes HTML tags from text.

    Args:
        text (str): HTML text

    Returns:
        str: Plain text without HTML tags
    """
    return BeautifulSoup(text, "html.parser").get_text()

def remove_non_ascii(text):
    """
    Removes non-ASCII characters from text.

    Args:
        text (str): Input text

    Returns:
        str: Text with only ASCII characters
    """
    return ''.join(character for character in text if ord(character) < 128)

def clean_text(text: str) -> str:
    """
    Cleans text by removing HTML, normalizing whitespace and removing non-ASCII chars.

    Args:
        text (str): Input text

    Returns:
        str: Cleaned text
    """
    text = remove_html_tags(text)
    text = normalize_whitespace(text)
    text = remove_non_ascii(text)
    return text


def extract_thumbnail(soup: BeautifulSoup) -> str:
    """
    Extracts thumbnail image URL from HTML content.

    Args:
        soup (BeautifulSoup): Parsed HTML content

    Returns:
        str: Thumbnail URL or primary image URL as fallback
    """
    thumb = soup.find('meta', attrs={'name': 'thumbnail'})
    if thumb:
        return thumb.get('content', '')
    # If no thumbnail meta tag is found, try fetching the primary image as a fallback
    return extract_primary_image(soup)


def reformat_document_to_markdown(document: dict) -> str:
    """
    Reformats a document dictionary into Markdown format.

    Args:
        document (dict): Document data including metadata and content

    Returns:
        str: Formatted Markdown string with metadata, content and images
    """
    markdown = f"# {document.get('name', 'Document')}\n\n"

    # Add thumbnail if present
    if 'thumbnail' in document:
        markdown += f"<img src='{document['thumbnail']}' alt='Thumbnail' style='float: right; margin: 0 0 20px 20px; max-width: 200px;'>\n\n"

    markdown += f"**Type:** {document.get('type', 'Unknown')}  \n"
    markdown += f"**Published:** {document.get('publisheddate', 'Unknown')}  \n"
    markdown += f"**Added:** {document.get('addeddate', 'Unknown')}  \n\n"

    if 'url' in document:
        markdown += f"[View Original Source]({document['url']})\n\n"

    markdown += "---\n\n"

    # Process text content with paragraph breaks
    text_content = document.get('text', 'No content available')
    paragraphs = text_content.split('\n\n')
    for paragraph in paragraphs:
        markdown += f"{paragraph.strip()}\n\n"

    # Add full-size image if present
    if 'image' in document:
        markdown += f"![Full-size Image]({document['image']})\n\n"

    markdown += "---\n\n"
    markdown += "*This document was generated by clockworKnowledge Research Agent.*\n"

    return markdown

def reformat_document_to_html(document: dict) -> str:
    """
    Reformats a document dictionary into styled HTML format.

    Args:
        document (dict): Document data including metadata and content

    Returns:
        str: Formatted HTML string with CSS styling, metadata and content
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                font-size: 2.5em;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            .meta-info {{
                background-color: #f8f9fa;
                border-left: 4px solid #3498db;
                padding: 10px;
                margin-bottom: 20px;
            }}
            .meta-info p {{
                margin: 5px 0;
            }}
            .content {{
                text-align: justify;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
            }}
            .thumbnail {{
                float: right;
                margin: 0 0 20px 20px;
                max-width: 200px;
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <div class="meta-info">
            <p><strong>Type:</strong> {type}</p>
            <p><strong>URL:</strong> <a href="{url}">{url}</a></p>
            <p><strong>Published Date:</strong> {published_date}</p>
            <p><strong>Added Date:</strong> {added_date}</p>
        </div>
        {thumbnail}
        <div class="content">
            {content}
        </div>
        {image}
    </body>
    </html>
    """

    title = document.get('name', 'Document')
    doc_type = document.get('type', 'Unknown')
    url = document.get('url', '#')
    published_date = document.get('publisheddate', 'Unknown')
    added_date = document.get('addeddate', 'Unknown')
    content = document.get('text', 'No content available')
    
    # Split content into paragraphs
    paragraphs = content.split('\n\n')
    # Wrap each paragraph in <p> tags, replace single \n with <br>
    newline = '\n'
    content_html = ''.join([f'<p>{para.replace(newline, "<br>")}</p>' for para in paragraphs])

    thumbnail = ''
    if 'thumbnail' in document:
        thumbnail = f'<img src="{document["thumbnail"]}" alt="Thumbnail" class="thumbnail">'

    image = ''
    if 'image' in document:
        image = f'<img src="{document["image"]}" alt="Main Image">'

    return html.format(
        title=title,
        type=doc_type,
        url=url,
        published_date=published_date,
        added_date=added_date,
        content=content_html,
        thumbnail=thumbnail,
        image=image
    )


