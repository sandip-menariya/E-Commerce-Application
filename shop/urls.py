from django.contrib import admin
from django.urls import path
from shop import views
urlpatterns=[
    path("",views.home,name="home"),
    path("registration_view/",views.registeration_view,name="registration_view"),
    path("login_view/",views.login_view,name="login_view"),
    path("register/",views.create_registration,name="register"),
    # path("login/",views.login,name="login"),
    path("login/",views.user_login,name="login"),
    path("logout/",views.user_logout,name="logout"),
    path("add_content/",views.add_content,name="add_content"),
    path("update_product/<int:product_id>/",views.upsert_content,name="update_product"),
    path("save_content/",views.upsert_content,name="save_content"),
    path("delete_item/",views.delete_item,name="delete_item"),
    # path("is_valid_registration/",views.is_valid_registration,name="is_valid_registration"),
    path("checkout/",views.my_cart,name="checkout"),
    path("add_to_cart/",views.add_to_cart,name="add_to_cart"),
    path("save_user_address/",views.add_user_address,name="save_user_address"),
    path("checkout_user/",views.checkout_user,name="checkout_user"),
    path("merchant_register",views.merchant_register,name="merchant_register"),
    path("merchant_account_register",views.create_merchant_account,name="merchant_account_register"),
    path("merchant_dashboard/",views.merchant_dashboard,name="merchant_dashboard"),
    path("callback/",views.callback)
]