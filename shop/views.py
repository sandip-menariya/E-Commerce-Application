from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from .models import contents, Cart, UserAddressModel, Order, OrderItem, MerchantPaymentAccount, MerchantAccount
from django.contrib.auth.decorators import login_required, user_passes_test
# from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from django.db import transaction
import json
from shop.forms import UserAddressForm, MerchantRegistrationForm
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
# Create your views here.
User=get_user_model()

def chunks(lst,n):
    for i in range(0,len(lst),n):
        yield lst[i:i+n]

def home(request):
    items=contents.objects.all()
    category={}
    for item in items:
        cat=item.category.capitalize()
        if cat not in category:
            category[cat]=[item]
        else:
            category[cat].append(item)
    for cat,items in category.items():
        group=list(chunks(items,4))
        category[cat]=group
    category_range={cat:range(len(cat_items)) for cat,cat_items in category.items()}
    return render(request,'shop/index.html',{'categories':category,'category_range':category_range})
    
def checkout(request):
    return render(request,"shop/checkout_page.html")

def create_registration(request):
    username=request.POST.get("username")
    contact=request.POST.get("contact")
    email=request.POST.get("email")
    password=request.POST.get("password")
    # re_password=request.POST.get("re_password")
    term=request.POST.get("terms")
    if(not email or not password or not username or not contact or term==None):
        messages.error(request,"all fields are required")
        return render(request,"shop/registration.html")
    is_present=validate(request)
    if(is_present['username']):
        messages.warning(request,"username already exists")
        return render(request,'shop/registration.html')
    if(is_present['email']):
        messages.warning(request,"email already exists")
        return render(request,'shop/registration.html')
    user=User.objects.create_user(username=username,email=email,mobile=contact)
    user.set_password(password)
    user.save()
    login(request,user,backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request,"you have successfully registered!")
    return redirect('home')

def merchant_register(request):
    merchant=MerchantAccount.objects.filter(user=request.user).first()
    form=MerchantRegistrationForm(instance=merchant)
    return render(request,"shop/merchant_registration_form.html",{"merchant_form":form})

@transaction.atomic
def create_merchant_account(request):
    if request.method=="POST" and request.user.is_authenticated:
        merchant_account=MerchantAccount.objects.filter(user=request.user).first()
        if merchant_account:
            messages.warning(request,"You have already filled the details you can't update these.")
            return redirect("home")
        form=MerchantRegistrationForm(request.POST)
        if form.is_valid():
            merchant_details=form.save(commit=False)
            merchant_details.user=request.user
            merchant_details.is_varified=True
            merchant_details.save()
            user=User.objects.get(id=request.user.id)
            user.role=user.Roles.MERCHANT
            user.save()
            messages.success(request,f"you are successfully registered as Merchant")
            return redirect("home")
        messages.error(request,"invalid form action recorded.")
        form=MerchantRegistrationForm(instance=merchant_account)
        return render(request,"merchant_registration_form.html",{"merchant_form":form})
    return redirect("merchant_register")

def merchant_dashboard(request):
    if request.user.is_authenticated and request.user.role=="MERCHANT":
        merchant=MerchantAccount.objects.filter(user=request.user).first()
        products=contents.objects.filter(user=merchant).order_by("-date")
        return render(request,"shop/merchant_dashboard.html",{"products":products})
    messages.error("you are not authorized to view merchant page.")
    return redirect("home")

def registeration_view(request):
    return render(request,'shop/registration.html')

def login_view(request):
    return render(request,'shop/login.html')

def validate(request):
    username=request.POST.get("username")
    email=request.POST.get("email")
    uname=User.objects.filter(username=username)
    e_mail=User.objects.filter(email=email)
    return {"username":uname,"email":e_mail}

def is_merchant_user(user):
    return user.role=="MERCHANT"

@login_required
@user_passes_test(is_merchant_user)
def add_content(request):
    operation="Add"
    return render(request,"shop/add_content.html",{"operation":operation})

