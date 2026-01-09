from django.contrib import admin
from .models import EmailTemplate, EmailConfiguration, EmailLog, CertificateBatch


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'is_predefined', 'created_at']
    list_filter = ['is_predefined', 'created_at']
    search_fields = ['name', 'subject', 'body_content']
    readonly_fields = ['created_at', 'updated_at']

    def get_readonly_fields(self, request, obj=None):
        # Make predefined templates read-only
        if obj and obj.is_predefined:
            return self.readonly_fields + ['name', 'subject', 'header_message', 'body_content', 'is_predefined']
        return self.readonly_fields


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['email_domain', 'from_email', 'from_name', 'updated_at']
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        # Only allow one configuration instance
        return not EmailConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of configuration
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'email', 'certificate_filename', 'status', 'sent_at']
    list_filter = ['status', 'sent_at', 'template_used']
    search_fields = ['student_id', 'email', 'certificate_filename']
    readonly_fields = ['student_id', 'email', 'certificate_filename', 'template_used', 'status', 'error_message', 'sent_at']
    date_hierarchy = 'sent_at'

    def has_add_permission(self, request):
        # Don't allow manual creation of logs
        return False


@admin.register(CertificateBatch)
class CertificateBatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'template_used', 'successful_sends', 'total_certificates', 'started_at']
    list_filter = ['status', 'started_at']
    readonly_fields = ['template_used', 'total_certificates', 'successful_sends', 'failed_sends', 
                       'status', 'started_at', 'completed_at', 'error_details']
    date_hierarchy = 'started_at'

    def has_add_permission(self, request):
        # Don't allow manual creation of batches
        return False