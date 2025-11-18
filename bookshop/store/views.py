from django.http import HttpResponseRedirect
from django.contrib.auth.forms import UserCreationForm
from decimal import Decimal, InvalidOperation
import stripe
from django.conf import settings
from .models import Order, OrderItem
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .models import UserProfile
import requests
import random
from django.db.models import F, Sum
from .models import CartItem
from django.contrib import messages
from .forms import UserUpdateForm, ProfileUpdateForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import Favorite
from django.contrib.auth.decorators import login_required


stripe.api_key = settings.STRIPE_SECRET_KEY


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/store/login/')
    else:
        form = UserCreationForm()
    return render(request, 'store/signup.html', {'form': form})

@login_required
def home(request):
    random_query = random.choice(['python', 'life', 'history', 'science', 'novel', 'code', 'adventure'])
    response = requests.get(f'https://www.googleapis.com/books/v1/volumes?q={random_query}&maxResults=12')

    books = []
    if response.status_code == 200:
        data = response.json()
        for item in data.get('items', []):
            volume_info = item.get('volumeInfo', {})
            book = {
                'id': item.get('id'),
                'title': volume_info.get('title', 'No title'),
                'authors': volume_info.get('authors', ['Unknown']),
                'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail'),
                'price': round(random.uniform(100, 500), 2)  # dummy price
            }
            books.append(book)

    return render(request, 'store/home.html', {'books': books})

def search_books(request):
    query = request.GET.get('q')
    books = []

    if query:
        url = f'https://www.googleapis.com/books/v1/volumes?q={query}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            books = data.get('items', [])

    return render(request, 'store/search.html', {'books': books, 'query': query})


@login_required
def add_to_cart(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        title = request.POST.get('title')
        thumbnail = request.POST.get('thumbnail')
        price = request.POST.get('price')

        # If price is empty or invalid, set a fake price
        try:
            price = Decimal(price)
        except (ValueError, TypeError, InvalidOperation):
            price = Decimal(random.randint(100, 500))  # ₹100–₹500

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            book_id=book_id,
            defaults={
                'title': title,
                'thumbnail': thumbnail,
                'price': price
            }
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(user=request.user)

    # ✅ Calculate subtotal for each item (for safety in template)
    for item in cart_items:
        item.subtotal = item.price * item.quantity

    # ✅ Calculate total cart amount
    cart_total = sum(item.subtotal for item in cart_items)

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
    })


@login_required
def update_cart(request):
    if request.method == 'POST':
        if 'increase' in request.POST:
            item_id = request.POST.get('increase')
            cart_item = CartItem.objects.get(id=item_id, user=request.user)
            cart_item.quantity += 1
            cart_item.save()

        elif 'decrease' in request.POST:
            item_id = request.POST.get('decrease')
            cart_item = CartItem.objects.get(id=item_id, user=request.user)
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()

        elif 'remove' in request.POST:
            item_id = request.POST.get('remove')
            CartItem.objects.filter(id=item_id, user=request.user).delete()

    return redirect('view_cart')

@login_required
def create_checkout_session(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items:
        return redirect('view_cart')

    line_items = []
    for item in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': item.title,
                },
                'unit_amount': int(item.price * 100),  # Stripe expects amount in paisa
            },
            'quantity': item.quantity,
        })

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri('/store/payment/success/'),
        cancel_url=request.build_absolute_uri('/cart/'),
        customer_email=request.user.email if request.user.email else None,
    )


    return redirect(checkout_session.url, code=303)


@login_required
def payment_success(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items:
        return redirect('view_cart')

    total_price = sum(item.price * item.quantity for item in cart_items)

    order = Order.objects.create(user=request.user, total_price=total_price)

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            title=item.title,
            price=item.price,
            quantity=item.quantity,
            thumbnail=item.thumbnail,
        )

    cart_items.delete()

    return render(request, 'store/payment_successfull.html', {'order': order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})


@login_required
def user_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'store/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'store/change_password.html'
    success_url = reverse_lazy('profile')

@login_required
def book_detail(request, book_id):
    url = f'https://www.googleapis.com/books/v1/volumes/{book_id}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        volume = data.get('volumeInfo', {})

        book = {
            'id': book_id,
            'title': volume.get('title', 'No title'),
            'authors': volume.get('authors', ['Unknown']),
            'thumbnail': volume.get('imageLinks', {}).get('thumbnail'),
            'description': volume.get('description', 'No description available.'),
            'price': round(random.uniform(100, 500), 2),  # dummy price
        }

        return render(request, 'store/book_detail.html', {'book': book})

    return render(request, 'store/book_detail.html', {'error': 'Book not found.'})



def cart_view(request):
    user = request.user

    cart_items = CartItem.objects.filter(user=user)

    # Annotate subtotal for each item (optional, for display)
    for item in cart_items:
        item.subtotal = item.book.price * item.quantity

    # Calculate total price
    cart_total = cart_items.aggregate(
        total=Sum(F('book__price') * F('quantity'))
    )['total'] or 0

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'store/cart.html', context)


@login_required
def profile_view(request):
    return render(request, 'store/profile_view.html', {
        'user': request.user,
        'profile': request.user.userprofile
    })

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.userprofile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.userprofile)

    return render(request, 'store/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

#FAVOURITES

@login_required
def add_favorite(request, book_id):
    # book_id from the external API
    title = request.POST.get('title')
    authors = request.POST.get('authors')
    thumbnail = request.POST.get('thumbnail')
    description = request.POST.get('description')

    Favorite.objects.get_or_create(
        user=request.user,
        book_id=book_id,
        defaults={
            'title': title,
            'authors': authors,
            'thumbnail': thumbnail,
            'description': description,
        }
    )
    return redirect('favorites')




@login_required
def remove_favorite(request, book_id):
    Favorite.objects.filter(user=request.user, book_id=book_id).delete()
    return redirect('my_favorites')


@login_required
def my_favorites(request):
    favorites = Favorite.objects.all()
    return render(request, 'store/my_favorites.html', {'favorites': favorites})






