# pedidos/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta

from .models import Pedido, HistoricoPedido, EstadoPedido, Notificacao, TipoPedido, SaidaColetiva, ConviteColetiva
from accounts.models import User

# ==================== FUNÇÕES AUXILIARES ====================

def criar_notificacao(usuario, pedido, tipo, mensagem):
    """Cria uma notificação para o usuário"""
    try:
        return Notificacao.objects.create(
            usuario=usuario,
            pedido=pedido,
            tipo=tipo,
            mensagem=mensagem
        )
    except Exception as e:
        print(f"Erro ao criar notificação: {e}")
        return None

def pode_gerenciar_pedido(user, pedido):
    """Verifica se o usuário pode aprovar/rejeitar o pedido"""
    if pedido.estado in [EstadoPedido.APROVADO, EstadoPedido.REJEITADO]:
        return False
    
    # ADMIN pode tudo
    if user.role == 'ADMIN':
        return True
    
    # DITE só pode gerenciar pedidos PENDENTE_DITE
    if user.role == 'DITE':
        return pedido.estado == EstadoPedido.PENDENTE_DITE
    
    # DIREÇÃO só pode gerenciar pedidos PENDENTE_DIRECAO encaminhados para ela
    if user.role == 'DIRECAO':
        return pedido.estado == EstadoPedido.PENDENTE_DIRECAO and pedido.responsavel_atual == 'DIRECAO'
    
    # ADMINISTRAÇÃO só pode gerenciar pedidos PENDENTE_DIRECAO encaminhados para ela
    if user.role == 'ADMINISTRACAO':
        return pedido.estado == EstadoPedido.PENDENTE_DIRECAO and pedido.responsavel_atual == 'ADMINISTRACAO'
    
    # ESTUDANTE e SEGURANCA não podem gerenciar
    return False

def pode_passar_pedido(user, pedido):
    """Verifica se o usuário pode passar o pedido adiante"""
    if pedido.estado in [EstadoPedido.APROVADO, EstadoPedido.REJEITADO]:
        return False
    
    # ADMIN pode passar qualquer pedido pendente
    if user.role == 'ADMIN':
        return pedido.estado in [EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]
    
    # DITE pode passar pedidos PENDENTE_DITE
    if user.role == 'DITE':
        return pedido.estado == EstadoPedido.PENDENTE_DITE
    
    # DIREÇÃO e ADMINISTRAÇÃO podem passar para ADMIN
    if user.role in ['DIRECAO', 'ADMINISTRACAO']:
        return pedido.estado == EstadoPedido.PENDENTE_DIRECAO and pedido.responsavel_atual == user.role
    
    return False

