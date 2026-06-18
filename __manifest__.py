# -*- coding: utf-8 -*-

{
    'name': 'Document hub',
    'version': '17.0.0.0.1',
    'author': 'Daniel Demedziuk',
    'license': 'GPL-2',
    'sequence': 55,
    'category': 'Customizations',
    'summary': 'Advanced document management system for Odoo Community',
    'description': """
Document hub
==================
An advanced document management module for Odoo 17 Community, inspired by the Odoo Enterprise "Documents" app. Enables centralized storage, categorization, sharing, and automation of document workflows within your company.

Key features:
- Store and organize files in folder structures and tags
- Share documents with users and groups
- Departmental document centralization (e.g., HR, Finance, Projects)
- Automatic tagging and classification on import
- Document versioning and change history
- Integration with other modules (Projects, Sales Orders, Contacts)
- Access rights per folder/tag
- Built-in preview for PDFs, images, videos
- Document template creation and management
- Advanced search and filtering
- Workflow automation: task assignment, notifications, validations
- Trash bin with restore capability
- Bulk operations on documents
- Extensions: OCR for text recognition from scans
- Extensions: e-signature integration (e.g., OCA Sign)
- Extensions: automatic import from email or network folders

This module is fully open source under the GPL-2 license.
""",
    'depends': [
        'base', 
        'mail',
        'project',
        'sale_offer',
    ],
    'data': [
        'data/document_sequence.xml',
        'data/folders_data.xml',
        'data/tags_data.xml',
        'data/cron_data.xml',
        'security/document_hub_security.xml',
        'security/ir.model.access.csv',
        'views/project_views.xml',
        'views/document_hub_views.xml',
        'views/config_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}
