# E-Commerce-Application
this repository contains a django project related to web and e-commerce where I(developer) tried to simulate a real e-commerce application like managing users, authentication , abstractions, payment methods, database connectivity and storage, managing permissions etc.

# Multi-Vendor E-Commerce Platform

An e-commerce application with rich features, developed using Django, emphasizing scalability, merchant analytics, and efficient data loading.

## 🚀 Key Features
* **Infinite Scroll Interface:** Asynchronous product loading using AJAX and the Intersection Observer API.
* **Complex Category Management:** Implemented using `django-mptt` for optimal management of hierarchical data.
* **Merchant Analytics Dashboard:** Real-time Chart.js charts (Line, Bar, Pie) for revenue and profit analysis.
* **Secure Checkout:** Fully integrated with Razorpay Payment Gateway.
* **Database Optimization:** Strategic indexing and QuerySet optimization (`select_related`, `F` expressions).

## 🛠️ Tech Stack
* **Backend:** Python, Django
* **Database:** PostgreSQL (or SQLite)
* **Frontend:** JavaScript (ES6+), jQuery, Bootstrap 5
* **Data Viz:** Chart.js
* **Payments:** Razorpay API

## 📦 Dependencies
Make sure you have the following packages installed:
- `django`
- `django-mptt`
- `razorpay`
- 'dotenv'
- 'django-allauth'

## 📸 Screenshots
| Home Page (Infinite Scroll) | Merchant Dashboard (Analytics) |
| :--- | :--- |
| ![Home](shop/e-commerce-project-screenshots/index_page.png) | ![Dashboard](shop/e-commerce-project-screenshots/merchant_dashboard.png) |![CheckoutPage](shop/e-commerce-project-screenshots/checkout_page.png) | ![RazorpayPaymentSuccess](shop/e-commerce-project-screenshots/razorpay_payment.png) |![SearchProducts](shop/e-commerce-project-screenshots/search_products.png) | ![GoogleAuth](shop/e-commerce-project-screenshots/google_authorization.png) |