# ==================== DASHBOARD ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Dashboard com estatísticas específicas por role"""
    user = request.user
    
    try:
        if user.role == 'ESTUDANTE':
            total_pedidos = Pedido.objects.filter(estudante=user).count()
            pedidos_pendentes = Pedido.objects.filter(
                estudante=user,
                estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]
            ).count()
            pedidos_aprovados = Pedido.objects.filter(estudante=user, estado=EstadoPedido.APROVADO).count()
            pedidos_rejeitados = Pedido.objects.filter(estudante=user, estado=EstadoPedido.REJEITADO).count()
            
            # Saídas coletivas pendentes
            coletivas_pendentes = ConviteColetiva.objects.filter(
                estudante=user, 
                estado='PENDENTE'
            ).count()
            
            return Response({
                'total_pedidos': total_pedidos,
                'pedidos_pendentes': pedidos_pendentes,
                'pedidos_aprovados': pedidos_aprovados,
                'pedidos_rejeitados': pedidos_rejeitados,
                'coletivas_pendentes': coletivas_pendentes,
            })
        
        elif user.role == 'DITE':
            meus_pedidos = Pedido.objects.filter(estado=EstadoPedido.PENDENTE_DITE)
            coletivas_ativas = SaidaColetiva.objects.filter(
                prazo_resposta__gt=timezone.now()
            ).count()
            
            return Response({
                'total_pedidos': Pedido.objects.count(),
                'pedidos_pendentes': Pedido.objects.filter(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]).count(),
                'pedidos_aprovados': Pedido.objects.filter(estado=EstadoPedido.APROVADO).count(),
                'pedidos_rejeitados': Pedido.objects.filter(estado=EstadoPedido.REJEITADO).count(),
                'meus_pedidos_pendentes': meus_pedidos.count(),
                'coletivas_ativas': coletivas_ativas,
            })
        
        elif user.role == 'DIRECAO':
            meus_pedidos = Pedido.objects.filter(estado=EstadoPedido.PENDENTE_DIRECAO, responsavel_atual='DIRECAO')
            return Response({
                'total_pedidos': Pedido.objects.count(),
                'pedidos_pendentes': Pedido.objects.filter(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]).count(),
                'pedidos_aprovados': Pedido.objects.filter(estado=EstadoPedido.APROVADO).count(),
                'pedidos_rejeitados': Pedido.objects.filter(estado=EstadoPedido.REJEITADO).count(),
                'meus_pedidos_pendentes': meus_pedidos.count(),
            })
        
        elif user.role == 'ADMINISTRACAO':
            meus_pedidos = Pedido.objects.filter(estado=EstadoPedido.PENDENTE_DIRECAO, responsavel_atual='ADMINISTRACAO')
            return Response({
                'total_pedidos': Pedido.objects.count(),
                'pedidos_pendentes': Pedido.objects.filter(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]).count(),
                'pedidos_aprovados': Pedido.objects.filter(estado=EstadoPedido.APROVADO).count(),
                'pedidos_rejeitados': Pedido.objects.filter(estado=EstadoPedido.REJEITADO).count(),
                'meus_pedidos_pendentes': meus_pedidos.count(),
            })
        
        else:  # ADMIN e outros
            coletivas_ativas = SaidaColetiva.objects.filter(
                prazo_resposta__gt=timezone.now()
            ).count()
            
            return Response({
                'total_pedidos': Pedido.objects.count(),
                'pedidos_pendentes': Pedido.objects.filter(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]).count(),
                'pedidos_aprovados': Pedido.objects.filter(estado=EstadoPedido.APROVADO).count(),
                'pedidos_rejeitados': Pedido.objects.filter(estado=EstadoPedido.REJEITADO).count(),
                'meus_pedidos_pendentes': Pedido.objects.filter(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]).count(),
                'coletivas_ativas': coletivas_ativas,
            })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== LISTAR PEDIDOS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_pedidos(request):
    """Listar pedidos com filtros por role"""
    user = request.user
    
    try:
        # Base query conforme role
        if user.role == 'ESTUDANTE':
            pedidos = Pedido.objects.filter(estudante=user)
        elif user.role == 'DITE':
            pedidos = Pedido.objects.all()
        elif user.role == 'DIRECAO':
            pedidos = Pedido.objects.filter(
                Q(estado=EstadoPedido.PENDENTE_DIRECAO, responsavel_atual='DIRECAO') |
                Q(estado=EstadoPedido.APROVADO) |
                Q(estado=EstadoPedido.REJEITADO) |
                Q(estado=EstadoPedido.PENDENTE_ADMIN)
            )
        elif user.role == 'ADMINISTRACAO':
            pedidos = Pedido.objects.filter(
                Q(estado=EstadoPedido.PENDENTE_DIRECAO, responsavel_atual='ADMINISTRACAO') |
                Q(estado=EstadoPedido.APROVADO) |
                Q(estado=EstadoPedido.REJEITADO) |
                Q(estado=EstadoPedido.PENDENTE_ADMIN)
            )
        else:  # ADMIN vê tudo
            pedidos = Pedido.objects.all()
        
        # Filtros
        estado = request.GET.get('estado')
        tipo = request.GET.get('tipo')
        busca = request.GET.get('busca')
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        
        if estado:
            pedidos = pedidos.filter(estado=estado)
        if tipo:
            pedidos = pedidos.filter(tipo=tipo)
        if busca:
            pedidos = pedidos.filter(
                Q(estudante__first_name__icontains=busca) |
                Q(estudante__last_name__icontains=busca) |
                Q(estudante__email__icontains=busca) |
                Q(motivo__icontains=busca) |
                Q(id__icontains=busca)
            )
        if data_inicio:
            pedidos = pedidos.filter(data_saida__gte=data_inicio)
        if data_fim:
            pedidos = pedidos.filter(data_saida__lte=data_fim)
        
        pedidos = pedidos.order_by('-created_at')
        
        dados = []
        for pedido in pedidos:
            acoes_disponiveis = []
            if pode_gerenciar_pedido(user, pedido):
                acoes_disponiveis.extend(['aprovar', 'rejeitar'])
            if pode_passar_pedido(user, pedido):
                acoes_disponiveis.append('passar')
            
            dados.append({
                'id': pedido.id,
                'tipo': pedido.tipo,
                'tipo_display': pedido.get_tipo_display(),
                'motivo': pedido.motivo,
                'data_saida': pedido.data_saida.strftime('%d/%m/%Y %H:%M') if pedido.data_saida else '',
                'hora_saida': pedido.data_saida.strftime('%H:%M') if pedido.data_saida else '',
                'data_volta': pedido.data_volta.strftime('%d/%m/%Y %H:%M') if pedido.data_volta else '',
                'data_saida_confirmada': pedido.data_saida_confirmada.strftime('%d/%m/%Y %H:%M') if pedido.data_saida_confirmada else '',
                'data_volta_confirmada': pedido.data_volta_confirmada.strftime('%d/%m/%Y %H:%M') if pedido.data_volta_confirmada else '',
                'estado': pedido.estado,
                'estado_display': pedido.get_estado_display(),
                'responsavel_atual': pedido.responsavel_atual,
                'estudante_id': pedido.estudante.id,
                'estudante_nome': pedido.estudante.get_full_name() or pedido.estudante.username,
                'estudante_email': pedido.estudante.email,
                'estudante_curso': pedido.estudante.curso or '',
                'estudante_classe': pedido.estudante.classe or '',
                'created_at': pedido.created_at.strftime('%d/%m/%Y %H:%M'),
                'acoes_disponiveis': acoes_disponiveis,
            })
        
        return Response({'pedidos': dados, 'total': len(dados)})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== CRIAR PEDIDO (APENAS ESTUDANTE) ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def criar_pedido(request):
    """Criar novo pedido - apenas estudantes"""
    user = request.user
    
    try:
        if user.role != 'ESTUDANTE':
            return Response({'error': 'Apenas estudantes podem criar pedidos'}, status=status.HTTP_403_FORBIDDEN)
        
        tipo = request.data.get('tipo')
        motivo = request.data.get('motivo')
        data_saida = request.data.get('data_saida')
        hora_saida = request.data.get('hora_saida', '07:00')
        data_volta = request.data.get('data_volta')
        hora_volta = request.data.get('hora_volta', '12:00')
        
        if not all([tipo, motivo, data_saida]):
            return Response({'error': 'Tipo, motivo e data de saída são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Combinar data e hora
        from datetime import datetime
        data_hora_saida = datetime.strptime(f"{data_saida} {hora_saida}", '%Y-%m-%d %H:%M')
        
        data_hora_volta = None
        if data_volta:
            data_hora_volta = datetime.strptime(f"{data_volta} {hora_volta}", '%Y-%m-%d %H:%M')
        else:
            # Padrão: mesmo dia, 12:00
            data_hora_volta = datetime.strptime(f"{data_saida} 12:00", '%Y-%m-%d %H:%M')
        
        pedido = Pedido.objects.create(
            estudante=user,
            tipo=tipo,
            motivo=motivo,
            data_saida=data_hora_saida,
            data_volta=data_hora_volta,
            estado=EstadoPedido.PENDENTE_DITE,
            responsavel_atual='DITE'
        )
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao='CRIADO',
            para_estado=EstadoPedido.PENDENTE_DITE,
            usuario=user,
            role_usuario=user.role
        )
        
        # Notificar DITE
        for u in User.objects.filter(role='DITE'):
            criar_notificacao(u, pedido, 'NOVO_PEDIDO', 
                f'Novo pedido de {user.get_full_name() or user.username}')
        
        return Response({'message': 'Pedido criado com sucesso', 'pedido_id': pedido.id}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== DETALHE PEDIDO ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalhe_pedido(request, pedido_id):
    """Detalhes do pedido"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if user.role == 'ESTUDANTE' and pedido.estudante != user:
            return Response({'error': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        acoes_disponiveis = []
        if pode_gerenciar_pedido(user, pedido):
            acoes_disponiveis.extend(['aprovar', 'rejeitar'])
        if pode_passar_pedido(user, pedido):
            acoes_disponiveis.append('passar')
        
        return Response({
            'id': pedido.id,
            'tipo': pedido.tipo,
            'tipo_display': pedido.get_tipo_display(),
            'motivo': pedido.motivo,
            'data_saida': pedido.data_saida.strftime('%d/%m/%Y %H:%M') if pedido.data_saida else '',
            'data_volta': pedido.data_volta.strftime('%d/%m/%Y %H:%M') if pedido.data_volta else '',
            'data_saida_confirmada': pedido.data_saida_confirmada.strftime('%d/%m/%Y %H:%M') if pedido.data_saida_confirmada else None,
            'data_volta_confirmada': pedido.data_volta_confirmada.strftime('%d/%m/%Y %H:%M') if pedido.data_volta_confirmada else None,
            'estado': pedido.estado,
            'estado_display': pedido.get_estado_display(),
            'responsavel_atual': pedido.responsavel_atual,
            'decisao_dite': pedido.decisao_dite,
            'decisao_direcao': pedido.decisao_direcao,
            'decisao_administracao': pedido.decisao_administracao,
            'decisao_admin': pedido.decisao_admin,
            'hora_saida_real': pedido.hora_saida_real.strftime('%H:%M') if pedido.hora_saida_real else None,
            'hora_retorno_real': pedido.hora_retorno_real.strftime('%H:%M') if pedido.hora_retorno_real else None,
            'atrasado': pedido.atrasado,
            'tempo_atraso': pedido.tempo_atraso,
            'estudante': {
                'id': pedido.estudante.id,
                'nome': pedido.estudante.get_full_name() or pedido.estudante.username,
                'email': pedido.estudante.email,
                'curso': pedido.estudante.curso,
                'classe': pedido.estudante.classe,
            },
            'created_at': pedido.created_at.strftime('%d/%m/%Y %H:%M'),
            'acoes_disponiveis': acoes_disponiveis,
            'historico': [{
                'id': h.id,
                'acao': h.acao,
                'acao_display': h.get_acao_display(),
                'usuario_nome': h.usuario.get_full_name() if h.usuario else 'Sistema',
                'role_usuario': h.role_usuario,
                'comentario': h.comentario,
                'data': h.data.strftime('%d/%m/%Y %H:%M'),
            } for h in pedido.historico.all()]
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== APROVAR PEDIDO ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def aprovar_pedido(request, pedido_id):
    """Aprovar pedido - apenas roles autorizadas"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if not pode_gerenciar_pedido(user, pedido):
            return Response({'error': f'Você não pode aprovar este pedido'}, status=status.HTTP_403_FORBIDDEN)
        
        estado_anterior = pedido.estado
        pedido.estado = EstadoPedido.APROVADO
        pedido.responsavel_atual = 'FINALIZADO'
        
        # Confirmar datas
        if not pedido.data_saida_confirmada:
            pedido.data_saida_confirmada = pedido.data_saida
        if not pedido.data_volta_confirmada:
            pedido.data_volta_confirmada = pedido.data_volta or pedido.data_saida
        
        # Registrar decisão
        if user.role == 'DITE':
            pedido.decisao_dite = 'APROVADO'
            pedido.data_decisao_dite = timezone.now()
            acao = 'APROVADO_DITE'
        elif user.role == 'DIRECAO':
            pedido.decisao_direcao = 'APROVADO'
            pedido.data_decisao_direcao = timezone.now()
            acao = 'APROVADO_DIRECAO'
        elif user.role == 'ADMINISTRACAO':
            pedido.decisao_administracao = 'APROVADO'
            pedido.data_decisao_administracao = timezone.now()
            acao = 'APROVADO_ADMINISTRACAO'
        elif user.role == 'ADMIN':
            pedido.decisao_admin = 'APROVADO'
            pedido.data_decisao_admin = timezone.now()
            acao = 'APROVADO_ADMIN'
        
        pedido.save()
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao=acao,
            de_estado=estado_anterior,
            para_estado=EstadoPedido.APROVADO,
            usuario=user,
            role_usuario=user.role
        )
        
        # Notificar estudante
        criar_notificacao(pedido.estudante, pedido, 'PEDIDO_APROVADO',
            f'Seu pedido #{pedido.id} foi APROVADO!')
        
        # Notificar segurança
        for u in User.objects.filter(role='SEGURANCA'):
            criar_notificacao(u, pedido, 'NOVO_PEDIDO',
                f'Aluno autorizado: {pedido.estudante.get_full_name()}')
        
        return Response({'message': 'Pedido aprovado com sucesso'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== REJEITAR PEDIDO ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rejeitar_pedido(request, pedido_id):
    """Rejeitar pedido - apenas roles autorizadas"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if not pode_gerenciar_pedido(user, pedido):
            return Response({'error': f'Você não pode rejeitar este pedido'}, status=status.HTTP_403_FORBIDDEN)
        
        comentario = request.data.get('comentario', '')
        if not comentario:
            return Response({'error': 'Motivo da rejeição é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        
        estado_anterior = pedido.estado
        pedido.estado = EstadoPedido.REJEITADO
        pedido.responsavel_atual = 'FINALIZADO'
        
        if user.role == 'DITE':
            pedido.decisao_dite = 'REJEITADO'
            pedido.data_decisao_dite = timezone.now()
            acao = 'REJEITADO_DITE'
        elif user.role == 'DIRECAO':
            pedido.decisao_direcao = 'REJEITADO'
            pedido.data_decisao_direcao = timezone.now()
            acao = 'REJEITADO_DIRECAO'
        elif user.role == 'ADMINISTRACAO':
            pedido.decisao_administracao = 'REJEITADO'
            pedido.data_decisao_administracao = timezone.now()
            acao = 'REJEITADO_ADMINISTRACAO'
        elif user.role == 'ADMIN':
            pedido.decisao_admin = 'REJEITADO'
            pedido.data_decisao_admin = timezone.now()
            acao = 'REJEITADO_ADMIN'
        
        pedido.save()
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao=acao,
            de_estado=estado_anterior,
            para_estado=EstadoPedido.REJEITADO,
            usuario=user,
            role_usuario=user.role,
            comentario=comentario
        )
        
        criar_notificacao(pedido.estudante, pedido, 'PEDIDO_REJEITADO',
            f'Seu pedido #{pedido.id} foi REJEITADO. Motivo: {comentario}')
        
        return Response({'message': 'Pedido rejeitado'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== PASSAR/ENCAMINHAR PEDIDO ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def passar_pedido_dite(request, pedido_id):
    """DITE escolhe para quem encaminhar (Direção ou Administração)"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if user.role != 'DITE':
            return Response({'error': 'Apenas DITE pode encaminhar'}, status=status.HTTP_403_FORBIDDEN)
        
        if pedido.estado != EstadoPedido.PENDENTE_DITE:
            return Response({'error': 'Pedido não está pendente para DITE'}, status=status.HTTP_400_BAD_REQUEST)
        
        destino = request.data.get('destino')
        if destino not in ['DIRECAO', 'ADMINISTRACAO']:
            return Response({'error': 'Destino inválido'}, status=status.HTTP_400_BAD_REQUEST)
        
        estado_anterior = pedido.estado
        pedido.estado = EstadoPedido.PENDENTE_DIRECAO
        pedido.responsavel_atual = destino
        pedido.save()
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao='PASSADO_DIRECAO',
            de_estado=estado_anterior,
            para_estado=EstadoPedido.PENDENTE_DIRECAO,
            usuario=user,
            role_usuario=user.role,
            comentario=f'Encaminhado para {dict(User.ROLE_CHOICES).get(destino, destino)}'
        )
        
        # Notificar destino
        for u in User.objects.filter(role=destino):
            criar_notificacao(u, pedido, 'PEDIDO_ENCAMINHADO',
                f'Pedido #{pedido.id} encaminhado para você')
        
        return Response({'message': f'Encaminhado para {destino}', 'responsavel_atual': destino})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def passar_pedido(request, pedido_id):
    """Direção/Administração passa para Admin"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if not pode_passar_pedido(user, pedido):
            return Response({'error': 'Sem permissão para encaminhar'}, status=status.HTTP_403_FORBIDDEN)
        
        estado_anterior = pedido.estado
        pedido.estado = EstadoPedido.PENDENTE_ADMIN
        pedido.responsavel_atual = 'ADMIN'
        pedido.save()
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao='PASSADO_ADMIN',
            de_estado=estado_anterior,
            para_estado=EstadoPedido.PENDENTE_ADMIN,
            usuario=user,
            role_usuario=user.role
        )
        
        for u in User.objects.filter(role='ADMIN'):
            criar_notificacao(u, pedido, 'PEDIDO_ENCAMINHADO',
                f'Pedido #{pedido.id} encaminhado para Admin')
        
        return Response({'message': 'Encaminhado para Admin'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== SEGURANÇA ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_seguranca(request):
    """Dashboard do segurança - saídas do dia"""
    user = request.user
    
    if user.role != 'SEGURANCA':
        return Response({'error': 'Acesso negado'}, status=status.HTTP_403_FORBIDDEN)
    
    hoje = timezone.now().date()
    
    # Pedidos aprovados para hoje ou em andamento
    saidas_hoje = Pedido.objects.filter(
        Q(estado=EstadoPedido.APROVADO, data_saida_confirmada__date=hoje) |
        Q(estado=EstadoPedido.EM_ANDAMENTO) |
        Q(estado=EstadoPedido.FINALIZADO, data_saida_confirmada__date=hoje)
    ).order_by('data_saida_confirmada')
    
    saidas = []
    for pedido in saidas_hoje:
        atrasado = pedido.atrasado
        if pedido.estado == EstadoPedido.EM_ANDAMENTO and pedido.data_volta_confirmada:
            if timezone.now() > pedido.data_volta_confirmada:
                atrasado = True
        
        saidas.append({
            'id': pedido.id,
            'estudante_nome': pedido.estudante.get_full_name(),
            'estudante_curso': pedido.estudante.curso or '',
            'estudante_classe': pedido.estudante.classe or '',
            'tipo': pedido.get_tipo_display(),
            'data_saida': pedido.data_saida_confirmada.strftime('%H:%M') if pedido.data_saida_confirmada else '',
            'data_volta': pedido.data_volta_confirmada.strftime('%H:%M') if pedido.data_volta_confirmada else '',
            'estado': pedido.estado,
            'hora_saida_real': pedido.hora_saida_real.strftime('%H:%M') if pedido.hora_saida_real else None,
            'hora_retorno_real': pedido.hora_retorno_real.strftime('%H:%M') if pedido.hora_retorno_real else None,
            'atrasado': atrasado,
            'tempo_atraso': pedido.tempo_atraso,
        })
    
    em_andamento = saidas_hoje.filter(estado=EstadoPedido.EM_ANDAMENTO).count()
    finalizados = saidas_hoje.filter(estado=EstadoPedido.FINALIZADO).count()
    
    return Response({
        'saidas_hoje': saidas,
        'total_saidas': saidas_hoje.count(),
        'em_andamento': em_andamento,
        'finalizados': finalizados,
        'atrasados': sum(1 for s in saidas if s['atrasado']),
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_saida(request, pedido_id):
    """Segurança marca saída do estudante"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if user.role != 'SEGURANCA':
            return Response({'error': 'Apenas segurança'}, status=status.HTTP_403_FORBIDDEN)
        
        if pedido.estado != EstadoPedido.APROVADO:
            return Response({'error': 'Pedido não aprovado'}, status=status.HTTP_400_BAD_REQUEST)
        
        pedido.hora_saida_real = timezone.now()
        pedido.estado = EstadoPedido.EM_ANDAMENTO
        pedido.save()
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao='SAIDA_REALIZADA',
            de_estado=EstadoPedido.APROVADO,
            para_estado=EstadoPedido.EM_ANDAMENTO,
            usuario=user,
            role_usuario='SEGURANCA',
            comentario=f'Saída: {timezone.now().strftime("%H:%M")}'
        )
        
        return Response({'message': 'Saída registrada', 'hora': pedido.hora_saida_real.strftime('%H:%M')})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_retorno(request, pedido_id):
    """Segurança marca retorno do estudante"""
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id)
        user = request.user
        
        if user.role != 'SEGURANCA':
            return Response({'error': 'Apenas segurança'}, status=status.HTTP_403_FORBIDDEN)
        
        if pedido.estado != EstadoPedido.EM_ANDAMENTO:
            return Response({'error': 'Estudante não está em saída'}, status=status.HTTP_400_BAD_REQUEST)
        
        hora_ajustada = request.data.get('hora_retorno')
        observacao = request.data.get('observacao', '')
        
        if hora_ajustada:
            pedido.hora_retorno_real = hora_ajustada
        else:
            pedido.hora_retorno_real = timezone.now()
        
        pedido.estado = EstadoPedido.FINALIZADO
        pedido.observacao_seguranca = observacao
        
        # Verificar atraso
        if pedido.data_volta_confirmada and pedido.hora_retorno_real > pedido.data_volta_confirmada:
            pedido.atrasado = True
            diferenca = pedido.hora_retorno_real - pedido.data_volta_confirmada
            pedido.tempo_atraso = int(diferenca.total_seconds() / 60)
        
        pedido.save()
        
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao='RETORNO_REALIZADO',
            de_estado=EstadoPedido.EM_ANDAMENTO,
            para_estado=EstadoPedido.FINALIZADO,
            usuario=user,
            role_usuario='SEGURANCA',
            comentario=f'Retorno: {pedido.hora_retorno_real.strftime("%H:%M")}' + 
                      (f' | ATRASO: {pedido.tempo_atraso}min' if pedido.atrasado else '')
        )
        
        return Response({
            'message': 'Retorno registrado',
            'atrasado': pedido.atrasado,
            'tempo_atraso': pedido.tempo_atraso
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== RELATÓRIOS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relatorios(request):
    """Relatórios para DITE, Direção, Administração, Admin"""
    user = request.user
    
    if user.role not in ['ADMIN', 'DITE', 'DIRECAO', 'ADMINISTRACAO']:
        return Response({'error': 'Acesso negado'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        periodo = request.GET.get('periodo', 'mes')
        mes = int(request.GET.get('mes', timezone.now().month))
        ano = int(request.GET.get('ano', timezone.now().year))
        
        if periodo == 'semana':
            inicio = timezone.now() - timedelta(days=7)
            pedidos = Pedido.objects.filter(created_at__gte=inicio)
        elif periodo == 'mes':
            pedidos = Pedido.objects.filter(created_at__month=mes, created_at__year=ano)
        else:
            pedidos = Pedido.objects.filter(created_at__year=ano)
        
        total = pedidos.count()
        aprovados = pedidos.filter(estado=EstadoPedido.APROVADO).count()
        rejeitados = pedidos.filter(estado=EstadoPedido.REJEITADO).count()
        pendentes = pedidos.filter(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.PENDENTE_DIRECAO, EstadoPedido.PENDENTE_ADMIN]).count()
        
        # Por estado
        pedidos_por_estado = {}
        for estado in EstadoPedido.values:
            pedidos_por_estado[estado] = pedidos.filter(estado=estado).count()
        
        # Por tipo
        pedidos_por_tipo = {}
        for tipo in TipoPedido.values:
            pedidos_por_tipo[tipo] = pedidos.filter(tipo=tipo).count()
        
        # Por curso
        pedidos_por_curso = {}
        cursos = pedidos.exclude(estudante__curso__isnull=True).exclude(estudante__curso='').values_list('estudante__curso', flat=True).distinct()
        for curso in cursos:
            pedidos_por_curso[curso] = pedidos.filter(estudante__curso=curso).count()
        
        taxa_aprovacao = round((aprovados / total * 100), 1) if total > 0 else 0
        
        return Response({
            'total_pedidos': total,
            'aprovados': aprovados,
            'rejeitados': rejeitados,
            'pendentes': pendentes,
            'taxa_aprovacao': taxa_aprovacao,
            'pedidos_por_estado': pedidos_por_estado,
            'pedidos_por_tipo': pedidos_por_tipo,
            'pedidos_por_curso': pedidos_por_curso,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relatorio_seguranca(request):
    """Relatório de segurança - entradas e saídas"""
    user = request.user
    
    if user.role not in ['ADMIN', 'DITE', 'DIRECAO', 'ADMINISTRACAO']:
        return Response({'error': 'Acesso negado'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        data = request.GET.get('data', timezone.now().date())
        
        pedidos = Pedido.objects.filter(
            data_saida_confirmada__date=data
        ).exclude(estado__in=[EstadoPedido.PENDENTE_DITE, EstadoPedido.REJEITADO])
        
        saidas = []
        total_sairam = 0
        total_voltaram = 0
        
        for p in pedidos:
            if p.hora_saida_real:
                total_sairam += 1
            if p.hora_retorno_real:
                total_voltaram += 1
            
            saidas.append({
                'id': p.id,
                'estudante': p.estudante.get_full_name(),
                'curso': p.estudante.curso or '',
                'classe': p.estudante.classe or '',
                'tipo': p.get_tipo_display(),
                'data_saida_prevista': p.data_saida_confirmada.strftime('%H:%M') if p.data_saida_confirmada else '',
                'data_volta_prevista': p.data_volta_confirmada.strftime('%H:%M') if p.data_volta_confirmada else '',
                'hora_saida_real': p.hora_saida_real.strftime('%H:%M') if p.hora_saida_real else '---',
                'hora_retorno_real': p.hora_retorno_real.strftime('%H:%M') if p.hora_retorno_real else '---',
                'estado': p.estado,
                'atrasado': p.atrasado,
                'tempo_atraso': p.tempo_atraso,
            })
        
        return Response({
            'data': data,
            'total': len(saidas),
            'total_sairam': total_sairam,
            'total_voltaram': total_voltaram,
            'atrasados': sum(1 for s in saidas if s['atrasado']),
            'saidas': saidas,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== NOTIFICAÇÕES ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notificacoes(request):
    """Listar notificações do usuário"""
    user = request.user
    
    try:
        notificacoes = Notificacao.objects.filter(usuario=user).order_by('-data')
        nao_lidas = notificacoes.filter(lida=False).count()
        
        return Response({
            'notificacoes': [{
                'id': n.id,
                'tipo': n.tipo,
                'tipo_display': n.get_tipo_display(),
                'mensagem': n.mensagem,
                'lida': n.lida,
                'data': n.data.strftime('%d/%m/%Y %H:%M'),
                'pedido_id': n.pedido.id if n.pedido else None,
            } for n in notificacoes[:50]],
            'total': notificacoes.count(),
            'nao_lidas': nao_lidas,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_notificacao_lida(request, notificacao_id):
    """Marcar notificação como lida"""
    try:
        notificacao = get_object_or_404(Notificacao, id=notificacao_id, usuario=request.user)
        notificacao.lida = True
        notificacao.save()
        return Response({'message': 'Notificação marcada como lida'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_todas_lidas(request):
    """Marcar todas como lidas"""
    try:
        Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
        return Response({'message': 'Todas marcadas como lidas'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== SAÍDA COLETIVA ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def criar_saida_coletiva(request):
    """DITE/Direção/Administração cria saída coletiva"""
    user = request.user
    
    if user.role not in ['DITE', 'DIRECAO', 'ADMINISTRACAO', 'ADMIN']:
        return Response({'error': 'Sem permissão'}, status=403)
    
    try:
        titulo = request.data.get('titulo')
        descricao = request.data.get('descricao')
        data_saida = request.data.get('data_saida')
        data_volta = request.data.get('data_volta')
        prazo_horas = int(request.data.get('prazo_horas', 24))
        
        if not all([titulo, data_saida, data_volta]):
            return Response({'error': 'Título, data saída e volta são obrigatórios'}, status=400)
        
        data_saida_dt = datetime.strptime(data_saida, '%Y-%m-%dT%H:%M')
        data_volta_dt = datetime.strptime(data_volta, '%Y-%m-%dT%H:%M')
        prazo = timezone.now() + timedelta(hours=prazo_horas)
        
        coletiva = SaidaColetiva.objects.create(
            criador=user,
            titulo=titulo,
            descricao=descricao,
            data_saida=data_saida_dt,
            data_volta=data_volta_dt,
            prazo_resposta=prazo,
        )
        
        # Convidar TODOS os estudantes ativos
        estudantes = User.objects.filter(role='ESTUDANTE', is_active=True)
        for est in estudantes:
            ConviteColetiva.objects.create(
                saida_coletiva=coletiva,
                estudante=est,
            )
            criar_notificacao(est, None, 'COLETIVA_NOVA',
                f'Nova saída coletiva: {titulo}. Responda até {prazo.strftime("%d/%m %H:%M")}')
        
        return Response({
            'message': 'Saída coletiva criada',
            'id': coletiva.id,
            'convidados': estudantes.count()
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_coletivas_estudante(request):
    """Estudante vê suas saídas coletivas pendentes"""
    user = request.user
    
    if user.role != 'ESTUDANTE':
        return Response({'error': 'Apenas estudantes'}, status=403)
    
    try:
        convites = ConviteColetiva.objects.filter(estudante=user).select_related('saida_coletiva').order_by('-created_at')
        
        # Verificar expiração
        for c in convites:
            c.verificar_expiracao()
        
        dados = []
        for c in convites:
            dados.append({
                'id': c.id,
                'coletiva_id': c.saida_coletiva.id,
                'titulo': c.saida_coletiva.titulo,
                'descricao': c.saida_coletiva.descricao,
                'data_saida': c.saida_coletiva.data_saida.strftime('%d/%m/%Y %H:%M'),
                'data_volta': c.saida_coletiva.data_volta.strftime('%d/%m/%Y %H:%M'),
                'prazo': c.saida_coletiva.prazo_resposta.strftime('%d/%m/%Y %H:%M'),
                'estado': c.estado,
                'criador': c.saida_coletiva.criador.get_full_name(),
            })
        
        return Response({'coletivas': dados, 'total': len(dados)})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def responder_coletiva(request, convite_id):
    """Estudante aceita ou recusa saída coletiva"""
    user = request.user
    
    if user.role != 'ESTUDANTE':
        return Response({'error': 'Apenas estudantes'}, status=403)
    
    try:
        convite = get_object_or_404(ConviteColetiva, id=convite_id, estudante=user)
        
        if convite.estado != 'PENDENTE':
            return Response({'error': 'Convite já respondido ou expirado'}, status=400)
        
        # Verificar expiração
        if convite.verificar_expiracao():
            return Response({'error': 'Prazo expirado. Automaticamente recusado.'}, status=400)
        
        resposta = request.data.get('resposta')  # 'ACEITE' ou 'RECUSADO'
        if resposta not in ['ACEITE', 'RECUSADO']:
            return Response({'error': 'Resposta inválida'}, status=400)
        
        convite.estado = resposta
        convite.data_resposta = timezone.now()
        convite.save()
        
        # Se aceitou, criar pedido automaticamente
        if resposta == 'ACEITE':
            pedido = Pedido.objects.create(
                estudante=user,
                tipo='escola',
                motivo=f'Saída Coletiva: {convite.saida_coletiva.titulo}',
                data_saida=convite.saida_coletiva.data_saida,
                data_volta=convite.saida_coletiva.data_volta,
                estado=EstadoPedido.APROVADO,
                responsavel_atual='FINALIZADO',
                data_saida_confirmada=convite.saida_coletiva.data_saida,
                data_volta_confirmada=convite.saida_coletiva.data_volta,
            )
            HistoricoPedido.objects.create(
                pedido=pedido,
                acao='CRIADO',
                para_estado=EstadoPedido.APROVADO,
                usuario=user,
                role_usuario=user.role,
                comentario='Aprovado automaticamente - Saída Coletiva'
            )
        
        # Notificar criador
        criar_notificacao(
            convite.saida_coletiva.criador,
            None,
            'COLETIVA_RESPOSTA',
            f'{user.get_full_name()} {dict(ConviteColetiva.ESTADO_CHOICES).get(resposta)} a saída: {convite.saida_coletiva.titulo}'
        )
        
        return Response({'message': f'Convite {dict(ConviteColetiva.ESTADO_CHOICES).get(resposta).lower()} com sucesso'})
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
