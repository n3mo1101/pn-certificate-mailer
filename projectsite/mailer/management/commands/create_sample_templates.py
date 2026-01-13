from django.core.management.base import BaseCommand
from django.conf import settings
from mailer.models import EmailTemplate


class Command(BaseCommand):
    help = 'Creates sample email templates for all colleges'

    def handle(self, *args, **kwargs):
        template_blueprints = [
            {
                'name': 'Certificate of Registration',
                'subject': 'Certificate of Registration',
                'header_message': 'Congratulations!',
                'body_content_template': '''On behalf of the {college_name}, we are sending you your Certificate of Registration, which serves as your proof of enrollment.

It is important that you keep this document as part of your record, as this is an official school document.

<h3 style="letter-spacing: 1px;">Welcome to the {college_name}!</h3>''',
                'is_predefined': True
            },
            {
                'name': 'Report of Grades',
                'subject': 'Report of Grades',
                'header_message': 'Hello, Alchemist!',
                'body_content_template': '''Kindly see the attached file for the copy of your report of grades for the semester: FIRST Sem. 2025-2026

For questions or concerns, please send an e-mail to {college_email}, with "Report of Grades" as the subject line.

Thank you so much.

<div style="color: red; font-style: italic;">
    This e-mail is confidential. It may also be legally privileged. If you are not the addressee you should not copy, forward, disclose or use any part of it. 
    If you have received this message in error, please delete it and all copies from your system and notify the sender immediately.
</div>''',
                'is_predefined': True
            },
        ]

        created_count = 0
        skipped_count = 0
        
        # Loop through all colleges
        for college_code, college_info in settings.COLLEGES.items():
            college_name = college_info['name']
            college_email = college_info['email']
            
            self.stdout.write(
                self.style.MIGRATE_HEADING(f'\n--- Creating templates for {college_name} ({college_code}) ---')
            )
            
            # Create templates for this college
            for blueprint in template_blueprints:
                # Format the body content with college-specific information
                body_content = blueprint['body_content_template'].format(
                    college_name=college_name,
                    college_email=college_email
                )
                
                # Use template name as is (college will be differentiated by the college field)
                template_name = blueprint['name'] 
                
                template_data = {
                    'name': template_name,
                    'subject': blueprint['subject'],
                    'header_message': blueprint['header_message'],
                    'body_content': body_content,
                    'college': college_code,
                    'is_predefined': blueprint['is_predefined']
                }
                
                # Create or get the template (unique by name AND college)
                template, created = EmailTemplate.objects.get_or_create(
                    name=template_data['name'],
                    college=college_code,
                    defaults=template_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created: {template.name}')
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'  ↷ Already exists: {template.name}')
                    )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(f'\n{"="*60}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Completed!')
        )
        self.stdout.write(
            self.style.SUCCESS(f'  • Created: {created_count} new template(s)')
        )
        self.stdout.write(
            self.style.WARNING(f'  • Skipped: {skipped_count} existing template(s)')
        )
        self.stdout.write(
            self.style.SUCCESS(f'  • Total colleges: {len(settings.COLLEGES)}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'{"="*60}\n')
        )