# Criar pedidos/serializers.py
from rest_framework import serializers
from .models import Pedido, HistoricoPedido

class HistoricoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = HistoricoPedido
        fields = '__all__'

class PedidoSerializer(serializers.ModelSerializer):
    historico = HistoricoSerializer(many=True, read_only=True)
    estudante_nome = serializers.CharField(source='estudante.get_full_name', read_only=True)
    estudante_curso = serializers.CharField(source='estudante.curso', read_only=True)
    
    class Meta:
        model = Pedido
        fields = '__all__'
        read_only_fields = ['estudante', 'estado', 'responsavel_atual']