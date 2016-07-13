from django import template
import string
trans_table = string.maketrans('1,2,3,4,5,6,7,8,9','A,B,C,D,E,F,G,H,I')

register = template.Library()
def toString(value):
    return str(value)
def toOption(value):
    global trans_table
    return value.translate(trans_table)
register.filter('toString', toString)
register.filter('toOption', toOption)