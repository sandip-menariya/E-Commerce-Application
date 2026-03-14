from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from .models import contents, Cart, UserAddressModel, Order, OrderItem, MerchantPaymentAccount, MerchantAccount, ProductCategories
from django.contrib.auth.decorators import login_required, user_passes_test
# from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from django.db import transaction
import json
from shop.forms import MerchantRegistrationForm, UserAddressForm, ProductCategoryForm
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.postgres.search import SearchVector
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import Sum,F
from django.db.models.functions import TruncMonth
# Create your views here.
User=get_user_model()

# dividing the products into a fixed length of lists for caraousels at home screen.
def chunks(lst,n):
    for i in range(0,len(lst),n):
        yield lst[i:i+n]

# getting items from database and organizing them by their categories using MPPT tree structure.
def home(request):
    # Get all root categories (no parent)
    root_categories = ProductCategories.objects.root_nodes()
    all_prods=contents.objects.select_related("category").all().order_by("-date")
    category = {}
    cat_ids_exclude=[]
    for root_cat in root_categories:
        if len(category)>=4:
            break
        # Get all descendants (including self) for this root category
        descendants = root_cat.get_descendants(include_self=True)
        # Get all products in this category tree
        items = all_prods.filter(category__in=descendants)[:8]
        if items.exists():
            # Organize items into chunks of 4 for carousel
            group = list(chunks(items, 4))
            category[root_cat] = group
            cat_ids_exclude.extend([item.id for item in items])
    all_prods=all_prods.exclude(id__in=cat_ids_exclude)
    paginator=Paginator(all_prods,4)
    page_number=request.GET.get("page")
    page_obj=paginator.get_page(page_number)
    # to improve UX and reduce the client side burden by instead of sending all products of application at once, if user hit the loader at intersection point of browser after scrolling then a fetch api will trigger the query of page number
    #  with header of XMLHttpRequest, then we will call the render_to_string function which will return the html page for the next paginator items
    #  for that page number requsted and finally we will return the JsonResponse to home page with those products html as string.
    if request.headers.get("X-Requested-With")=="XMLHttpRequest":
        html=render_to_string("shop/partial_products_list.html",context={"categories":page_obj})
        return JsonResponse({"html":html,"has_next":page_obj.has_next()})
    print("we are returning carousel items...")
    category_range = {cat: range(len(cat_items)) for cat, cat_items in category.items()}
    context={"category_groups":category,'category_range': category_range,"search_performed":False}
    # Create a range for template iteration
    return render(request, 'shop/index.html',context)
    
def checkout(request):
    return render(request,"shop/checkout_page.html")

# user registration logic coming for first time where we validate user and .
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

# this method is used to validate a user if there is the same username from which a user wants to sign up with username and/or email which is already in the database then we will make user to sign up with another username.
def validate(request):
    username=request.POST.get("username")
    email=request.POST.get("email")
    uname=User.objects.filter(username=username)
    e_mail=User.objects.filter(email=email)
    return {"username":uname,"email":e_mail}

# creating a merchant account for user who wants to add its business with this website.
def merchant_register(request):
    merchant=MerchantAccount.objects.filter(user=request.user).first()
    form=MerchantRegistrationForm(instance=merchant)
    return render(request,"shop/merchant_registration_form.html",{"merchant_form":form})
