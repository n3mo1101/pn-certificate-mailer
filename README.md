<div align="center">
  <img src="projectsite\static\img\nexus_text_logo.png" alt="Project Nexus" style="max-width: 175px; height: auto">
</div>

# Certificate Mailer

A Django web application for distributing certificates and email messages to students. The system validates PDF certificate files, extracts student information from filenames, and sends emails with attachments using customizable templates.

## Features

- **Batch Certificate Sending**: Upload multiple PDF certificates and send them all at once
- **Email Template Management**: Create, edit, preview, and delete custom email templates
- **Automatic Email Generation**: Converts student IDs from filenames to institutional email addresses
- **Email Logging**: Tracks all sent emails with success/failure status and error messages
- **Preview Functionality**: Preview email templates before sending

## How It Works

### Filename to Email Validation

The application uses two modes for validating certificate filenames and generating email addresses:

#### Default Mode (Production)
- **Filename Format**: `####-#-####.pdf` (e.g., `2000-1-0123.pdf`)
- **Email Format**: Student ID without hyphens + domain (e.g., `200010123@psu.palawan.edu.ph`)
- **Validation**: Strict format checking - all three parts must be numeric and separated by hyphens

#### Testing Mode
- **Filename Format**: Any PDF filename (e.g., `john.doe.pdf`)
- **Email Format**: Filename (without extension) + test domain (e.g., `john.doe@gmail.com`)
- **Validation**: Minimal - only checks if file is a PDF
- **Use Case**: Development, testing, or sending to non-standard email addresses

To enable testing mode, set in `projectsite/settings.py`:
```python
CERTIFICATE_TESTING_MODE = True
CERTIFICATE_TEST_EMAIL_DOMAIN = "gmail.com"  # or any domain
```

### Synchronous Sending Process

**Important**: This application sends emails **synchronously** (one after another), not in parallel. This means:

- Emails are sent sequentially in the order they are processed
- The sending process blocks until all emails are sent or fail
- For large batches (50+ certificates), the process may take several minutes
- The user must wait for the entire batch to complete before the page refreshes

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd pn-certificate-mail
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `projectsite/` directory:
```env
EMAIL_HOST_USER='your-email@gmail.com'
EMAIL_HOST_PASSWORD='your-app-password'
DEFAULT_FROM_EMAIL='your-email@gmail.com'
```

**Gmail App Password Setup** (Brief):
1. Go to Google Account Settings → Security
2. Enable 2-Step Verification
3. Generate an App Password (Select "Mail" and your device)
4. Use the 16-character password in your `.env` file

### 5. Run Migrations
```bash
cd projectsite
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```
Follow the prompts to set username, email, and password.

### 7. Create Sample Templates (Optional)
```bash
python manage.py create_sample_templates
```
This creates three sample templates:
- Template 1 - COR (Certificate of Registration)
- Template 2 - COA (Certificate of Achievement)
- Template 3 - COG (Copy of Grades)

### 8. Run Development Server
```bash
python manage.py runserver
```
Access the application at: `http://127.0.0.1:8000`  

### 9. Update Email Configuration

#### Email Configuration

Log in and configure email settings through the Django Admin Panel:

1. Click the 'Admin Panel' or go to: `http://127.0.0.1:8000/admin/`
2. Navigate to **Email Configuration**
3. Set the following:
   - **Email Domain**: Your institution's domain (e.g., `psu.palawan.edu.ph`)
   - **From Email**: Sender email address (IMPORTANT)
   - **From Name**: Display name for sender (e.g., "College of Sciences")
   - **SMTP Host**: SMTP server (default: `smtp.gmail.com`)
   - **SMTP Port**: SMTP port (default: `587`)

## Using the Application

### 1. Managing Email Templates

#### View Templates
- Navigate to **Manage Templates** from the navigation bar
- View all custom and sample templates

#### Create New Template
1. Click **"+ Create New Template"**
2. Fill in:
   - **Template Name**: Unique identifier
   - **Email Subject**: Subject line for emails
   - **Header Message**: Large header text in email
   - **Body Content**: Main email content (supports HTML tags)
     - **Supports HTML**: Use tags like `<strong>`, `<em>`, `<h4>`, `<div>`, `<br>`, etc.
     - **Example**: 
       ```html
       Welcome to the <strong>College of Sciences</strong>!
       
       Your certificate is attached to this email.
       
       <h4>Important Reminders:</h4>
       Keep this document safe as it is an official record.
       
       <div style="color: red; font-style: italic;">
       This email is confidential and intended only for the addressee.
       </div>
       ```
   

3. Click **"Save Template"**

#### Edit Template
- Only **custom templates** can be edited
- Sample templates are read-only
- Click **"Edit"** on any custom template

#### Preview Template
- Click **"Preview"** to see how the email will look
- Shows subject line and full email design with logos

#### Delete Template
- Click **"Delete"** on any template
- Confirm deletion (this action cannot be undone)

### 2. Sending Certificates

1. Navigate to **Send Certificates**
2. **Select Email Template** from dropdown
3. **Upload Certificate Files**:
   - Click "Choose Files" and select multiple PDFs
   - Files must follow naming convention (unless in testing mode)
   - Example: `2000-1-0123.pdf`, `2021-2-0456.pdf`
4. Click **"Send Certificates"**
5. Confirm the operation
6. Monitor progress modal (shows sending status)
7. Review results:
   - **Success**: All certificates sent
   - **Partial Success**: Some failed, some succeeded
   - **Failed**: All certificates failed
8. Check **Recent Email Logs** table for detailed status

### 3. Viewing Logs

**Recent Email Logs** (on Send Certificates page):
- Last 20 certificate deliveries
- Shows student ID, email, filename, status, timestamp, and errors

**Admin Panel Logs** (detailed view):
- Navigate to the Admin Panel or `http://127.0.0.1:8000/admin/`
- View **Email Logs** for complete history
- Filter by status, date, template
- View **Certificate Batches** for batch operation tracking

## File Naming Conventions

### Default Mode
```
Format: ####-#-####.pdf
Examples:
  ✓ 2000-1-0123.pdf → 200010123@psu.palawan.edu.ph
  ✓ 2021-2-0456.pdf → 202120456@psu.palawan.edu.ph
  ✗ 2000-0123.pdf (invalid - wrong format)
  ✗ john-doe.pdf (invalid - not numeric)
```

### Testing Mode
```
Format: <anything>.pdf
Examples:
  ✓ john.doe.pdf → john.doe@gmail.com
  ✓ test.user.pdf → test.user@gmail.com
  ✓ alice-smith.pdf → alice-smith@gmail.com
```

## Troubleshooting

### Emails Not Sending
- Verify Gmail App Password is correct in `.env`
- Check Email Configuration in admin panel
- Ensure 2-Step Verification is enabled on Google Account
- Check email logs for specific error messages

### Invalid Filename Errors
- Ensure filenames match the required format: `####-#-####.pdf`
- Check that all parts are numeric (no letters)
- Or enable Testing Mode for flexible naming

### File Upload Issues
- Maximum file size: 10MB per file
- Only PDF files are accepted
- Check file permissions in upload directory

### Template Not Showing
- Run `python manage.py create_sample_templates` to create default templates
- Or create templates manually through the web interface

## License

© 2025 - 2026 Computer Studies Department  
Powered by **Project Nexus**

---