# a merchant can post it's product on the website if it is authenticated and staff members will also have access to products.
def upsert_content(request,product_id=None):
    if request.user.is_authenticated and request.user.role=="MERCHANT":
        product=None
        operation="Add"
        if product_id is not None:
            operation="Update"
            product=get_object_or_404(contents,user=request.user.Merchant,id=product_id)
        if request.method=="POST":
            title=request.POST.get("title")
            category=request.POST.get("category")
            sub_category=request.POST.get("sub_category")
            publisher=request.POST.get("publisher")
            summary=request.POST.get("summary")
            price=request.POST.get("price")
            date=request.POST.get("date")
            image_path=None
            image_url=None
            if request.POST.get("img-option")=='url':
                image_url=request.POST.get("image_url")
            else:
                image_path=request.FILES.get("image")
            if product:
                product.title=title
                product.category=category
                product.sub_category=sub_category
                product.publisher=publisher
                product.summary=summary
                product.price=price
                product.date=date
                if image_url:
                    product.image_url=image_url
                else:
                    product.image=image_path
                product.save()
                messages.success(request,f"product title {product.title} updated successfully.")
                return redirect("merchant_dashboard")
            else:
                merchant=MerchantAccount.objects.filter(user=request.user).first()
                item=contents.objects.filter(user=merchant,title=title)
                if(item):
                    messages.warning(request,"you have already this product in your shop you can update it from update page.")
                    return render(request,"shop/add_content.html")
                if image_url:
                    content=contents(user=merchant,category=category,sub_category=sub_category,summary=summary,title=title,publisher=publisher,price=price,date=date,image_url=image_url)
                    content.save()
                else:
                    content=contents(user=merchant,category=category,sub_category=sub_category,summary=summary,title=title,publisher=publisher,price=price,date=date,image=image_path)
                    content.save()
                messages.success(request,f"content {title} added successfully")
                return render(request,"shop/add_content.html")
        return render(request,"shop/add_content.html",{"product":product,"operation":operation})
    else: 
        messages.error(request,"You are not authorized to add content..!")
    return redirect("home")

def delete_item(request):
    if request.method=="POST":
        prod_id=request.POST.get("prod_id")
        product=get_object_or_404(contents,id=prod_id)
        title=product.title
        product.delete()
        return JsonResponse({"message":f"Item {title} deleted successfully."})
    return JsonResponse({"message":"error"},status=400)

def add_to_cart(request):
    if request.method=="POST" and request.user.is_authenticated:
        item_id=request.POST.get("product_id")
        product=contents.objects.get(id=item_id)
        user_cart,created=Cart.objects.get_or_create(user=request.user,product=product)
        if not created:
            user_cart.quantity+=1
            user_cart.save()
        return JsonResponse({'status':'success','message':f"item {product.title} added to cart successfully"})
    return JsonResponse({"status":"login_required"})

# view to display cart items
def my_cart(request):
    if request.user.is_authenticated:
        cart=Cart.objects.filter(user=request.user)
        products=[]
        for item in cart:
            product=item.product
            products.append({"product":product,"quantity":item.quantity})
        address=UserAddressModel.objects.filter(user=request.user).first()
        AddressForm=UserAddressForm(instance=address)
        return render(request,"shop/checkout_page.html",{"products":products,"address":AddressForm,"user_address":address})
    return redirect("home")


# login user view if user is regeistered in the database.
def user_login(request):
    if request.method=="POST":
        username=request.POST.get("username")
        password=request.POST.get("password")
        user=authenticate(request,username=username,password=password)
        if not user:
            messages.warning(request,"Invalid username or password")
            return redirect("login_view")
        login(request,user)
        return redirect("home")

# log out view if user is authenticated and logged in.
def user_logout(request):
    if User.is_active and request.user.is_authenticated:
        logout(request)
    return redirect("home")