# creating merchant account by getting details from MerchantRegistrationForm and changing the role of user from 'CUSTOMER' to 'MERCHANT' and doing this by using transaction.atomic so if the process get failed at any point before saving it to database then this operation will get rollback to prevent it from creating inconsistencies in database.
@transaction.atomic
def create_merchant_account(request):
    if request.method=="POST" and request.user.is_authenticated:
        merchant_account=MerchantAccount.objects.filter(user=request.user).first()
        if merchant_account:
            messages.warning(request,"You have already a merchant account you can't update it.")
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
# showing the merchant its merchant dashboard by listing all products and stastistics.
def merchant_dashboard(request):
    if request.user.is_authenticated and request.user.role=="MERCHANT":
        merchant=MerchantAccount.objects.filter(user=request.user).first()
        line_chart_data=OrderItem.objects.filter(merchant=merchant)\
            .annotate(month=TruncMonth("order_date"))\
            .values("month")\
            .annotate(total_revenue=Sum("list_price_at_purchase"))\
            .order_by("month")
        profit_by_categories=OrderItem.objects.filter(merchant=merchant)\
        .values("product__category__category")\
        .annotate(total_category_profit=Sum((F("list_price_at_purchase")-F("base_price_at_purchase"))*F("quantity")))
        merchant=MerchantAccount.objects.filter(user=request.user).first()
        products=contents.objects.filter(user=merchant).order_by("-date")
        month_labels=[item['month'] for item in line_chart_data]
        monthly_sales=[float(item['total_revenue']) for item in line_chart_data]
        category_labels=[item['product__category__category'] for item in profit_by_categories]
        category_profits=[float(item['total_category_profit']) for item in profit_by_categories]
        context={
            "products":products,
            "month_labels":month_labels,
            "monthly_sales":monthly_sales,
            "category_labels":category_labels,
            "category_profits":category_profits,
        }
        return render(request,"shop/merchant_dashboard.html",context)
    messages.error("you are not authorized to view merchant page.")
    return redirect("home")

def registeration_view(request):
    return render(request,'shop/registration.html')

def login_view(request):
    return render(request,'shop/login.html')

def is_merchant_user(user):
    return user.role=="MERCHANT"

@login_required
@user_passes_test(is_merchant_user)
def add_content(request):
    operation="Add"
    catform=ProductCategoryForm()
    return render(request,"shop/add_content.html",{"operation":operation,"category_form":catform})

# a merchant can post it's product on the website if it is authenticated and staff members will also have access to products.
def upsert_content(request,product_id=None):
    if request.user.is_authenticated and request.user.role=="MERCHANT":
        product=None
        operation="Add"
        catform=ProductCategoryForm()
        merchant=get_object_or_404(MerchantAccount,user=request.user)
        if product_id is not None:
            operation="Update"
            product=get_object_or_404(contents,user=merchant,id=product_id)
            catform=ProductCategoryForm(initial={"parent":product.category})
        if request.method=="POST":
            title=request.POST.get("title")
            category=request.POST.get("parent")
            category=get_object_or_404(ProductCategories,id=category)
            publisher=request.POST.get("publisher")
            summary=request.POST.get("summary")
            base_price=request.POST.get("base_price")
            list_price=request.POST.get("list_price")
            image_path=None
            image_url=None
            if request.POST.get("img-option")=='url':
                image_url=request.POST.get("image_url")
            else:
                image_path=request.FILES.get("image")
            if product:
                product.title=title
                product.category=category
                product.publisher=publisher
                product.summary=summary
                product.base_price=base_price
                product.list_price=list_price
                if image_url:
                    product.image_url=image_url
                else:
                    product.image=image_path
                product.save()
                messages.success(request,f"product title {product.title} updated successfully.")
                return redirect("merchant_dashboard")
            else:
                item=contents.objects.filter(user=merchant,title=title)
                if(item):
                    messages.warning(request,"you have already this product in your shop you can update it from update page.")
                    return render(request,"shop/add_content.html",context={"category_form":catform})
                if image_url:
                    content=contents(user=merchant,category=category,summary=summary,title=title,publisher=publisher,base_price=base_price,list_price=list_price,image_url=image_url)
                    content.save()
                else:
                    content=contents(user=merchant,category=category,summary=summary,title=title,publisher=publisher,base_price=base_price,list_price=list_price,image=image_path)
                    content.save()
                messages.success(request,f"content {title} added successfully")
                return render(request,"shop/add_content.html",context={"category_form":catform})
        return render(request,"shop/add_content.html",{"product":product,"operation":operation,"category_form":catform})
    else: 
        messages.error(request,"You are not authorized to add content..!")
    return redirect("home")


