from django.contrib import admin

# Register your models here.

from models import *

class UserAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'score','ip')
    search_fields = ('student_id',)

class ProblemsAdmin(admin.ModelAdmin):
    list_display = ('stem',)
    search_fields = ('stem',)
    list_filter = ('stem_type','difficulty_degree')


admin.site.register(User,UserAdmin)
admin.site.register(Problems,ProblemsAdmin)
