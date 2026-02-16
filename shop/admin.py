from django.contrib import admin
from shop.models import contents,Cart
from django.contrib.auth.admin  import UserAdmin
from django.contrib.auth import get_user_model

user_registration=get_user_model()

class CustomUserAdmin(UserAdmin):
    list_display=("username","role","mobile","is_staff","is_superuser")
    fieldsets=UserAdmin.fieldsets+((None,{"fields":("role","mobile")}),)
    
admin.site.register(user_registration,CustomUserAdmin)
admin.site.register(contents)
admin.site.register(Cart)
# admin
# Register your models here.