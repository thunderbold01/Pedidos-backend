from django.contrib import admin
from .models import Pedido, HistoricoPedido, Notificacao

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'estudante', 'tipo', 'estado', 'responsavel_atual', 'created_at']
    list_filter = ['estado', 'tipo', 'responsavel_atual']
    search_fields = ['estudante__email', 'estudante__first_name', 'motivo']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']

@admin.register(HistoricoPedido)
class HistoricoPedidoAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'acao', 'usuario', 'role_usuario', 'data']
    list_filter = ['acao', 'role_usuario']
    date_hierarchy = 'data'

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo', 'lida', 'data']
    list_filter = ['tipo', 'lida']
    search_fields = ['usuario__email', 'mensagem']