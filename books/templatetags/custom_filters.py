from django import template
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
from html import unescape  # Use Python's built-in unescape

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Returns the value for a given key from a dictionary.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None  # Return None if `dictionary` is not a valid dict

@register.filter
def truncatehtml(words, num):
    """
    Truncates HTML content to a specified number of words without breaking tags.
    """
    truncator = Truncator(words)
    return mark_safe(truncator.words(num, html=True))

@register.filter
def unescape_html(value):
    """
    Unescapes HTML entities in the given value.
    """
    return unescape(value)