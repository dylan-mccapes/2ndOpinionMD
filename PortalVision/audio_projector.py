"""
Audio Projector - HTML to verbatim text conversion.

Responsibilities:
- Parse HTML in document order
- Strip decorative UI and non-semantic markup
- Preserve headings, sections, disclaimers, version labels
- Generate verbatim text for narration (no interpretation)

Non-responsibilities:
- Summarization
- Paraphrasing
- Emphasis injection
- Tone adaptation
"""

import re
from html.parser import HTMLParser
from typing import List, Tuple


class AudioProjector(HTMLParser):
    """
    Converts HTML to verbatim text for audio narration.
    
    Preserves:
    - Headings (with level indication)
    - Section boundaries
    - Paragraphs
    - Lists
    - Explicit disclaimers
    - Version labels
    
    Strips:
    - Decorative UI (buttons, inputs, navigation)
    - Non-semantic markup (divs, spans)
    - Scripts and styles
    - Images (reads alt text if present)
    """
    
    # Semantic elements to preserve
    SEMANTIC_TAGS = {
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'li', 'ul', 'ol',
        'strong', 'em', 'b', 'i',
        'blockquote', 'pre', 'code',
        'section', 'article', 'aside',
        'header', 'footer', 'main',
    }
    
    # Tags to completely ignore (including content)
    SKIP_TAGS = {
        'script', 'style', 'noscript',
        'button', 'input', 'select', 'textarea',
        'nav', 'form',
    }
    
    # Heading tags with levels
    HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    
    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.current_tag_stack: List[str] = []
        self.skip_content = False
        self.in_list = False
        self.list_item_count = 0
    
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        self.current_tag_stack.append(tag)
        
        # Skip certain tags entirely
        if tag in self.SKIP_TAGS:
            self.skip_content = True
            return
        
        # Handle headings
        if tag in self.HEADING_TAGS:
            level = int(tag[1])
            self.text_parts.append(f"\n\nHeading level {level}: ")
        
        # Handle lists
        elif tag == 'ul':
            self.in_list = True
            self.list_item_count = 0
            self.text_parts.append("\n\nList: ")
        
        elif tag == 'ol':
            self.in_list = True
            self.list_item_count = 0
            self.text_parts.append("\n\nNumbered list: ")
        
        elif tag == 'li':
            self.list_item_count += 1
            self.text_parts.append(f"\nItem {self.list_item_count}: ")
        
        # Handle block elements
        elif tag == 'p':
            self.text_parts.append("\n\n")
        
        elif tag == 'blockquote':
            self.text_parts.append("\n\nQuote: ")
        
        elif tag == 'pre':
            self.text_parts.append("\n\nCode block: ")
        
        # Handle sections
        elif tag in {'section', 'article', 'aside'}:
            self.text_parts.append("\n\nSection: ")
        
        # Handle images (read alt text)
        elif tag == 'img':
            alt_text = dict(attrs).get('alt', '')
            if alt_text:
                self.text_parts.append(f"\n[Image: {alt_text}]\n")
        
        # Handle line breaks
        elif tag == 'br':
            self.text_parts.append("\n")
    
    def handle_endtag(self, tag: str):
        if self.current_tag_stack and self.current_tag_stack[-1] == tag:
            self.current_tag_stack.pop()
        
        # Re-enable content after skip tags
        if tag in self.SKIP_TAGS:
            self.skip_content = False
        
        # Reset list state
        if tag in {'ul', 'ol'}:
            self.in_list = False
            self.list_item_count = 0
    
    def handle_data(self, data: str):
        if self.skip_content:
            return
        
        # Clean and normalize whitespace
        text = data.strip()
        if text:
            # Collapse multiple spaces
            text = re.sub(r'\s+', ' ', text)
            self.text_parts.append(text)
    
    def get_text(self) -> str:
        """
        Get the final verbatim text for narration.
        
        Returns:
            Clean text suitable for TTS, preserving document structure
        """
        # Join all parts
        raw_text = ' '.join(self.text_parts)
        
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', raw_text)
        
        # Clean up spaces around newlines
        text = re.sub(r' *\n *', '\n', text)
        
        # Final trim
        text = text.strip()
        
        return text


def html_to_audio_text(html_content: str) -> str:
    """
    Convert HTML to verbatim text for audio narration.
    
    Args:
        html_content: The HTML artifact content
    
    Returns:
        Clean text suitable for TTS, preserving semantic structure
    
    Guarantees:
    - No summarization
    - No paraphrasing
    - No interpretation
    - Document order preserved
    - Semantic structure indicated
    """
    projector = AudioProjector()
    projector.feed(html_content)
    return projector.get_text()


def validate_audio_text(text: str) -> Tuple[bool, str]:
    """
    Validate that audio text is suitable for TTS.
    
    Args:
        text: The text to validate
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not text or len(text.strip()) == 0:
        return False, "Text is empty"
    
    if len(text) < 10:
        return False, "Text is too short (< 10 characters)"
    
    # Check for excessive HTML that wasn't stripped
    if '<script' in text.lower() or '<style' in text.lower():
        return False, "HTML tags detected in text"
    
    return True, ""

