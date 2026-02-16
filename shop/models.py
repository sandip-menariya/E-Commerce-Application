from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password,check_password
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings
from django.contrib.auth import get_user_model
# Create your models here.

# created custom base user manager by redefining some roles like Customer, Merchant, Admin and Staff member
class CustomBaseUserManager(BaseUserManager):
    def create_user(self,username,password,**extra_fields):
        extra_fields.setdefault("role","CUSTOMER")
        user=self.model(username=username,**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self,username,password,**extra_fields):
        extra_fields.setdefault("is_staff",True)
        extra_fields.setdefault("is_superuser",True)
        extra_fields.setdefault("role","ADMIN")
        return self.create_user(username,password,**extra_fields)

# custom user registration model which is deriving the properties of User model by inheriting AbstractUser model like password hashing and other security and convenience 
class user_registration(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN="ADMIN","Admin"
        STAFF="STAFF","Staff"
        CUSTOMER="CUSTOMER","Customer"
        MERCHANT="MERCHANT","Merchant"
    role=models.CharField(max_length=10,choices=Roles.choices,default=Roles.CUSTOMER)
    mobile=models.CharField(max_length=15)
    USERNAME_FIELD='username'
    REQUIRED_FIELDS=['email']
    object=CustomBaseUserManager()
    def save(self,*args,**kwargs):
        if self.role in [self.Roles.ADMIN,self.Roles.STAFF]:
            self.is_staff=True
        else:
            self.is_staff=False
        super().save(*args,**kwargs)
    def has_perm(self,perm,obj=None):
        return self.is_superuser
    def has_module_perms(self,app_label):
        return True
    def __str__(self):
        return self.username

# Merchant account for posting products by listing shop on website and manage products.
class MerchantAccount(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="Merchant")
    shop_name=models.CharField(max_length=150,null=False,blank=False)
    description=models.CharField(max_length=300,null=False,blank=False)
    adhar_card=models.CharField(max_length=12,blank=False,null=False)
    pan_card=models.CharField(max_length=10,null=False,blank=False)
    bank_details=models.CharField(max_length=70,null=False,blank=False)
    is_varified=models.BooleanField(default=False)
    def __str__(self):
        return self.shop_name

# content are simply products which will be posted by the merchant from their shops merchant will have some special previlleges as compared to normal user, as we have stored the merchant as foreign key.
class contents(models.Model):
    user=models.ForeignKey(MerchantAccount,on_delete=models.CASCADE)
    title=models.CharField(max_length=100)
    category=models.CharField(max_length=100)
    sub_category=models.CharField(max_length=100)
    summary=models.CharField(max_length=100)
    publisher=models.CharField(max_length=100)
    date=models.DateField()
    price=models.FloatField()
    image=models.ImageField(upload_to="shop/images/",null=True,blank=True)
    image_url=models.URLField(max_length=500,null=True,blank=True)
    def get_img_url(self):
        if self.image:
            return self.image.url
        elif self.image_url:
            return self.image_url
        return ""
    def __str__(self):
        return self.title
    def latest_items(self):
        return contents.objects.order_by('-date').first()
    
# cart is used to show user items in the cart by storing the product id and user as foreign key for reference.
class Cart(models.Model):
    user=models.ForeignKey(user_registration,related_name="users",on_delete=models.CASCADE)
    product=models.ForeignKey(contents,related_name="cart_items",on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)

# this model stores the user's address for shipping the order placed and used user field as foreign key for user.
class UserAddressModel(models.Model):
    user=models.ForeignKey(user_registration,related_name="address_user",on_delete=models.CASCADE)
    full_name=models.CharField(max_length=100)
    mobile=models.CharField(max_length=15)
    postal_code=models.CharField(max_length=10)
    address_line=models.TextField()
    city=models.CharField(max_length=50)
    state=models.CharField(max_length=50)
    country=models.CharField(max_length=50)

# the order model where after user have placed order and payment the status will be toggled based on callback_url's response in razorpay, by defult status is pending and will be changed while the callback has returned success, and based on this we will decide that merchant payment model is ready for settlement or not.
class Order(models.Model):
    class StatusChoices(models.TextChoices):
        SUCCESS="SUCCESS","success"
        PENDING="PENDING","pending"
        FAILURE="FAILED","failed"
    user=models.ForeignKey(user_registration,on_delete=models.CASCADE)
    order_id=models.CharField(max_length=50,null=False,blank=False,primary_key=True)
    payment_id=models.CharField(max_length=40,null=False,blank=False)
    signature_id=models.CharField(max_length=128,null=False,blank=False)
    amount=models.DecimalField(max_digits=10,decimal_places=2)
    status=models.CharField(max_length=20,choices=StatusChoices.choices,default=StatusChoices.PENDING)
    def __str__(self):
        return self.order_id

# merchant payment account where the all payments which are ready or not ready to settle will be stored by relating the merchant's payment model with both order and merchant account.
class MerchantPaymentAccount(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING="PENDING","Pending"
        READY="READY","Ready"
        SETTLED="SETTLED","Settled"
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="merchant_items")
    merchant=models.ForeignKey(MerchantAccount,on_delete=models.CASCADE)
    amount=models.DecimalField(max_digits=10,decimal_places=2)
    status=models.CharField(max_length=20,choices=StatusChoices.choices,default=StatusChoices.PENDING)
    def __str__(self):
        return f"{self.merchant}-{self.order}-{self.status}"

# order item model for storing the product by relating the product to Order which is made by user and merchant ("the seller") and made the order as reverse lookup for the model.
class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name="items")
    merchant=models.ForeignKey(MerchantAccount,on_delete=models.CASCADE)
    product=models.ForeignKey(contents,on_delete=models.CASCADE)
    quantity=models.PositiveBigIntegerField()
    price_at_purchase=models.IntegerField()
    order_date=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.product}-{self.items}"