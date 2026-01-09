from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from django.template.loader import render_to_string
from .models import EmailTemplate, EmailLog, CertificateBatch
from .forms import EmailTemplateForm, SendCertificatesForm
from .utils import send_certificates_batch, validate_certificate_filename


@login_required
def send_certificates_view(request):
    # Main view for sending certificates page
    testing_mode = getattr(settings, 'CERTIFICATE_TESTING_MODE', False)
    
    if request.method == 'POST':
        # Get the uploaded files using getlist()
        form = SendCertificatesForm(request.POST, request.FILES)
        certificate_files = request.FILES.getlist('certificates')
        
        if not certificate_files:
            messages.error(request, "Please upload at least one certificate.")
        else:
            # Validate files and collect valid ones
            validation_errors = []
            valid_files = []
            
            for file in certificate_files:
                if not file.name.lower().endswith('.pdf'):
                    validation_errors.append(f"'{file.name}' is not a PDF file.")
                    continue
                
                if not testing_mode:
                    # DEFAULT MODE: Check filename format (####-#-####.pdf)
                    is_valid, _, _ = validate_certificate_filename(file.name)
                    if not is_valid:
                        validation_errors.append(f"'{file.name}' has invalid format. Expected: ####-#-####.pdf")
                        continue
                
                valid_files.append(file)
            
            # Display validation errors if any
            if validation_errors:
                error_message = "<strong>File Validation Errors:</strong><br>"
                error_message += "<br>".join([f"• {err}" for err in validation_errors[:10]])
                if len(validation_errors) > 10:
                    error_message += f"<br>... and {len(validation_errors) - 10} more errors"
                messages.error(request, error_message)
            
            # If no valid files after validation, stop here
            if not valid_files:
                messages.error(request, "No valid certificate files to process.")
                return render(request, 'send_certificates.html', {
                    'form': form,
                    'recent_logs': EmailLog.objects.select_related('template_used').all()[:20],
                    'testing_mode': testing_mode,
                })
        
        if form.is_valid() and valid_files:
            template = form.cleaned_data['template']
            
            # Show info about skipped files if any
            if validation_errors:
                messages.warning(
                    request,
                    f"⚠ Processing {len(valid_files)} valid file(s). Skipped {len(validation_errors)} invalid file(s)."
                )
            
            # Create batch record
            batch = CertificateBatch.objects.create(
                template_used=template,
                total_certificates=len(valid_files),
                status='processing'
            )
            
            try:
                # Send certificates
                results = send_certificates_batch(
                    certificate_files=valid_files,
                    template=template,
                    batch_obj=batch
                )
                
                # Update batch completion
                batch.update_completion()
                
                # Display results
                if results['failed'] == 0:
                    messages.success(
                        request,
                        f"✓ Success! All {results['successful']} certificates were sent successfully."
                    )
                elif results['successful'] == 0:
                    messages.error(
                        request,
                        f"✗ Failed! All {results['failed']} certificates failed to send."
                    )
                else:
                    messages.warning(
                        request,
                        f"⚠ Partial Success: {results['successful']} out of {results['total']} sent. "
                        f"{results['failed']} failed."
                    )
                
                # Show specific errors if any
                if results['errors']:
                    error_list = "<br>".join([
                        f"• {err['student_id']}: {err['error']}"
                        for err in results['errors'][:5] # Show first 5 errors
                    ])
                    if len(results['errors']) > 5:
                        error_list += f"<br>... and {len(results['errors']) - 5} more errors"
                    messages.error(request, f"Error Details:<br>{error_list}")
            
            # Catch any unexpected exceptions 
            except Exception as e:
                batch.status = 'failed'
                batch.error_details = str(e)
                batch.completed_at = timezone.now()
                batch.save()
                messages.error(request, f"An unexpected error occurred: {str(e)}")
            
            return redirect('send_certificates')
    else:
        form = SendCertificatesForm()
    
    # Get recent logs for display (last 20)
    context = {
        'form': form,
        'recent_logs': EmailLog.objects.select_related('template_used').all()[:20],
        'testing_mode': testing_mode,
    }
    return render(request, 'send_certificates.html', context)


@login_required
def get_batch_progress(request, batch_id):
    # AJAX endpoint to get batch progress
    try:
        batch = CertificateBatch.objects.get(id=batch_id)
        return JsonResponse({
            'status': batch.status,
            'total': batch.total_certificates,
            'successful': batch.successful_sends,
            'failed': batch.failed_sends,
            'completed': batch.status in ['completed', 'failed']
        })
    except CertificateBatch.DoesNotExist:
        return JsonResponse({'error': 'Batch not found'}, status=404)


# List all email templates
class TemplateListView(LoginRequiredMixin, ListView):
    model = EmailTemplate
    template_name = 'templates_list.html'
    context_object_name = 'templates'


# Create a new email template
class TemplateCreateView(LoginRequiredMixin, CreateView):
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = 'template_form.html'
    success_url = reverse_lazy('templates_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f"Template '{form.instance.name}' created successfully!")
        return super().form_valid(form)


# Edit an existing email template
class TemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = 'template_form.html'
    success_url = reverse_lazy('templates_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        return context
    
    def get_queryset(self):
        return EmailTemplate.objects.filter(is_predefined=False)
    
    def form_valid(self, form):
        messages.success(self.request, f"Template '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


# Delete an email template
class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = EmailTemplate
    template_name = 'template_confirm_delete.html'
    success_url = reverse_lazy('templates_list')
    
    def delete(self, request, *args, **kwargs):
        template_name = self.get_object().name
        messages.success(request, f"Template '{template_name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


@login_required
def preview_template(request, pk):
    # Preview an email template
    template = EmailTemplate.objects.get(id=pk)
    
     # Render the email template with sample data
    email_html = render_to_string('email_template.html', {
        'header_message': template.header_message,
        'body_content': template.body_content,
        'for_preview': True,
    })
    
    # Return the rendered HTML directly for preview
    return render(request, 'template_preview.html', {
        'template': template,
        'email_html': email_html,
    })