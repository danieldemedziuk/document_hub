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

    def _project_folder(self, project):
        return self.env['document_hub.folder'].search([('project_id', '=', project.id)])

    def _create_document(self, folder, **vals):
        return self.env['document_hub.document'].create(dict({
            'topic': 'Drawing',
            'folder_id': folder.id,
            'file_ids': [Command.create({'name': 'drawing.pdf', 'raw': b'drawing'})],
        }, **vals))

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

    def test_document_takes_the_project_of_its_project_folder(self):
        arena = self.env['project.project'].create({'name': 'Arena'})
        depot = self.env['project.project'].create({'name': 'Depot'})

        document = self._create_document(self._project_folder(arena).children_folder_ids[:1], project_id=depot.id)
        self.assertEqual(document.project_id, arena)

        document.folder_id = self._project_folder(depot)
        self.assertEqual(document.project_id, depot)

        document.folder_id = self.env.ref('document_hub.folder_project')
        self.assertEqual(document.project_id, depot)

    def test_documents_of_a_moved_folder_take_its_new_project(self):
        arena = self.env['project.project'].create({'name': 'Arena'})
        folder = self.env['document_hub.folder'].create({'name': 'Drawings'})
        subfolder = self.env['document_hub.folder'].create({'name': 'Details', 'parent_folder_id': folder.id})
        documents = self._create_document(folder) | self._create_document(subfolder)
        documents[1].action_archive()

        folder.parent_folder_id = self._project_folder(arena)

        self.assertRecordValues(documents, [{'project_id': arena.id}, {'project_id': arena.id}])
