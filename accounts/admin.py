# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.conf import settings
import psutil
import os
from .models import User, SystemConfig, SystemLog, ServerMonitor
from pedidos.models import Pedido, HistoricoPedido, Relatorio, Notificacao

# ==================== INLINE MODELS ====================

class SystemLogInline(admin.TabularInline):
    model = SystemLog
    extra = 0
    readonly_fields = ['created_at']
    can_delete = True
    fields = ['action', 'level', 'ip_address', 'created_at']

# ==================== SYSTEM CONFIG ADMIN ====================

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'login_enabled', 'registration_enabled', 'maintenance_mode', 'updated_at']
    list_editable = ['login_enabled', 'registration_enabled', 'maintenance_mode']
    
    def has_add_permission(self, request):
        return not SystemConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        SystemLog.objects.create(
            user=request.user,
            action='Configurações do sistema atualizadas',
            level='INFO',
            ip_address=request.META.get('REMOTE_ADDR')
        )

# ==================== SYSTEM LOG ADMIN ====================

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'level_badge', 'user', 'action', 'ip_address', 'created_at']
    list_filter = ['level', 'created_at']
    search_fields = ['action', 'details', 'user__email']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    actions = ['delete_old_logs', 'export_logs']
    
    def level_badge(self, obj):
        cores = {
            'INFO': '#4CAF50',
            'WARNING': '#FF9800',
            'ERROR': '#F44336',
            'CRITICAL': '#9C27B0'
        }
        cor = cores.get(obj.level, '#999')
        texto = obj.get_level_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 10px; font-size: 11px;">{}</span>',
            cor,
            texto
        )
    level_badge.short_description = 'Nível'
    
    @admin.action(description='🗑️ Deletar logs antigos (mais de 30 dias)')
    def delete_old_logs(self, request, queryset):
        from datetime import timedelta
        old_date = timezone.now() - timedelta(days=30)
        deleted = SystemLog.objects.filter(created_at__lt=old_date).delete()
        messages.success(request, f'Logs antigos deletados: {deleted[0]} registros')
    
    @admin.action(description='📊 Exportar logs selecionados')
    def export_logs(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Data', 'Usuário', 'Ação', 'Nível', 'IP', 'Detalhes'])
        
        for log in queryset:
            writer.writerow([
                log.created_at,
                log.user.email if log.user else 'Sistema',
                log.action,
                log.get_level_display(),
                log.ip_address,
                log.details
            ])
        
        return response

# ==================== SERVER MONITOR ADMIN ====================

@admin.register(ServerMonitor)
class ServerMonitorAdmin(admin.ModelAdmin):
    list_display = ['id', 'cpu_usage_bar', 'memory_usage_bar', 'disk_usage_bar', 
                   'active_users', 'error_count', 'uptime', 'checked_at']
    readonly_fields = ['checked_at']
    list_filter = ['checked_at']
    date_hierarchy = 'checked_at'
    
    actions = ['monitor_now', 'clear_old_monitoring']
    
    def cpu_usage_bar(self, obj):
        color = '#4CAF50' if obj.cpu_usage < 70 else '#FF9800' if obj.cpu_usage < 90 else '#F44336'
        return format_html(
            '<div style="width:100px; height:20px; background:#eee; border-radius:10px; overflow:hidden;">'
            '<div style="width:{}%; height:100%; background:{}; text-align:center; color:white; '
            'font-size:11px; line-height:20px;">{}%</div></div>',
            str(obj.cpu_usage),
            str(color),
            str(obj.cpu_usage)
        )
    cpu_usage_bar.short_description = 'CPU'
    
    def memory_usage_bar(self, obj):
        color = '#4CAF50' if obj.memory_usage < 70 else '#FF9800' if obj.memory_usage < 90 else '#F44336'
        return format_html(
            '<div style="width:100px; height:20px; background:#eee; border-radius:10px; overflow:hidden;">'
            '<div style="width:{}%; height:100%; background:{}; text-align:center; color:white; '
            'font-size:11px; line-height:20px;">{}%</div></div>',
            str(obj.memory_usage),
            str(color),
            str(obj.memory_usage)
        )
    memory_usage_bar.short_description = 'Memória'
    
    def disk_usage_bar(self, obj):
        color = '#4CAF50' if obj.disk_usage < 70 else '#FF9800' if obj.disk_usage < 90 else '#F44336'
        return format_html(
            '<div style="width:100px; height:20px; background:#eee; border-radius:10px; overflow:hidden;">'
            '<div style="width:{}%; height:100%; background:{}; text-align:center; color:white; '
            'font-size:11px; line-height:20px;">{}%</div></div>',
            str(obj.disk_usage),
            str(color),
            str(obj.disk_usage)
        )
    disk_usage_bar.short_description = 'Disco'
    
    @admin.action(description='🔍 Monitorar agora')
    def monitor_now(self, request, queryset):
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            ServerMonitor.objects.create(
                cpu_usage=cpu,
                memory_usage=memory,
                disk_usage=disk,
                active_users=User.objects.filter(is_active=True).count(),
                error_count=SystemLog.objects.filter(level='ERROR').count(),
                uptime="0h"
            )
            messages.success(request, 'Monitoramento realizado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao monitorar: {str(e)}')
    
    @admin.action(description='🗑️ Limpar monitoramento antigo')
    def clear_old_monitoring(self, request, queryset):
        from datetime import timedelta
        old = timezone.now() - timedelta(days=7)
        ServerMonitor.objects.filter(checked_at__lt=old).delete()
        messages.success(request, 'Monitoramento antigo limpo')

# ==================== CUSTOM USER ADMIN ====================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['id', 'email', 'username', 'get_full_name_user', 'role_badge', 
                   'two_factor_status', 'account_status', 'login_permission', 'last_login', 'created_at']
    list_filter = ['role', 'is_active', 'two_factor_enabled', 'can_login', 'is_staff', 'is_superuser']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'curso', 'phone']
    ordering = ['-created_at']
    
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_login_ip']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('email', 'username', 'password')
        }),
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'phone', 'foto')
        }),
        ('Curso/Classe', {
            'fields': ('curso', 'classe', 'ano_ingresso')
        }),
        ('Papel e Permissões', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_monitor', 
                      'groups', 'user_permissions')
        }),
        ('Controle de Acesso', {
            'fields': ('can_login', 'can_register')
        }),
        ('Segurança e 2FA', {
            'fields': ('two_factor_enabled', 'two_factor_secret', 'two_factor_code', 
                      'two_factor_expires', 'login_attempts', 'locked_until', 'email_verified')
        }),
        ('Datas', {
            'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role', 
                      'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    actions = [
        'ativar_2fa', 'desativar_2fa', 'bloquear_usuarios', 'desbloquear_usuarios',
        'ativar_usuarios', 'desativar_usuarios', 'permitir_login', 'bloquear_login',
        'reset_tentativas_login', 'promover_admin', 'rebaixar_estudante',
        'enviar_email_credenciais', 'duplicar_usuario'
    ]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('system-control/', 
                 self.admin_site.admin_view(self.system_control_view), 
                 name='system-control'),
            path('monitor/', 
                 self.admin_site.admin_view(self.monitor_view), 
                 name='monitor-dashboard'),
            path('<int:user_id>/toggle-role/', 
                 self.admin_site.admin_view(self.toggle_role_view), 
                 name='toggle-role'),
        ]
        return custom_urls + urls
    
    def get_full_name_user(self, obj):
        return obj.get_full_name() or obj.username
    get_full_name_user.short_description = 'Nome'
    get_full_name_user.admin_order_field = 'first_name'
    
    def role_badge(self, obj):
        cores = {
            'ADMIN': ('#9C27B0', '👑 Admin'),
            'DIRECAO': ('#FF9800', '👨‍💼 Direção'),
            'DITE': ('#4CAF50', '💻 DITE'),
            'ESTUDANTE': ('#2196F3', '🎓 Estudante'),
            'ADMINISTRACAO': ('#E91E63', '🏛️ Administração'),
            'SEGURANCA': ('#FF5722', '🛡️ Segurança'),
        }
        cor, texto = cores.get(obj.role, ('#999', obj.role))
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 15px; font-size: 12px; font-weight: 600;">{}</span>',
            cor,
            texto
        )
    role_badge.short_description = 'Papel'
    
    # ==================== CORRIGIDO: usando mark_safe em vez de format_html ====================
    
    def two_factor_status(self, obj):
        if obj.role == 'ADMIN' and not obj.two_factor_enabled:
            return mark_safe('<span style="color: #9C27B0; font-weight: 600;">👑 Isento</span>')
        if obj.two_factor_enabled:
            return mark_safe('<span style="color: #4CAF50; font-weight: 600;">✅ Ativo</span>')
        return mark_safe('<span style="color: #F44336; font-weight: 600;">❌ Inativo</span>')
    two_factor_status.short_description = '2FA'

    def account_status(self, obj):
        if not obj.is_active:
            return mark_safe(
                '<span style="background-color: #F44336; color: white; padding: 3px 10px; '
                'border-radius: 10px; font-size: 11px;">🔒 Desativada</span>'
            )
        if obj.is_locked():
            return mark_safe(
                '<span style="background-color: #FF9800; color: white; padding: 3px 10px; '
                'border-radius: 10px; font-size: 11px;">⏳ Bloqueada</span>'
            )
        return mark_safe(
            '<span style="background-color: #4CAF50; color: white; padding: 3px 10px; '
            'border-radius: 10px; font-size: 11px;">✅ Ativa</span>'
        )
    account_status.short_description = 'Status'

    def login_permission(self, obj):
        if obj.can_login:
            return mark_safe('<span style="color: #4CAF50;">✅ Permitido</span>')
        return mark_safe('<span style="color: #F44336;">❌ Bloqueado</span>')
    login_permission.short_description = 'Login'
    
    # ==================== FIM DA CORREÇÃO ====================
    
    def system_control_view(self, request):
        """View para controle do sistema"""
        config = SystemConfig.objects.first()
        if not config:
            config = SystemConfig.objects.create()
        
        context = {
            'title': 'Controle do Sistema',
            'config': config,
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'total_pedidos': Pedido.objects.count(),
            'today_pedidos': Pedido.objects.filter(created_at__date=timezone.now().date()).count(),
            'error_logs': SystemLog.objects.filter(level='ERROR').count(),
            'cpu_usage': psutil.cpu_percent() if hasattr(psutil, 'cpu_percent') else 0,
            'memory_usage': psutil.virtual_memory().percent if hasattr(psutil, 'virtual_memory') else 0,
        }
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'toggle_login':
                config.login_enabled = not config.login_enabled
                config.save()
                messages.success(request, f'Login {"ativado" if config.login_enabled else "desativado"}')
            
            elif action == 'toggle_register':
                config.registration_enabled = not config.registration_enabled
                config.save()
                messages.success(request, f'Registro {"ativado" if config.registration_enabled else "desativado"}')
            
            elif action == 'toggle_maintenance':
                config.maintenance_mode = not config.maintenance_mode
                config.save()
                messages.warning(request, f'Modo manutenção {"ativado" if config.maintenance_mode else "desativado"}')
            
            elif action == 'block_all_non_admin':
                User.objects.exclude(role='ADMIN').update(can_login=False)
                messages.warning(request, 'Login bloqueado para todos exceto admins')
            
            elif action == 'allow_all':
                User.objects.all().update(can_login=True)
                messages.success(request, 'Login liberado para todos')
            
            return redirect('admin:system-control')
        
        return render(request, 'admin/system_control.html', context)
    
    def monitor_view(self, request):
        """Dashboard de monitoramento"""
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        except:
            cpu = memory = disk = 0
        
        ServerMonitor.objects.create(
            cpu_usage=cpu,
            memory_usage=memory,
            disk_usage=disk,
            active_users=User.objects.filter(is_active=True).count(),
            total_requests=0,
            error_count=SystemLog.objects.filter(level='ERROR').count(),
        )
        
        context = {
            'title': 'Monitor do Servidor',
            'cpu': cpu,
            'memory': memory,
            'disk': disk,
            'active_users': User.objects.filter(is_active=True).count(),
            'total_pedidos': Pedido.objects.count(),
            'monitors': ServerMonitor.objects.all()[:50],
        }
        
        return render(request, 'admin/monitor.html', context)
    
    def toggle_role_view(self, request, user_id):
        """Alternar papel do usuário"""
        user = get_object_or_404(User, pk=user_id)
        
        if request.method == 'POST':
            new_role = request.POST.get('role')
            if new_role in dict(User.ROLE_CHOICES):
                user.role = new_role
                if new_role == 'ADMIN':
                    user.two_factor_enabled = False
                    user.is_staff = True
                user.save()
                
                SystemLog.objects.create(
                    user=request.user,
                    action=f'Papel alterado para {user.get_role_display()}',
                    level='INFO',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details=f'Usuário: {user.email}'
                )
                messages.success(request, f'Papel de {user.email} alterado para {user.get_role_display()}')
        
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))
    
    # ==================== AÇÕES EM MASSA ====================
    
    @admin.action(description='✅ Ativar 2FA dos selecionados')
    def ativar_2fa(self, request, queryset):
        count = 0
        for user in queryset:
            if user.role != 'ADMIN' and not user.two_factor_enabled:
                user.two_factor_enabled = True
                user.save()
                count += 1
        messages.success(request, f'2FA ativado para {count} usuários')
    
    @admin.action(description='❌ Desativar 2FA dos selecionados')
    def desativar_2fa(self, request, queryset):
        count = 0
        for user in queryset:
            if user.role != 'ADMIN' and user.two_factor_enabled:
                user.two_factor_enabled = False
                user.save()
                count += 1
        messages.success(request, f'2FA desativado para {count} usuários')
    
    @admin.action(description='🔒 Bloquear selecionados (24h)')
    def bloquear_usuarios(self, request, queryset):
        count = 0
        for user in queryset:
            if user != request.user:
                user.locked_until = timezone.now() + timezone.timedelta(hours=24)
                user.can_login = False
                user.save()
                count += 1
        messages.warning(request, f'{count} usuários bloqueados')
    
    @admin.action(description='🔓 Desbloquear selecionados')
    def desbloquear_usuarios(self, request, queryset):
        queryset.update(locked_until=None, login_attempts=0, can_login=True)
        messages.success(request, f'{queryset.count()} usuários desbloqueados')
    
    @admin.action(description='✅ Ativar contas')
    def ativar_usuarios(self, request, queryset):
        queryset.update(is_active=True, can_login=True)
        messages.success(request, f'{queryset.count()} contas ativadas')
    
    @admin.action(description='❌ Desativar contas')
    def desativar_usuarios(self, request, queryset):
        if request.user in queryset:
            queryset = queryset.exclude(id=request.user.id)
        queryset.update(is_active=False, can_login=False)
        messages.warning(request, f'{queryset.count()} contas desativadas')
    
    @admin.action(description='🔓 Permitir login')
    def permitir_login(self, request, queryset):
        queryset.update(can_login=True, locked_until=None, login_attempts=0)
        messages.success(request, f'Login liberado para {queryset.count()} usuários')
    
    @admin.action(description='🔒 Bloquear login')
    def bloquear_login(self, request, queryset):
        if request.user in queryset:
            queryset = queryset.exclude(id=request.user.id)
        queryset.update(can_login=False)
        messages.warning(request, f'Login bloqueado para {queryset.count()} usuários')
    
    @admin.action(description='🔄 Resetar tentativas de login')
    def reset_tentativas_login(self, request, queryset):
        queryset.update(login_attempts=0, locked_until=None)
        messages.success(request, f'Tentativas resetadas para {queryset.count()} usuários')
    
    @admin.action(description='👑 Promover para Admin')
    def promover_admin(self, request, queryset):
        queryset.update(role='ADMIN', two_factor_enabled=False, is_staff=True, 
                       can_login=True, can_register=True)
        messages.success(request, f'{queryset.count()} usuários promovidos a Admin')
    
    @admin.action(description='🎓 Rebaixar para Estudante')
    def rebaixar_estudante(self, request, queryset):
        if request.user in queryset:
            queryset = queryset.exclude(id=request.user.id)
        queryset.update(role='ESTUDANTE', two_factor_enabled=True, is_staff=False, 
                       is_superuser=False)
        messages.info(request, f'{queryset.count()} usuários rebaixados a Estudante')
    
    @admin.action(description='📧 Enviar credenciais por email')
    def enviar_email_credenciais(self, request, queryset):
        count = 0
        for user in queryset:
            try:
                temp_password = User.objects.make_random_password()
                user.set_password(temp_password)
                user.save()
                
                send_mail(
                    'Suas Credenciais - Sistema de Pedidos',
                    f'Email: {user.email}\nSenha temporária: {temp_password}\n\nAltere sua senha após o login.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                )
                count += 1
            except Exception as e:
                messages.error(request, f'Erro para {user.email}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'Emails enviados para {count} usuários')
    
    @admin.action(description='📋 Duplicar usuário')
    def duplicar_usuario(self, request, queryset):
        for user in queryset:
            new_user = User.objects.create(
                username=f"{user.username}_copy",
                email=f"copy_{user.email}",
                role=user.role,
                first_name=user.first_name,
                last_name=user.last_name,
                curso=user.curso,
                classe=user.classe,
                two_factor_enabled=user.two_factor_enabled,
                is_active=True
            )
            new_user.set_password('Temp123456')
            new_user.save()
        messages.success(request, f'{queryset.count()} usuários duplicados')
    
    def save_model(self, request, obj, form, change):
        """Garantir regras ao salvar"""
        if obj.role == 'ADMIN':
            obj.two_factor_enabled = False
            obj.is_staff = True
            obj.can_login = True
            obj.can_register = True
        
        if not change:
            if not obj.username:
                obj.username = obj.email.split('@')[0]
        
        super().save_model(request, obj, form, change)
        
        action = 'atualizado' if change else 'criado'
        SystemLog.objects.create(
            user=request.user,
            action=f'Usuário {action}: {obj.email}',
            level='INFO',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    def delete_model(self, request, obj):
        SystemLog.objects.create(
            user=request.user,
            action=f'Usuário deletado: {obj.email}',
            level='WARNING',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        super().delete_model(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj == request.user:
            return False
        return request.user.is_superuser