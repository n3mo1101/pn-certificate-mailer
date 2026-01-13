from django import forms
from .models import EmailTemplate
from django.conf import settings


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'header_message', 'body_content', 'college']
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
            'college': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # For non-superusers: auto-populate and lock college field
        if self.user and not self.user.is_superuser:
            if hasattr(self.user, 'profile') and self.user.profile:
                # Set initial value to user's college
                self.fields['college'].initial = self.user.profile.college
                self.fields['college'].disabled = True
                self.fields['college'].help_text = "College is automatically set based on your account"
                self._user_college = self.user.profile.college
            else:
                # If user has no profile, hide the field and remove from required
                self.fields['college'].widget = forms.HiddenInput()
                self.fields['college'].required = False
    
    def clean_college(self):
        if self.user and not self.user.is_superuser:
            if hasattr(self, '_user_college'):
                return self._user_college
        return self.cleaned_data.get('college')


class SendCertificatesForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(), 
        empty_label="Select a template",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Choose an email template for the certificates"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter templates based on user's college
        if self.user:
            if self.user.is_superuser:
                # Superusers see all templates
                self.fields['template'].queryset = EmailTemplate.objects.all()
            elif hasattr(self.user, 'profile'):
                # Regular users see only their college's templates
                self.fields['template'].queryset = EmailTemplate.objects.filter(
                    college=self.user.profile.college
                )
            else:
                self.fields['template'].queryset = EmailTemplate.objects.none()
        else:
            self.fields['template'].queryset = EmailTemplate.objects.none()