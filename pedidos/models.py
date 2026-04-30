from django.db import models
from django.conf import settings

class EstadoPedido(models.TextChoices):
    PENDENTE_DITE = 'PENDENTE_DITE', 'Verde - Pendente DITE'
    PENDENTE_DIRECAO = 'PENDENTE_DIRECAO', 'Amarelo - Pendente Direção'
    PENDENTE_ADMIN = 'PENDENTE_ADMIN', 'Vermelho - Pendente Admin'
    APROVADO = 'APROVADO', 'Aprovado'
    REJEITADO = 'REJEITADO', 'Rejeitado'

class TipoPedido(models.TextChoices):
    MEDICOS = 'medicos', 'Médicos'
    OUTROS = 'outros', 'Outros'
    DOCUMENTOS = 'documentos', 'Documentos'
    ESCOLA = 'escola', 'Sugerido pela Escola'
    COLETIVA = 'coletiva', 'Saída Coletiva'

class Pedido(models.Model):
    estudante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pedidos'
    )
    tipo = models.CharField(max_length=20, choices=TipoPedido.choices)
    motivo = models.TextField()
    data_saida = models.DateTimeField()
    hora_saida = models.TimeField()
    
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.PENDENTE_DITE
    )
    responsavel_atual = models.CharField(
        max_length=20,
        choices=[('DITE', 'DITE'), ('DIRECAO', 'Direção'), ('ADMIN', 'Admin')],
        default='DITE'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pedidos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pedido {self.id} - {self.estudante}"

class HistoricoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historico')
    acao = models.CharField(max_length=100)
    de_responsavel = models.CharField(max_length=20)
    para_responsavel = models.CharField(max_length=20)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    data = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)
    
    class Meta:
        db_table = 'historico_pedidos'
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.acao} - {self.data}"