# view for adding user addresss in checkout page getting data through AJAX from checkout page.
def add_user_address(request):
    if request.method=="POST" and request.user.is_authenticated:
        address_instance=UserAddressModel.objects.filter(user=request.user).first()
        AddressForm=UserAddressForm(request.POST,instance=address_instance)
        if AddressForm.is_valid():
            address=AddressForm.save(commit=False)
            address.user=request.user
            address.save()
            if address_instance is None:
                address_instance=UserAddressModel.objects.filter(user=request.user).first
            address={
                "full_name":address_instance.full_name,
                "address_line":address_instance.address_line,
                "postal_code":address_instance.postal_code
            }
            messages.success(request,"Address added successfully")
            return JsonResponse({'status':'success',"message":"address saved successfully","user_address":address})
        else:
            AddressForm=UserAddressForm(instance=address_instance)
    return JsonResponse({'status':"error","message":"invalid request method",},status=405)

# checkout page for creating order and payment backend.-- here is raozorpay test api and managing the order by each product to customer model and merchant model for further processing and after completion of payment integration the data will go to callback url for validation(success or error).
@transaction.atomic
def checkout_user(request):
    if request.method=="POST" and request.user.is_authenticated:
        try:
            data=json.loads(request.body)
            items=data.get("items")
            if not items:
                return JsonResponse({"status":"you have no products available in cart."})
            temp_items=[]
            total_price=0
            for item in items:
                product=contents.objects.get(id=item["id"])
                product_price=product.price*item['quantity']
                total_price+=product_price
                temp_items.append({"product":product,"amount":product_price,"quantity":item["quantity"]})

            client=razorpay.Client(auth=(settings.RAZORPAY_TEST_API_KEY,settings.RAZORPAY_TEST_KEY_SECRET))
            razorpay_order = client.order.create({"amount": int(total_price) * 100, "currency": "INR", "payment_capture": "1"})
            order=Order.objects.create(user=request.user,order_id=razorpay_order['id'],amount=total_price)
            for item in temp_items: 
                OrderItem.objects.create(order=order,merchant=item['product'].user,product=item['product'],quantity=item['quantity'],price_at_purchase=item['product'].price)
                MerchantPaymentAccount.objects.create(order=order,merchant=item['product'].user,amount=item['amount'])
            return JsonResponse({"razorpay_order_id":razorpay_order['id'],"razorpay_merchant_key":settings.RAZORPAY_TEST_API_KEY,"currency":"INR","callback_url":"http://127.0.0.1:8000/shop/callback/"},status=200)                
        except Exception as e:
            return JsonResponse({"error":str(e),"message":"order creation error."},status=500)
    messages.error("invalid payment request.")
    return JsonResponse({"status":"error","message":"invalid payment request."},status=400)

def callback_payment_process(request):
    return render(request,"shop/paymentprocess.html")

@csrf_exempt
def callback(request):
    def verify_signature(response_data):
        client=razorpay.Client(auth=(settings.RAZORPAY_TEST_API_KEY,settings.RAZORPAY_TEST_KEY_SECRET))
        return client.utility.verify_payment_signature(response_data)
    if "razorpay_signature" in request.POST:
        order_id=request.POST.get("razorpay_order_id","")
        payment_id=request.POST.get("razorpay_payment_id","")
        signature=request.POST.get("razorpay_signature","")
        order=Order.objects.get(order_id=order_id)
        order.payment_id=payment_id
        order.signature_id=signature
        merchant_account=MerchantPaymentAccount.objects.filter(order=order)
        if verify_signature(request.POST):
            for merchants in merchant_account:
                merchants.status=merchants.StatusChoices.READY
            order.status=order.StatusChoices.SUCCESS
            order.save()
            return render(request,"shop/paymentsuccess.html",context={"status":order.status})
        else:
            order.status=order.StatusChoices.FAILURE
            order.save()
            return render(request,"shop/paymentfailed.html",context={"status":order.status})
    else:
        payment_id = json.loads(request.POST.get("error[metadata]")).get("payment_id")
        provider_order_id = json.loads(request.POST.get("error[metadata]")).get("order_id")
        order=Order.objects.get(order_id=provider_order_id)
        order.payment_id=payment_id
        order.status=order.StatusChoices.FAILURE
        order.save()
        return render(request,"shop/paymentfailed.html",context={"status":order.status})