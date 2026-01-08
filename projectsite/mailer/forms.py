from django import forms
from .models import EmailTemplate


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'header_message', 'body_content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Certificate of Registration'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2025-2026 First Semester'
            }),
            'header_message': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Congratulations!'
            }),
            'body_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Enter the main email body content here...'
            }),
        }


class SendCertificatesForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.all(),
        empty_label="Select a template",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Choose an email template for the certificates"
    )