# pedidos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    path('pedidos/criar/', views.criar_pedido, name='criar_pedido'),
    path('pedidos/<int:pedido_id>/', views.detalhe_pedido, name='detalhe_pedido'),
    path('pedidos/<int:pedido_id>/aprovar/', views.aprovar_pedido, name='aprovar_pedido'),
    path('pedidos/<int:pedido_id>/rejeitar/', views.rejeitar_pedido, name='rejeitar_pedido'),
    path('pedidos/<int:pedido_id>/passar/', views.passar_pedido, name='passar_pedido'),
    path('pedidos/<int:pedido_id>/passar-dite/', views.passar_pedido_dite, name='passar_pedido_dite'),
    path('seguranca/dashboard/', views.dashboard_seguranca, name='dashboard_seguranca'),
    path('pedidos/<int:pedido_id>/marcar-saida/', views.marcar_saida, name='marcar_saida'),
    path('pedidos/<int:pedido_id>/marcar-retorno/', views.marcar_retorno, name='marcar_retorno'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('seguranca/relatorio/', views.relatorio_seguranca, name='relatorio_seguranca'),
    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path('notificacoes/<int:notificacao_id>/ler/', views.marcar_notificacao_lida, name='marcar_notificacao_lida'),
    path('notificacoes/ler-todas/', views.marcar_todas_lidas, name='marcar_todas_lidas'),
]
