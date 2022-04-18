from django.urls import path
from . import views

app_name = 'pricePredict'

urlpatterns = [
    path('<int:product_id>/', views.priceViewbyParam, name='test'),
]
