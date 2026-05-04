from django.urls import path
from . import views

urlpatterns = [
    # Dashboard e listagem
    path('dashboard/', views.dashboard, name='dashboard'),
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    
    # CRUD de pedidos
    path('pedidos/criar/', views.criar_pedido, name='criar_pedido'),
    path('pedidos/<int:pedido_id>/', views.detalhe_pedido, name='detalhe_pedido'),
    
    # Ações nos pedidos
    path('pedidos/<int:pedido_id>/aprovar/', views.aprovar_pedido, name='aprovar_pedido'),
    path('pedidos/<int:pedido_id>/rejeitar/', views.rejeitar_pedido, name='rejeitar_pedido'),
    path('pedidos/<int:pedido_id>/passar/', views.passar_pedido, name='passar_pedido'),
    
    # Notificações
    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path('notificacoes/<int:notificacao_id>/ler/', views.marcar_notificacao_lida, name='marcar_notificacao_lida'),
    path('notificacoes/ler-todas/', views.marcar_todas_lidas, name='marcar_todas_lidas'),
    
    # Relatórios
    path('relatorios/', views.relatorios, name='relatorios'),
    path('pedidos/<int:pedido_id>/passar-dite/', views.passar_pedido_dite,  name='passar_pedido_dite'),

]