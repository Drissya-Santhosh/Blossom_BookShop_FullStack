from django.urls import path
from . import views
from .views import CustomPasswordChangeView
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.signup, name='signup'),
    path('home/', views.home, name='home'),

    # Custom login/logout
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('search/', views.search_books, name='search_books'),
    # path('favorite/', views.add_to_favorites, name='add_to_favorites'),
    # path('favorites/', views.my_favorites, name='favorites'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/checkout/', views.create_checkout_session, name='checkout'),
    path('cart/success/', views.payment_success, name='payment_success'),
    path('orders/history/', views.order_history, name='order_history'),
    # path('profile/', views.user_profile, name='user_profile'),
    path('profile/change-password/', CustomPasswordChangeView.as_view(), name='change_password'),
    path('book/<str:book_id>/', views.book_detail, name='book_detail'),
    # path('favorites/remove/', views.remove_from_favorites, name='remove_from_favorites'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('payment/success/', views.payment_success, name='cart_success'),

    #FAVOURITES

    path('favorites/', views.my_favorites, name='my_favorites'),
    path('favorites/add/<str:book_id>/', views.add_favorite, name='add_favorite'),
    path('favorites/remove/<str:book_id>/', views.remove_favorite, name='remove_favorite')




]
