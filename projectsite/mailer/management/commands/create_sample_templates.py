from django.core.management.base import BaseCommand
from mailer.models import EmailTemplate


class Command(BaseCommand):
    help = 'Creates sample email templates for the certificate mailer'

    def handle(self, *args, **kwargs):
        templates = [
            {
                'name': 'Template 1 - COR',
                'subject': 'Certificate of Registration',
                'header_message': 'Congratulations!',
                'body_content': '''On behalf of the College of Sciences, we are sending you your Certificate of Registration, which serves as your proof of enrollment.

It is important that you keep this document as part of your record, as this is an official school document.

If you have any questions or need additional copies of your certificate, please don't hesitate to contact us.

<h4>Welcome to the College of Sciences!</h4>''',
                'is_predefined': True
            },
            {
                'name': 'Template 2 - COA',
                'subject': 'Certificate of Achievement',
                'header_message': 'Outstanding Achievement!',
                'body_content': '''We are delighted to recognize your exceptional performance and achievement.

Your Certificate of Achievement is attached to this email, acknowledging your outstanding work and dedication.

This certificate is a testament to your commitment to excellence. We are proud of your accomplishments and look forward to your continued success.

Congratulations once again on this well-deserved recognition!

<h4>From the College of Sciences!</h4>''',
                'is_predefined': True
            },
            {
                'name': 'Template 3 - COG',
                'subject': 'Copy of Grades',
                'header_message': 'Hello, Alchemist!',
                'body_content': '''Kindly see the attached file for the copy of your report of grades for the semester: FIRST Sem. 2025-2026

For questions or concerns, please send an e-mail to cs@psu.palawan.edu.ph, with "Report of Grades" as the subject line.

Thank you so much.

<div style="color: red; font-style: italic;">
    This e-mail is confidential. It may also be legally privileged. If you are not the addressee you should not copy, forward, disclose or use any part of it. 
    If you have received this message in error, please delete it and all copies from your system and notify the sender immediately.
</div>''',
                'is_predefined': True
            },
        ]

        created_count = 0
        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'→ Template already exists: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nCompleted! Created {created_count} new template(s).')
        )