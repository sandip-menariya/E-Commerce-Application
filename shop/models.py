from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings
from django.contrib.auth import get_user_model
from mptt.models import MPTTModel,TreeForeignKey
from django.utils.text import slugify
# Create your models here.

# creating custom BaseUserManager by redefining some roles like Customer, Merchant, Admin or Staff member.
class CustomBaseUserManager(BaseUserManager):
    def create_user(self,username,password,**extra_fields):
        # creating a normal user and specifying its role as customer if the it is not an admin user as role specified in create_superuser then it will set the role as default 'CUSTOMER'.
        extra_fields.setdefault("role","CUSTOMER")
        user=self.model(username=username,**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self,username,password,**extra_fields):
        # creating superuser and specifying its role and previleges.
        extra_fields.setdefault("is_staff",True)
        extra_fields.setdefault("is_superuser",True)
        extra_fields.setdefault("role","ADMIN")
        return self.create_user(username,password,**extra_fields)

# custom user registration model which is deriving the properties of User model by inheriting AbstractUser model like password hashing and other security and convenience 
class user_registration(AbstractUser):
    # it is the overriden class of default User model to specify some other fields in the user registration than it provides by default such as roles, contact and more.
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
    # at the time of saving if user's role is admin or staff then we will make the is_staff attribute as true otherwise false.
    def save(self,*args,**kwargs):
        if self.role in [self.Roles.ADMIN,self.Roles.STAFF]:
            self.is_staff=True
        else:
            self.is_staff=False
        super().save(*args,**kwargs)
    # specifying the user as if it has certain permission, in this case is it a superuser or not.
    def has_perm(self,perm,obj=None):
        return self.is_superuser
    def has_module_perms(self,app_label):
        return True
    def __str__(self):
        return self.username

# Merchant account for user wants to add their products by adding its shop on website and manage products.
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

# this model is for creating product categories which will be maintained at admin level and we used the modified preorder tree traversal for better management and UX.
class ProductCategories(MPTTModel):
    category=models.CharField(max_length=50)
    # for creating a tree like structure for sub categories we are using TreeForeignKey for referencing a category to its parent category in self model.
    parent=TreeForeignKey("self",on_delete=models.CASCADE,blank=True,null=True,related_name="children")
    slug=models.SlugField(max_length=100,unique=False)
    class MPTTMeta:
        # here if there are some sub categories have same name for different parent categories then we are creating the slug and category as unique_together so the parent category will not ahve duplicate sub categories.
        unique_together=('category','slug')
        order_insertion_by=['category']
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug=slugify(self.category)
        super().save(*args,**kwargs)
    def __str__(self):
        return self.category
    
# content are simply products which will be posted by the merchant from their shops merchant will have some special previlleges as compared to normal user, as we have stored the merchant as foreign key.
class contents(models.Model):
    user=models.ForeignKey(MerchantAccount,on_delete=models.CASCADE)
    title=models.CharField(max_length=100)
    category=TreeForeignKey("ProductCategories",on_delete=models.CASCADE)
    search_tags=models.TextField(blank=True,editable=False)
    summary=models.CharField(max_length=500)
    publisher=models.CharField(max_length=50)
    date=models.DateField(auto_now_add=True)
    base_price=models.FloatField()
    list_price=models.FloatField()
    image=models.ImageField(upload_to="shop/images/",null=True,blank=True)
    image_url=models.URLField(max_length=500,null=True,blank=True)
    def save(self,*args,**kwargs):
        # combining all the related categories of all parents and title and joining them as single string with single space for efficient search operation.
        tags=[self.title]
        ancestors=self.category.get_ancestors(include_self=True)
        for cat in ancestors:
            tags.append(cat.category)
        self.search_tags=" ".join(tags).lower()
        super().save(*args,**kwargs)
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
    base_price_at_purchase=models.FloatField()
    list_price_at_purchase=models.FloatField()
    order_date=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.product}-{self.items}"