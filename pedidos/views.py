from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Pedido, HistoricoPedido, EstadoPedido

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_pedidos(request):
    """Listar pedidos baseado na role"""
    user = request.user
    
    # Filtrar por estado (query param)
    estado_filtro = request.GET.get('estado', None)
    
    # Estudante vê apenas seus pedidos
    if user.role == 'ESTUDANTE':
        pedidos = Pedido.objects.filter(estudante=user)
    else:
        pedidos = Pedido.objects.all()
    
    # Aplicar filtro de estado
    if estado_filtro:
        pedidos = pedidos.filter(estado=estado_filtro)
    
    # Serializar
    dados = []
    for pedido in pedidos.order_by('-created_at'):
        dados.append({
            'id': pedido.id,
            'tipo': pedido.tipo,
            'motivo': pedido.motivo,
            'data_saida': pedido.data_saida.strftime('%d/%m/%Y'),
            'hora_saida': pedido.hora_saida.strftime('%H:%M'),
            'estado': pedido.estado,
            'responsavel_atual': pedido.responsavel_atual,
            'estudante_nome': pedido.estudante.get_full_name() or pedido.estudante.username,
            'estudante_curso': pedido.estudante.curso,
            'estudante_classe': pedido.estudante.classe,
            'created_at': pedido.created_at.strftime('%d/%m/%Y %H:%M'),
        })
    
    return Response(dados)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def criar_pedido(request):
    """Criar novo pedido (apenas estudantes)"""
    user = request.user
    
    if user.role != 'ESTUDANTE':
        return Response({'error': 'Apenas estudantes podem criar pedidos'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    try:
        pedido = Pedido.objects.create(
            estudante=user,
            tipo=request.data.get('tipo'),
            motivo=request.data.get('motivo'),
            data_saida=request.data.get('data_saida'),
            hora_saida=request.data.get('hora_saida'),
        )
        
        # Registrar histórico
        HistoricoPedido.objects.create(
            pedido=pedido,
            acao='Pedido criado',
            de_responsavel='ESTUDANTE',
            para_responsavel='DITE',
            usuario=user
        )
        
        return Response({
            'id': pedido.id,
            'message': 'Pedido criado com sucesso'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalhe_pedido(request, pedido_id):
    """Ver detalhes de um pedido"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Verificar permissão
    user = request.user
    if user.role == 'ESTUDANTE' and pedido.estudante != user:
        return Response({'error': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
    
    # Histórico
    historico = []
    for h in pedido.historico.all():
        historico.append({
            'acao': h.acao,
            'de_responsavel': h.de_responsavel,
            'para_responsavel': h.para_responsavel,
            'usuario': h.usuario.get_full_name() if h.usuario else 'Sistema',
            'data': h.data.strftime('%d/%m/%Y %H:%M'),
            'comentario': h.comentario,
        })
    
    # Determinar ações disponíveis
    acoes = []
    pode_decidir = False
    pode_passar = False
    
    if user.role == 'ADMIN':
        pode_decidir = True
    elif user.role == 'DIRECAO' and pedido.responsavel_atual in ['DITE', 'DIRECAO']:
        pode_decidir = True
        if pedido.responsavel_atual == 'DIRECAO':
            pode_passar = True
    elif user.role == 'DITE' and pedido.responsavel_atual == 'DITE':
        pode_decidir = True
        pode_passar = True
    
    if pode_decidir:
        acoes.append('aprovar')
        acoes.append('rejeitar')
    if pode_passar:
        acoes.append('passar')
    
    return Response({
        'id': pedido.id,
        'tipo': pedido.tipo,
        'motivo': pedido.motivo,
        'data_saida': pedido.data_saida.strftime('%d/%m/%Y'),
        'hora_saida': pedido.hora_saida.strftime('%H:%M'),
        'estado': pedido.estado,
        'responsavel_atual': pedido.responsavel_atual,
        'estudante_nome': pedido.estudante.get_full_name(),
        'estudante_curso': pedido.estudante.curso,
        'estudante_classe': pedido.estudante.classe,
        'created_at': pedido.created_at.strftime('%d/%m/%Y %H:%M'),
        'historico': historico,
        'acoes_disponiveis': acoes,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def aprovar_pedido(request, pedido_id):
    """Aprovar pedido"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    user = request.user
    
    # Verificar permissão
    pode = False
    if user.role == 'ADMIN':
        pode = True
    elif user.role == 'DIRECAO' and pedido.responsavel_atual in ['DITE', 'DIRECAO']:
        pode = True
    elif user.role == 'DITE' and pedido.responsavel_atual == 'DITE':
        pode = True
    
    if not pode:
        return Response({'error': 'Sem permissão para aprovar'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    # Registrar histórico
    HistoricoPedido.objects.create(
        pedido=pedido,
        acao=f'{user.role} aprovou',
        de_responsavel=pedido.responsavel_atual,
        para_responsavel='FINAL',
        usuario=user
    )
    
    # Atualizar pedido
    pedido.estado = EstadoPedido.APROVADO
    pedido.save()
    
    return Response({'message': 'Pedido aprovado com sucesso'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rejeitar_pedido(request, pedido_id):
    """Rejeitar pedido"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    user = request.user
    
    # Mesma verificação de aprovar
    pode = False
    if user.role == 'ADMIN':
        pode = True
    elif user.role == 'DIRECAO' and pedido.responsavel_atual in ['DITE', 'DIRECAO']:
        pode = True
    elif user.role == 'DITE' and pedido.responsavel_atual == 'DITE':
        pode = True
    
    if not pode:
        return Response({'error': 'Sem permissão para rejeitar'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    HistoricoPedido.objects.create(
        pedido=pedido,
        acao=f'{user.role} rejeitou',
        de_responsavel=pedido.responsavel_atual,
        para_responsavel='FINAL',
        usuario=user
    )
    
    pedido.estado = EstadoPedido.REJEITADO
    pedido.save()
    
    return Response({'message': 'Pedido rejeitado'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def passar_responsabilidade(request, pedido_id):
    """Passar responsabilidade para próximo nível"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    user = request.user
    
    # Verificar se pode passar
    pode_passar = False
    if user.role == 'DITE' and pedido.responsavel_atual == 'DITE':
        pode_passar = True
    elif user.role == 'DIRECAO' and pedido.responsavel_atual == 'DIRECAO':
        pode_passar = True
    elif user.role == 'ADMIN' and pedido.responsavel_atual in ['DITE', 'DIRECAO']:
        pode_passar = True
    
    if not pode_passar:
        return Response({'error': 'Sem permissão para transferir'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    # Definir próximo responsável
    proximo = {
        'DITE': 'DIRECAO',
        'DIRECAO': 'ADMIN',
    }
    
    if pedido.responsavel_atual not in proximo:
        return Response({'error': 'Não é possível transferir'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    novo_responsavel = proximo[pedido.responsavel_atual]
    novo_estado = {
        'DIRECAO': EstadoPedido.PENDENTE_DIRECAO,
        'ADMIN': EstadoPedido.PENDENTE_ADMIN,
    }
    
    # Registrar histórico
    HistoricoPedido.objects.create(
        pedido=pedido,
        acao=f'Transferido de {pedido.responsavel_atual} para {novo_responsavel}',
        de_responsavel=pedido.responsavel_atual,
        para_responsavel=novo_responsavel,
        usuario=user
    )
    
    # Atualizar pedido
    pedido.responsavel_atual = novo_responsavel
    pedido.estado = novo_estado[novo_responsavel]
    pedido.save()
    
    return Response({'message': f'Responsabilidade transferida para {novo_responsavel}'})