def search_products(request):
    query = request.GET.get("query", "").strip()
    category = {}
    category_range = {}
    results=None
    if query:
        # Search across multiple fields: title, summary, publisher, and search_tags
        results = contents.objects.filter(
            summary__icontains=query
        ) | contents.objects.filter(
            publisher__icontains=query
        ) | contents.objects.filter(
            search_tags__icontains=query.lower()
        )
        
        # Remove duplicates and order by date
        results = results.distinct().order_by('-date')
        
        # Organize results by their category hierarchy
        if results.exists():
            category_dict = {}
            
            for product in results:
                # Get the root category for this product
                root_cat = product.category.get_root()
                
                if root_cat not in category_dict:
                    category_dict[root_cat] = []
                category_dict[root_cat].append(product)
            
            # Group items into chunks of 4 for carousel
            for cat, items in category_dict.items():
                group = list(chunks(items, 4))
                category[cat] = group
            
            # Create range for template iteration
            category_range = {cat: range(len(cat_items)) for cat, cat_items in category.items()}
    
    return render(request, "shop/index.html", {
        # 'category_groups': category,
        'categories':results,
        'category_range': category_range,
        'search_query': query,
        'search_performed': True
    })

# deleting item from application database.
def delete_item(request):
    if request.method=="POST":
        prod_id=request.POST.get("prod_id")
        product=get_object_or_404(contents,id=prod_id)
        title=product.title
        product.delete()
        return JsonResponse({"message":f"Item {title} deleted successfully."})
    return JsonResponse({"message":"error"},status=400)

# adding item to the cart
def add_to_cart(request):
    if request.method=="POST" and request.user.is_authenticated:
        item_id=request.POST.get("product_id")
        product=contents.objects.get(id=item_id)
        user_cart,created=Cart.objects.get_or_create(user=request.user,product=product)
        if not created:
            user_cart.quantity+=1
            user_cart.save()
        return JsonResponse({'status':'success','message':f"item {product.title} added to cart successfully"},status=200)
    return JsonResponse({"status":"login_required"},status=400)

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
                address_instance=UserAddressModel.objects.filter(user=request.user).first()
            address={
                "full_name":address_instance.full_name,
                "address_line":address_instance.address_line,
                "postal_code":address_instance.postal_code
            }
            messages.success(request,"Address added successfully")
            return JsonResponse({'status':'success',"message":"address saved successfully","user_address":address})
        else:
            AddressForm=UserAddressForm(instance=address_instance)
            return JsonResponse({"status":"warning","message":"please fill the address form","address":AddressForm})
    return JsonResponse({'status':"error","message":"invalid request method",},status=405)

# checkout page for creating order and payment backend.-- here is raozorpay test api and managing the order by each product to customer model and merchant model for further processing and after completion of payment integration the data will go to callback url for validation(success or error).
@transaction.atomic
def checkout_user(request):
    if request.method=="POST" and request.user.is_authenticated:
        try:
            data=json.loads(request.body)
            items=data.get("items")
            if not items:
                return JsonResponse({"status":"error","message":"you have no products available in cart."})
            temp_items=[]
            total_list_price=0
            for item in items:
                product=contents.objects.get(id=item["id"])
                product_list_price=product.list_price*item['quantity']
                total_list_price+=product_list_price
                temp_items.append({"product":product,"amount":product_list_price,"quantity":item["quantity"]})
            client=razorpay.Client(auth=(settings.RAZORPAY_TEST_API_KEY,settings.RAZORPAY_TEST_KEY_SECRET))
            razorpay_order = client.order.create({"amount": int(total_list_price) * 100, "currency": "INR", "payment_capture": "1"})
            order=Order.objects.create(user=request.user,order_id=razorpay_order['id'],amount=total_list_price)
            for item in temp_items: 
                OrderItem.objects.create(order=order,merchant=item['product'].user,product=item['product'],quantity=item['quantity'],base_price_at_purchase=item['product'].base_price,list_price_at_purchase=item['product'].list_price)
                MerchantPaymentAccount.objects.create(order=order,merchant=item['product'].user,amount=item['amount'])
            return JsonResponse({"razorpay_order_id":razorpay_order['id'],"amount":int(total_list_price)*100,"razorpay_merchant_key":settings.RAZORPAY_TEST_API_KEY,"currency":"INR","callback_url":"http://127.0.0.1:8000/callback/"},status=200)                
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
        merchant_payment_accounts=MerchantPaymentAccount.objects.filter(order=order)
        if verify_signature(request.POST):
            for merchants in merchant_payment_accounts:
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