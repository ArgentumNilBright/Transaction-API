from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from main.views import DepositAPIView, WithdrawalAPIView, TransferAPIView, GetUserBalanceAPIView, \
    GetUserTransactionsAPIView

urlpatterns = [
    path('api/v1/transactions/deposit/', DepositAPIView.as_view(), name='deposit'),
    path('api/v1/transactions/withdrawal/', WithdrawalAPIView.as_view(), name='withdrawal'),
    path('api/v1/transactions/transfer/', TransferAPIView.as_view(), name='transfer'),
    path('api/v1/users/<int:user_id>/transactions/', GetUserTransactionsAPIView.as_view(), name='get_user_transactions'),
    path('api/v1/users/<int:user_id>/balance/', GetUserBalanceAPIView.as_view(), name='get_user_balance'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
