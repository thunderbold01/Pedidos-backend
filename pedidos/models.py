# pedidos/models.py
from django.db import models
from django.conf import settings

class EstadoPedido(models.TextChoices):
    PENDENTE_DITE = 'PENDENTE_DITE', '🟢 Pendente DITE'
    PENDENTE_DIRECAO = 'PENDENTE_DIRECAO', '🟡 Pendente Direção/Administração'
    PENDENTE_ADMIN = 'PENDENTE_ADMIN', '🔴 Pendente Admin'
    APROVADO = 'APROVADO', '✅ Aprovado'
    REJEITADO = 'REJEITADO', '❌ Rejeitado'
    EM_ANDAMENTO = 'EM_ANDAMENTO', '🚶 Em Andamento'
    FINALIZADO = 'FINALIZADO', '🏁 Finalizado'

class TipoPedido(models.TextChoices):
    MEDICOS = 'medicos', '🏥 Médicos'
    OUTROS = 'outros', '📋 Outros'
    DOCUMENTOS = 'documentos', '📄 Documentos'
    ESCOLA = 'escola', '🏫 Sugerido pela Escola'
    COLETIVA = 'coletiva', '👥 Saída Coletiva'

class Pedido(models.Model):
    estudante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pedidos'
    )
    tipo = models.CharField(max_length=20, choices=TipoPedido.choices)
    motivo = models.TextField()
    
    # Datas sugeridas pelo estudante
    data_saida = models.DateTimeField()
    data_volta = models.DateTimeField(null=True, blank=True)
    hora_saida = models.TimeField(null=True, blank=True)
    
    # Datas confirmadas/aprovadas (podem ser alteradas por DITE/Direção/Admin)
    data_saida_confirmada = models.DateTimeField(null=True, blank=True)
    data_volta_confirmada = models.DateTimeField(null=True, blank=True)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='datas_alteradas'
    )
    motivo_alteracao_data = models.TextField(blank=True, null=True)
    
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.PENDENTE_DITE
    )
    responsavel_atual = models.CharField(max_length=20, default='DITE')
    
    # Decisões
    decisao_dite = models.CharField(max_length=20, null=True, blank=True)
    decisao_direcao = models.CharField(max_length=20, null=True, blank=True)
    decisao_administracao = models.CharField(max_length=20, null=True, blank=True)
    decisao_admin = models.CharField(max_length=20, null=True, blank=True)
    
    data_decisao_dite = models.DateTimeField(null=True, blank=True)
    data_decisao_direcao = models.DateTimeField(null=True, blank=True)
    data_decisao_administracao = models.DateTimeField(null=True, blank=True)
    data_decisao_admin = models.DateTimeField(null=True, blank=True)
    
    # Controle de saída (Segurança)
    hora_saida_real = models.DateTimeField(null=True, blank=True)
    hora_retorno_real = models.DateTimeField(null=True, blank=True)
    atrasado = models.BooleanField(default=False)
    tempo_atraso = models.IntegerField(default=0)
    observacao_seguranca = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pedidos'
        ordering = ['-created_at']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
    
    def __str__(self):
        return f"Pedido #{self.id} - {self.estudante.get_full_name()}"
    
    def get_cor_estado(self):
        cores = {
            'PENDENTE_DITE': '#10b981',
            'PENDENTE_DIRECAO': '#f59e0b',
            'PENDENTE_ADMIN': '#ef4444',
            'APROVADO': '#10b981',
            'REJEITADO': '#ef4444',
            'EM_ANDAMENTO': '#3b82f6',
            'FINALIZADO': '#6b7280',
        }
        return cores.get(self.estado, '#6b7280')
    
    def get_icone_estado(self):
        icones = {
            'PENDENTE_DITE': '🟢',
            'PENDENTE_DIRECAO': '🟡',
            'PENDENTE_ADMIN': '🔴',
            'APROVADO': '✅',
            'REJEITADO': '❌',
            'EM_ANDAMENTO': '🚶',
            'FINALIZADO': '🏁',
        }
        return icones.get(self.estado, '❓')
    
    def verificar_atraso(self):
        """Verifica se o estudante está atrasado"""
        if self.hora_retorno_real and self.data_volta_confirmada:
            if self.hora_retorno_real > self.data_volta_confirmada:
                self.atrasado = True
                diferenca = self.hora_retorno_real - self.data_volta_confirmada
                self.tempo_atraso = int(diferenca.total_seconds() / 60)
                self.save()
                return True
        return False


class HistoricoPedido(models.Model):
    ACAO_CHOICES = [
        ('CRIADO', 'Pedido Criado'),
        ('APROVADO_DITE', 'Aprovado pelo DITE'),
        ('REJEITADO_DITE', 'Rejeitado pelo DITE'),
        ('PASSADO_DIRECAO', 'Encaminhado para Direção/Administração'),
        ('APROVADO_DIRECAO', 'Aprovado pela Direção'),
        ('REJEITADO_DIRECAO', 'Rejeitado pela Direção'),
        ('APROVADO_ADMINISTRACAO', 'Aprovado pela Administração'),
        ('REJEITADO_ADMINISTRACAO', 'Rejeitado pela Administração'),
        ('PASSADO_ADMIN', 'Encaminhado para Admin'),
        ('APROVADO_ADMIN', 'Aprovado pelo Admin'),
        ('REJEITADO_ADMIN', 'Rejeitado pelo Admin'),
        ('EDITADO', 'Pedido Editado'),
        ('DELETADO', 'Pedido Deletado'),
        ('INICIAR_ANDAMENTO', 'Saída Iniciada'),
        ('FINALIZAR_SAIDA', 'Saída Finalizada'),
        ('DATAS_ALTERADAS', 'Datas Alteradas'),
    ]
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historico')
    acao = models.CharField(max_length=30, choices=ACAO_CHOICES)
    de_estado = models.CharField(max_length=20, null=True, blank=True)
    para_estado = models.CharField(max_length=20, null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='acoes_historico'
    )
    role_usuario = models.CharField(max_length=20, null=True, blank=True)
    comentario = models.TextField(blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'historico_pedidos'
        ordering = ['-data']


class Relatorio(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    dados = models.JSONField(default=dict)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'relatorios'
        ordering = ['-created_at']


class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('NOVO_PEDIDO', 'Novo Pedido'),
        ('PEDIDO_APROVADO', 'Pedido Aprovado'),
        ('PEDIDO_REJEITADO', 'Pedido Rejeitado'),
        ('PEDIDO_ENCAMINHADO', 'Pedido Encaminhado'),
        ('DATAS_ALTERADAS', 'Datas Alteradas'),
        ('SAIDA_INICIADA', 'Saída Iniciada'),
        ('SAIDA_FINALIZADA', 'Saída Finalizada'),
        ('ATRASO', 'Atraso Registrado'),
        ('SISTEMA', 'Notificação do Sistema'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificacoes')
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True, blank=True, related_name='notificacoes')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    data = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notificacoes'
        ordering = ['-data']