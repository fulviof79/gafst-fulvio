from django import template
import flag as ecf

register = template.Library()


@register.filter
def flag_emoji(country_code):
    if country_code == "en":
        country_code = "gb"

    return ecf.flag(country_code)
