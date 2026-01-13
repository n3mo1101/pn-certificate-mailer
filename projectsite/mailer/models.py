from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError


# User Profile to store college information
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    college = models.CharField(
        max_length=10,
        choices=settings.COLLEGE_CHOICES,
        help_text="College this user belongs to"
    )
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_college_display()}"


# Signal to auto-create UserProfile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Only create profile if user is not superuser
        # Superusers don't need college assignment
        if not instance.is_superuser:
            UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# Email templates for certificate distribution
class EmailTemplate(models.Model):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=300)
    header_message = models.CharField(max_length=200)
    body_content = models.TextField(help_text="Main email body content")
    college = models.CharField(
        max_length=10,
        choices=settings.COLLEGE_CHOICES,
        help_text="College this template belongs to"
    )
    is_predefined = models.BooleanField(default=False, help_text="Predefined templates cannot be edited")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_predefined', 'name']
        unique_together = [['name', 'college']] # Ensure unique combination of name and college (same name allowed for different colleges)

    def __str__(self):
        return f"{self.name} ({self.college})"
    
    def clean(self):
        # Validate that college code exists in settings
        if self.college not in settings.COLLEGES:
            raise ValidationError({
                'college': f"Invalid college code. Must be one of: {', '.join(settings.COLLEGES.keys())}"
            })


# Singleton model for email configuration
class EmailConfiguration(models.Model):
    email_domain = models.CharField(
        max_length=100,
        default="psu.palawan.edu.ph",
        help_text="(e.g., psu.palawan.edu.ph)"
    )
    from_email = models.EmailField(help_text="The sender email address")
    from_name = models.CharField(
        max_length=200,
        default="College of Sciences",
        help_text="Display name for sender"
    )

    # Gmail SMTP settings (configured in Django admin settings.)
    smtp_host = models.CharField(
        max_length=200,
        default="smtp.gmail.com",
        help_text="SMTP server host"
    )
    smtp_port = models.IntegerField(default=587, help_text="SMTP server port")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configuration"

    def __str__(self):
        return f"Email Config (Domain: {self.email_domain})"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        # Get or create the singleton configuration
        config, _ = cls.objects.get_or_create(pk=1)
        return config


# Log of all certificate emails sent
class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    student_id = models.CharField(max_length=50, db_index=True)
    email = models.EmailField()
    certificate_filename = models.CharField(max_length=255)
    template_used = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='email_logs'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, db_index=True)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['-sent_at', 'status']),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.status}"


# Track batches of certificate sending operations
class CertificateBatch(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    template_used = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True)
    total_certificates = models.IntegerField(default=0)
    successful_sends = models.IntegerField(default=0)
    failed_sends = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name_plural = "Certificate Batches"

    def __str__(self):
        return f"Batch {self.id} - {self.status} ({self.successful_sends}/{self.total_certificates})"

    def update_completion(self):
        # Update batch completion status
        self.completed_at = timezone.now()
        self.status = 'failed' if self.failed_sends > 0 and self.successful_sends == 0 else 'completed'
        self.save()