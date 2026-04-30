from django.urls import path
from . import views

urlpatterns = [
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    path('pedidos/criar/', views.criar_pedido, name='criar_pedido'),
    path('pedidos/<int:pedido_id>/', views.detalhe_pedido, name='detalhe_pedido'),
    path('pedidos/<int:pedido_id>/aprovar/', views.aprovar_pedido, name='aprovar_pedido'),
    path('pedidos/<int:pedido_id>/rejeitar/', views.rejeitar_pedido, name='rejeitar_pedido'),
    path('pedidos/<int:pedido_id>/passar/', views.passar_responsabilidade, name='passar_responsabilidade'),
]