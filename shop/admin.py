from django.contrib import admin
from shop.models import contents, Cart, ProductCategories
from django.contrib.auth.admin  import UserAdmin
from django.contrib.auth import get_user_model
from mptt.admin import DraggableMPTTAdmin

user_registration=get_user_model()

class CustomUserAdmin(UserAdmin):
    list_display=("username","role","mobile","is_staff","is_superuser")
    fieldsets=UserAdmin.fieldsets+((None,{"fields":("role","mobile")}),)

class CategoryAdmin(DraggableMPTTAdmin):
    prepopulated_fields={"slug":("category",)}
    
admin.site.register(user_registration,CustomUserAdmin)
admin.site.register(contents)
admin.site.register(Cart)
# admin.site.unregister(ProductCategories,MPTTModelAdmin)
# if admin.site.is_registered(ProductCategories):
#     admin.site.unregister(ProductCategories)
admin.site.register(ProductCategories,CategoryAdmin)
# admin.site.unregister(ProductCategories)
# admin.site.register(ProductCategories)