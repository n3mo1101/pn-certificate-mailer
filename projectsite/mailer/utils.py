import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
from .models import EmailConfiguration, EmailLog

# ============================================================
# TESTING MODE CONFIGURATION
# ============================================================
# Set CERTIFICATE_TESTING_MODE = True in settings.py to enable testing mode
# In testing mode: filename (without .pdf) becomes email address directly without name validation
# Example: "john.doe.pdf" -> "john.doe@test_domain"
# ============================================================


def extract_student_id_from_filename(filename):
    # Extract student ID and removes .pdf extension
    return filename.replace('.pdf', '').replace('.PDF', '')


def generate_email_from_student_id(student_id):
    """
    Generate email address from student ID.
    
    DEFAULT MODE (CERTIFICATE_TESTING_MODE = False):
        Format: ####-#-#### → ########@domain.edu.ph
        Example: "2000-1-0123" → "200010123@psu.palawan.edu.ph"
    
    TESTING MODE (CERTIFICATE_TESTING_MODE = True):
        Format: student_id → student_id@test_domain
        Example: "john.doe" → "john.doe@gmail.com"
    """

    # Check if testing mode is enabled
    testing_mode = getattr(settings, 'CERTIFICATE_TESTING_MODE', False)
    
    if testing_mode:
        test_domain = getattr(settings, 'CERTIFICATE_TEST_EMAIL_DOMAIN', 'gmail.com')
        return f"{student_id}@{test_domain}"
    
    config = EmailConfiguration.get_config()
    email_prefix = student_id.replace('-', '')
    return f"{email_prefix}@{config.email_domain}"


def validate_certificate_filename(filename):
    # Validate certificate filename based on mode.

    # Returns (is_valid, student_id, email)
    if not filename.lower().endswith('.pdf'):
        return False, None, None
    
    student_id = extract_student_id_from_filename(filename)
    testing_mode = getattr(settings, 'CERTIFICATE_TESTING_MODE', False)
    
    if testing_mode:
        email = generate_email_from_student_id(student_id)
        return True, student_id, email
    
    # DEFAULT MODE: Validate ####-#-#### format
    parts = student_id.split('-')
    if len(parts) != 3:
        return False, None, None
    
    # Check if all parts are numeric
    try:
        for part in parts:
            int(part)
    except ValueError:
        return False, None, None
    
     # Generate email
    email = generate_email_from_student_id(student_id)
    return True, student_id, email


def get_logo_path(logo_filename):
    # Get the absolute path to a logo file
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', logo_filename)
    return logo_path if os.path.exists(logo_path) else None


def read_logo_data(logo_filename):
    # Read logo binary data
    logo_path = get_logo_path(logo_filename)
    if logo_path:
        with open(logo_path, 'rb') as f:
            return f.read()
    return None


def send_certificate_email(certificate_file, template):
    """
    Send a certificate email to a student.
    
    Args:
        certificate_file: InMemoryUploadedFile or File object
        template: EmailTemplate instance
    
    Returns:
        tuple: (success: bool, student_id: str, email: str, error_message: str or None)
    """
    try:
        # Validate filename and extract info
        is_valid, student_id, email = validate_certificate_filename(certificate_file.name)
        
        if not is_valid:
            error_msg = f"Invalid filename format: {certificate_file.name}"
            return False, certificate_file.name, None, error_msg
        
        # Get email configuration
        config = EmailConfiguration.get_config()
        from_email = f"{config.from_name} <{config.from_email}>"
        
         # Prepare email content
        email_message = EmailMultiAlternatives(
            subject=template.subject,
            body=f"{template.header_message}\n\n{template.body_content}",
            from_email=from_email,
            to=[email],
        )
        
         # Create email with alternative content (HTML)
        email_html = render_to_string('email_template.html', {
            'header_message': template.header_message,
            'body_content': template.body_content,
        })
        email_message.attach_alternative(email_html, 'text/html')
        
        # Attach certificate
        email_message.attach(
            certificate_file.name,
            certificate_file.read(),
            'application/pdf'
        )
        
        # Attach logos as inline images
        for logo_name, cid in [('college_logo.png', 'college_logo'), ('nexus_logo.png', 'nexus_logo')]:
            logo_data = read_logo_data(logo_name)
            if logo_data:
                logo_img = MIMEImage(logo_data)
                logo_img.add_header('Content-ID', f'<{cid}>')
                logo_img.add_header('Content-Disposition', 'inline', filename=logo_name)
                email_message.attach(logo_img)
        
        # Send email
        email_message.send(fail_silently=False)
        
        # Log success
        EmailLog.objects.create(
            student_id=student_id,
            email=email,
            certificate_filename=certificate_file.name,
            template_used=template,
            status='success'
        )
        
        return True, student_id, email, None
        
    except Exception as e:
        error_message = str(e)
        EmailLog.objects.create(
            student_id=student_id if 'student_id' in locals() else 'unknown',
            email=email if 'email' in locals() else 'unknown',
            certificate_filename=certificate_file.name,
            template_used=template,
            status='failed',
            error_message=error_message
        )
        
        return False, student_id if 'student_id' in locals() else certificate_file.name, \
               email if 'email' in locals() else None, error_message


def send_certificates_batch(certificate_files, template, batch_obj=None):
    """
    Send multiple certificates in a batch.
    
    Args:
        certificate_files: List of file objects
        template: EmailTemplate instance
        batch_obj: Optional CertificateBatch instance to update
    
    Returns:
        dict: Statistics about the sending process
    """
    results = {
        'total': len(certificate_files),
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for cert_file in certificate_files:
        success, student_id, email, error = send_certificate_email(cert_file, template)
        
        if success:
            results['successful'] += 1
        else:
            results['failed'] += 1
            results['errors'].append({
                'student_id': student_id,
                'email': email,
                'error': error
            })
        
        # Update batch if provided
        if batch_obj:
            batch_obj.successful_sends = results['successful']
            batch_obj.failed_sends = results['failed']
            batch_obj.save()
    
    return results