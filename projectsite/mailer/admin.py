from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile,
    EmailTemplate,
    EmailConfiguration,
    EmailLog,
    CertificateBatch
)


# Inline admin for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ['college']


# Extended User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    
    def get_inline_instances(self, request, obj=None):
        # Only show profile inline for non-superusers
        if obj and obj.is_superuser:
            return []
        return super().get_inline_instances(request, obj)


# Unregister the default User admin and register the new one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# UserProfile Admin (standalone)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'college', 'get_email']
    list_filter = ['college']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'


# Email Template Admin
@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'college', 'subject', 'is_predefined', 'created_at', 'updated_at']
    list_filter = ['college', 'is_predefined', 'created_at']
    search_fields = ['name', 'subject', 'header_message', 'body_content']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'college', 'is_predefined')
        }),
        ('Email Content', {
            'fields': ('subject', 'header_message', 'body_content')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusers see all templates
        if request.user.is_superuser:
            return qs
        # Regular staff users see only their college's templates
        if hasattr(request.user, 'profile'):
            return qs.filter(college=request.user.profile.college)
        return qs.none()


# Email Configuration Admin
@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['email_domain', 'from_email', 'from_name', 'smtp_host', 'smtp_port', 'updated_at']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Email Settings', {
            'fields': ('email_domain', 'from_email', 'from_name')
        }),
        ('SMTP Configuration', {
            'fields': ('smtp_host', 'smtp_port')
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one configuration
        return not EmailConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the configuration
        return False


# Email Log Admin
@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'email', 'status', 'template_used', 'sent_at']
    list_filter = ['status', 'sent_at', 'template_used__college']
    search_fields = ['student_id', 'email', 'certificate_filename', 'error_message']
    readonly_fields = ['student_id', 'email', 'certificate_filename', 'template_used', 
                       'status', 'error_message', 'sent_at']
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        # Logs are created automatically, not manually
        return False
    
    def has_change_permission(self, request, obj=None):
        # Logs should not be edited
        return False


# Certificate Batch Admin
@admin.register(CertificateBatch)
class CertificateBatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'template_used', 'status', 'total_certificates', 
                    'successful_sends', 'failed_sends', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at', 'template_used__college']
    search_fields = ['id', 'error_details']
    readonly_fields = ['template_used', 'total_certificates', 'successful_sends', 
                       'failed_sends', 'status', 'started_at', 'completed_at', 'error_details']
    date_hierarchy = 'started_at'
    
    def has_add_permission(self, request):
        # Batches are created automatically, not manually
        return False
    
    def has_change_permission(self, request, obj=None):
        # Batches should not be edited
        return False