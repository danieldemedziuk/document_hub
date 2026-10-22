from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install')
class TestProjectFolder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref('document_hub.folder_template_project')
        cls.manager = mail_new_test_user(
            cls.env, 'document_hub_manager', groups='base.group_user,document_hub.group_document_hub_document_manager')

    def test_new_project_gets_folder_structure_from_template(self):
        project = self.env['project.project'].create({'name': 'Control cabinet'})
        folder = self.env['document_hub.folder'].search([('project_id', '=', project.id)])

        self.assertEqual(folder.name, project.display_name)
        self.assertEqual(folder.parent_folder_id, self.env.ref('document_hub.folder_project'))
        self.assertEqual(folder.children_folder_ids.mapped('name'), self.template.line_ids.mapped('name'))
        self.assertEqual(folder.children_folder_ids.template_line_id, self.template.line_ids)

    def test_manager_can_edit_folder_template(self):
        template = self.template.with_user(self.manager)

        template.write({'name': 'Projects', 'line_ids': [Command.create({'name': 'Contracts'})]})

        self.assertEqual(template.name, 'Projects')
        self.assertIn('Contracts', template.line_ids.mapped('name'))

    def test_only_manually_added_template_lines_can_be_deleted(self):
        module_line = self.env.ref('document_hub.folder_template_project_meeting_notes').with_user(self.manager)
        manual_line = self.env['document_hub.folder.template.line'].with_user(self.manager).create(
            {'template_id': self.template.id, 'name': 'Contracts'})

        with self.assertRaises(UserError):
            module_line.unlink()
        manual_line.unlink()

        self.assertTrue(module_line.exists())
        self.assertFalse(manual_line.exists())
