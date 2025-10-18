from django import template

register = template.Library()

@register.simple_tag
def page_numbers(current_page, total_pages, window=1):
    """
    Return a list representing the pagination bar with ellipses.
    Example: [1, 2, 3, '...', 100] when current_page=1 and total_pages=100.

    - If total_pages <= 7: show all pages.
    - Else: show first page, a window around current_page, ellipses as needed, and last page.
    """
    try:
        current_page = int(current_page)
        total_pages = int(total_pages)
    except Exception:
        return []

    if total_pages <= 0:
        return []

    # Show all pages if small
    if total_pages <= 3:
        return list(range(1, total_pages + 1))

    pages = [1]

    start = max(2, current_page - window)
    end = min(total_pages - 1, current_page + window)

    if start > 2:
        pages.append('...')

    pages.extend(range(start, end + 1))

    if end < total_pages - 1:
        pages.append('...')

    pages.append(total_pages)
    return pages