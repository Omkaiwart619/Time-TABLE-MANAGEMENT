from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Safely retrieves a value from a dictionary using a variable key inside templates.
    Chained Usage: {{ grid|get_item:day|get_item:period }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter(name='get_attr')
def get_attr(obj, attr_name):
    """
    Dynamically retrieves an attribute from an object or dictionary.
    Usage: {{ entry|get_attr:'room' }}
    """
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    elif isinstance(obj, dict):
        return obj.get(attr_name)
    return None


@register.filter(name='filter_by_day')
def filter_by_day(queryset_or_list, day_name):
    """
    Filters a list or QuerySet of TimetableEntry items by day name.
    Usage: {{ entries|filter_by_day:'Monday' }}
    """
    if not queryset_or_list:
        return []
    return [item for item in queryset_or_list if getattr(item, 'day', None) == day_name]


@register.filter(name='is_lab')
def is_lab(entry):
    """
    Returns True if the timetable entry's subject is a lab session.
    Usage: {% if entry|is_lab %}...{% endif %}
    """
    if entry and hasattr(entry, 'subject'):
        return getattr(entry.subject, 'is_lab', False)
    return False


@register.filter(name='slot_css_class')
def slot_css_class(entry):
    """
    Returns appropriate Bootstrap table contextual background classes based on entry type.
    Usage: <td class="{{ entry|slot_css_class }}">
    """
    if not entry:
        return ""
    if hasattr(entry, 'subject') and getattr(entry.subject, 'is_lab', False):
        return "table-info"  # Light blue for labs
    return "table-primary"    # Soft primary blue for theory classes