from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
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
        # Pass user to form for college filtering
        form = SendCertificatesForm(request.POST, request.FILES, user=request.user)
        certificate_files = request.FILES.getlist('certificates')
        
        if not certificate_files:
            messages.error(request, "Please upload at least one certificate.")
        else:
            # Validate files and collect valid ones
            validation_errors = []
            valid_files = []
            
            max_file_size = getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', 10485760)

            for file in certificate_files:
                if not file.name.lower().endswith('.pdf'):
                    validation_errors.append(f"'{file.name}' is not a PDF file.")
                    continue

                if file.size > max_file_size:
                    size_mb = file.size / (1024 * 1024)
                    limit_mb = max_file_size / (1024 * 1024)
                    validation_errors.append(
                        f"'{file.name}' exceeds the {limit_mb:.0f}MB limit ({size_mb:.1f}MB)."
                    )
                    continue
                
                if not testing_mode:
                    # DEFAULT MODE: Check filename format (####-#-####.pdf or ########.pdf)
                    is_valid, _, _ = validate_certificate_filename(file.name)
                    if not is_valid:
                        validation_errors.append(f"'{file.name}' has invalid format. Expected: ####-#-####.pdf or ########.pdf")
                        continue
                
                valid_files.append(file)
            
            # Check batch size limit
            max_batch = getattr(settings, 'MAX_CERTIFICATES_PER_BATCH', 100)
            if len(valid_files) > max_batch:
                validation_errors.append(
                    f"Maximum of {max_batch} certificates per batch. "
                    f"You uploaded {len(valid_files)}."
                )
            
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
                # Get user's college for filtering logs
                if request.user.is_superuser:
                    recent_logs = EmailLog.objects.select_related('template_used').all()[:20]
                elif hasattr(request.user, 'profile') and request.user.profile:
                    recent_logs = EmailLog.objects.select_related('template_used').filter(
                        template_used__college=request.user.profile.college)[:20]
                else:
                    recent_logs = EmailLog.objects.none()[:20]
                
                return render(request, 'send_certificates.html', {
                    'form': form,
                    'recent_logs': recent_logs,
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
        # Pass user to form for college filtering
        form = SendCertificatesForm(user=request.user)
    
    # Paginated logs (filtered by college for non-superusers)
    logs_qs = EmailLog.objects.select_related('template_used')
    if request.user.is_superuser:
        logs_qs = logs_qs.all()
    elif hasattr(request.user, 'profile') and request.user.profile:
        logs_qs = logs_qs.filter(
            template_used__college=request.user.profile.college)
    else:
        logs_qs = logs_qs.none()
    logs_qs = logs_qs.order_by('-sent_at')

    paginator = Paginator(logs_qs, 20)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Build elided page range
    num_pages = paginator.num_pages
    current = page_obj.number
    page_range = []
    if num_pages <= 7:
        page_range = list(range(1, num_pages + 1))
    else:
        page_range.append(1)
        if current > 3:
            page_range.append('...')
        left = max(2, current - 1)
        right = min(num_pages - 1, current + 1)
        if current <= 3:
            right = min(4, num_pages - 1)
        if current >= num_pages - 2:
            left = max(num_pages - 3, 2)
        for p in range(left, right + 1):
            page_range.append(p)
        if current < num_pages - 2:
            page_range.append('...')
        page_range.append(num_pages)

    context = {
        'form': form,
        'page_obj': page_obj,
        'page_range': page_range,
        'testing_mode': testing_mode,
        'MAX_CERTIFICATES_PER_BATCH': settings.MAX_CERTIFICATES_PER_BATCH,
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
    
    def get_queryset(self):
        # Filter templates by user's college (unless superuser)
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, 'profile'):
                return qs.filter(college=self.request.user.profile.college)
            else:
                # User has no profile, return empty queryset
                return qs.none()
        return qs


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
    
    def get_form_kwargs(self):
        # Pass the user to the form
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Auto-set college for non-superusers
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, 'profile'):
                form.instance.college = self.request.user.profile.college
        
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
        # Only allow editing non-predefined templates
        qs = EmailTemplate.objects.filter(is_predefined=False)
        
        # Filter by college for non-superusers
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, 'profile'):
                return qs.filter(college=self.request.user.profile.college)
            else:
                return qs.none()
        return qs
    
    def get_form_kwargs(self):
        # Pass the user to the form
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, f"Template '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


# Delete an email template
class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = EmailTemplate
    template_name = 'template_confirm_delete.html'
    success_url = reverse_lazy('templates_list')
    
    def get_queryset(self):
        # Filter by college for non-superusers
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            if hasattr(self.request.user, 'profile'):
                return qs.filter(college=self.request.user.profile.college)
            else:
                return qs.none()
        return qs
    
    def delete(self, request, *args, **kwargs):
        template_name = self.get_object().name
        messages.success(request, f"Template '{template_name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


@login_required
def preview_template(request, pk):
    # Preview an email template
    template = get_object_or_404(EmailTemplate, id=pk)
    
    # Check if user has access to this template
    if not request.user.is_superuser:
        if hasattr(request.user, 'profile'):
            if template.college != request.user.profile.college:
                messages.error(request, "You don't have permission to view this template.")
                return redirect('templates_list')
        else:
            messages.error(request, "You don't have permission to view this template.")
            return redirect('templates_list')
    
    # Get college information
    college_info = settings.COLLEGES.get(template.college, {})
    
    # Render the email template with sample data
    email_html = render_to_string('email_template.html', {
        'header_message': template.header_message,
        'body_content': template.body_content,
        'college_info': college_info,
        'for_preview': True,
    })
    
    # Return the rendered HTML directly for preview
    return render(request, 'template_preview.html', {
        'template': template,
        'email_html': email_html,
    })