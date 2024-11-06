# tests/services/test_document_services.py

import pytest
from bs4 import BeautifulSoup, Comment
from datetime import datetime, timedelta
import uuid
import json

from backend.services.document_formatting_services import (
    extract_title,
    extract_primary_image,
    extract_publisher,
    extract_full_text,
    normalize_whitespace,
    tag_visible,
    remove_html_tags,
    remove_non_ascii,
    clean_text,
    extract_thumbnail,
    reformat_document_to_markdown,
    reformat_document_to_html
)
from backend.schemas import DefaultIcons

# --------------------------- Unit Tests ---------------------------

def test_extract_title_with_title_tag():
    html = "<html><head><title>Test Document</title></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup, "1234")
    assert title == "Test Document"

def test_extract_title_without_title_tag_but_with_meta():
    html = """
    <html>
        <head>
            <meta property="og:title" content="Meta Title">
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup, "1234")
    assert title == "Meta Title"

def test_extract_title_without_title_or_meta():
    html = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup, "1234")
    assert title == "Untitled Document 1234"

def test_extract_primary_image_with_og_image():
    html = """
    <html>
        <head>
            <meta property="og:image" content="https://example.com/image.jpg">
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    image = extract_primary_image(soup)
    assert image == "https://example.com/image.jpg"

def test_extract_primary_image_with_img_tag():
    html = """
    <html>
        <body>
            <img src="https://example.com/image.png" alt="Sample Image">
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    image = extract_primary_image(soup)
    assert image == "https://example.com/image.png"

def test_extract_primary_image_without_image():
    html = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    image = extract_primary_image(soup)
    assert image == DefaultIcons.ARTICLE_ICON_SVG

def test_extract_publisher_with_og_site_name():
    html = """
    <html>
        <head>
            <meta property="og:site_name" content="Example Publisher">
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    publisher = extract_publisher(soup, "https://example.com/article")
    assert publisher == "Example Publisher"

def test_extract_publisher_without_og_site_name():
    html = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    publisher = extract_publisher(soup, "https://www.example.com/article")
    assert publisher == "example.com"

def test_extract_publisher_without_domain():
    html = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    publisher = extract_publisher(soup, "")
    assert publisher == ""

def test_extract_full_text_with_document_content():
    html = """
    <html>
        <body>
            <div class="document-content">
                <p>This is the first paragraph.</p>
                <p>This is the second paragraph.</p>
            </div>
            <script>var a = 1;</script>
            <style>body {}</style>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    full_text = extract_full_text(soup)
    assert full_text == "This is the first paragraph. This is the second paragraph."

def test_extract_full_text_without_document_content():
    html = """
    <html>
        <body>
            <p>General content without specific div.</p>
            <script>var a = 1;</script>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    full_text = extract_full_text(soup)
    assert full_text == "General content without specific div."

def test_normalize_whitespace():
    text = "This    is  a\n\nsample\ttext."
    normalized = normalize_whitespace(text)
    assert normalized == "This is a sample text."

def test_tag_visible():
    # Create a BeautifulSoup object with a comment
    html_with_comment = "<html><body><!-- This is a comment --></body></html>"
    soup_with_comment = BeautifulSoup(html_with_comment, "html.parser")
    comment = soup_with_comment.find(string=lambda text: isinstance(text, Comment))
    
    # Create a BeautifulSoup object with a script tag
    html_with_script = "<html><body><script>var a = 1;</script></body></html>"
    soup_with_script = BeautifulSoup(html_with_script, "html.parser")
    script_tag = soup_with_script.script
    
    # Create a BeautifulSoup object with a visible body tag
    html_with_body = "<html><body>Visible Text</body></html>"
    soup_with_body = BeautifulSoup(html_with_body, "html.parser")
    body_tag = soup_with_body.body
    
    # Assertions
    assert not tag_visible(comment), "Comment should not be visible"
    assert not tag_visible(script_tag), "Script tag should not be visible"
    assert tag_visible(body_tag), "Body tag content should be visible"

def test_remove_html_tags():
    html = "<p>This is <b>bold</b> and <a href='#'>link</a>.</p>"
    text = remove_html_tags(html)
    assert text == "This is bold and link."

def test_remove_non_ascii():
    text = "This is a test 😊 with emojis."
    cleaned = remove_non_ascii(text)
    assert cleaned == "This is a test  with emojis."

def test_clean_text():
    html = """
    <html>
        <body>
            <p>This is <b>bold</b> text.</p>
            <p>Second paragraph with emoji 😊.</p>
            <script>var a = 1;</script>
            <!-- Comment -->
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    cleaned = clean_text(extract_full_text(soup))
    assert cleaned == "This is bold text. Second paragraph with emoji ."

def test_extract_thumbnail_with_meta_thumbnail():
    html = """
    <html>
        <head>
            <meta name="thumbnail" content="https://example.com/thumbnail.jpg">
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    thumbnail = extract_thumbnail(soup)
    assert thumbnail == "https://example.com/thumbnail.jpg"

def test_extract_thumbnail_without_meta_thumbnail():
    html = """
    <html>
        <head></head>
        <body>
            <img src="https://example.com/image.png" alt="Sample Image">
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    thumbnail = extract_thumbnail(soup)
    assert thumbnail == "https://example.com/image.png"

def test_extract_thumbnail_without_any_image():
    html = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    thumbnail = extract_thumbnail(soup)
    assert thumbnail == DefaultIcons.ARTICLE_ICON_SVG

def test_reformat_document_to_markdown():
    document = {
        "name": "Test Document",
        "type": "Article",
        "publisheddate": "2023-01-01",
        "addeddate": "2023-01-02",
        "url": "https://example.com/test-document",
        "text": "This is the first paragraph.\n\nThis is the second paragraph.",
        "thumbnail": "https://example.com/thumbnail.jpg",
        "image": "https://example.com/image.png"
    }
    
    expected_markdown = (
        "# Test Document\n\n"
        "<img src='https://example.com/thumbnail.jpg' alt='Thumbnail' style='float: right; margin: 0 0 20px 20px; max-width: 200px;'>\n\n"
        "**Type:** Article  \n"
        "**Published:** 2023-01-01  \n"
        "**Added:** 2023-01-02  \n\n"
        "[View Original Source](https://example.com/test-document)\n\n"
        "---\n\n"
        "This is the first paragraph.\n\n"
        "This is the second paragraph.\n\n"
        "![Full-size Image](https://example.com/image.png)\n\n"
        "---\n\n"
        "*This document was generated by clockworKnowledge Research Agent.*\n"
    )
    
    markdown = reformat_document_to_markdown(document)
    assert markdown == expected_markdown

def test_reformat_document_to_html():
    document = {
        "name": "Test Document",
        "type": "Article",
        "publisheddate": "2023-01-01",
        "addeddate": "2023-01-02",
        "url": "https://example.com/test-document",
        "text": "This is the first paragraph.\n\nThis is the second paragraph.",
        "thumbnail": "https://example.com/thumbnail.jpg",
        "image": "https://example.com/image.png"
    }
    
    html = reformat_document_to_html(document)
    
    # Simple assertions to check if key elements are present
    assert "<h1>Test Document</h1>" in html
    assert "<strong>Type:</strong> Article" in html
    assert '<a href="https://example.com/test-document">https://example.com/test-document</a>' in html
    # Check for both paragraphs
    assert "<p>This is the first paragraph.</p>" in html
    assert "<p>This is the second paragraph.</p>" in html
    assert '<img src="https://example.com/thumbnail.jpg" alt="Thumbnail" class="thumbnail">' in html
    assert '<img src="https://example.com/image.png" alt="Main Image">' in html
