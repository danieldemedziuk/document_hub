import base64

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user

PASSWORD = 'document-hub-test-password-2026'


@tagged('post_install', '-at_install')
class TestDocumentAccess(TransactionCase):
    """document create()/archive/restore/new version run sudo()'d so that
    read-only department groups can upload. These tests pin down that the
    sudo() does not let anyone reach folders, documents or files they cannot
    read themselves."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Folder = cls.env['document_hub.folder']
        cls.production_folder = Folder.create({'name': 'Production docs', 'visibility_production': True})
        cls.hr_folder = Folder.create({'name': 'HR docs', 'visibility_hr': True})
        cls.producer = mail_new_test_user(
            cls.env, 'dh_producer', password=PASSWORD,
            groups='base.group_user,document_hub.group_document_hub_document_production')
        cls.colleague = mail_new_test_user(
            cls.env, 'dh_colleague', password=PASSWORD,
            groups='base.group_user,document_hub.group_document_hub_document_production')
        cls.hr_document = cls.env['document_hub.document'].create({
            'topic': 'Payroll',
            'folder_id': cls.hr_folder.id,
            'file_ids': [Command.set(cls._make_attachment(cls.env, 'payroll.pdf').ids)],
        })
        cls.production_document = cls.env['document_hub.document'].create({
            'topic': 'Drawing',
            'folder_id': cls.production_folder.id,
            'file_ids': [Command.set(cls._make_attachment(cls.env, 'drawing.pdf').ids)],
        })

    @staticmethod
    def _make_attachment(env, name, **vals):
        return env['ir.attachment'].create(dict({
            'name': name,
            'datas': base64.b64encode(b'%PDF-1.4 test'),
        }, **vals))

    def _create_as(self, user, folder, attachment):
        return self.env['document_hub.document'].with_user(user).create({
            'topic': attachment.name,
            'folder_id': folder.id,
            'file_ids': [Command.set(attachment.ids)],
        })

    # --- what must keep working -------------------------------------------

    def test_read_only_department_can_upload_into_its_folder(self):
        upload = self._make_attachment(self.env(user=self.producer), 'own.pdf')

        document = self._create_as(self.producer, self.production_folder, upload)

        self.assertEqual(document.folder_id, self.production_folder)
        self.assertEqual((upload.res_model, upload.res_id), ('document_hub.document', document.id))
        self.assertTrue(document.with_user(self.producer).file_ids.with_user(self.producer).raw)

    def test_department_can_trash_and_new_version_its_documents(self):
        document = self.production_document.with_user(self.producer)
        new_file = self._make_attachment(self.env, 'drawing-v2.pdf',
                                         res_model='document_hub.document', res_id=document.id)

        document.action_upload_new_version(new_file.id)
        document.action_archive()

        self.assertEqual(self.production_document.file_ids, new_file)
        self.assertFalse(self.production_document.active)

    def test_restoring_an_old_version_is_still_allowed(self):
        document = self.production_document.with_user(self.producer)
        old_file = self.production_document.file_ids
        new_file = self._make_attachment(self.env, 'drawing-v2.pdf',
                                         res_model='document_hub.document', res_id=document.id)
        document.action_upload_new_version(new_file.id)

        document.action_upload_new_version(old_file.id)

        self.assertEqual(self.production_document.file_ids, old_file)

    # --- what the sudo() must not open up ---------------------------------

    def test_cannot_upload_into_a_folder_one_cannot_see(self):
        upload = self._make_attachment(self.env(user=self.producer), 'planted.pdf')

        with self.assertRaises(AccessError):
            self._create_as(self.producer, self.hr_folder, upload)

    def test_cannot_upload_via_default_folder_one_cannot_see(self):
        upload = self._make_attachment(self.env(user=self.producer), 'planted.pdf')

        with self.assertRaises(AccessError):
            self.env['document_hub.document'].with_user(self.producer).with_context(
                default_folder_id=self.hr_folder.id).create({
                    'topic': 'planted', 'file_ids': [Command.set(upload.ids)]})

    def test_cannot_take_over_a_file_of_a_hidden_document(self):
        payroll_file = self.hr_document.file_ids

        with self.assertRaises(AccessError):
            self._create_as(self.producer, self.production_folder, payroll_file)

    def test_cannot_take_over_someone_elses_unsaved_upload(self):
        colleague_upload = self._make_attachment(self.env(user=self.colleague), 'colleague.pdf')

        with self.assertRaises(AccessError):
            self._create_as(self.producer, self.production_folder, colleague_upload)
        self.assertFalse(colleague_upload.res_id)

    def test_cannot_add_a_hidden_file_to_an_existing_document(self):
        # The everyone group has write access on documents (no sudo involved).
        writer = mail_new_test_user(
            self.env, 'dh_writer', password=PASSWORD,
            groups='base.group_user,document_hub.group_document_hub_document_everyone')
        self.production_folder.visibility_everyone = True

        with self.assertRaises(AccessError):
            self.production_document.with_user(writer).write(
                {'file_ids': [Command.link(self.hr_document.file_ids.id)]})

    def test_cannot_move_a_document_into_a_hidden_folder(self):
        writer = mail_new_test_user(
            self.env, 'dh_writer', password=PASSWORD,
            groups='base.group_user,document_hub.group_document_hub_document_everyone')
        self.production_folder.visibility_everyone = True

        with self.assertRaises(AccessError):
            self.production_document.with_user(writer).write({'folder_id': self.hr_folder.id})

    def test_cannot_trash_a_hidden_document(self):
        with self.assertRaises(AccessError):
            self.hr_document.with_user(self.producer).action_archive()
        self.assertTrue(self.hr_document.active)

    def test_cannot_restore_a_hidden_document(self):
        self.hr_document.action_archive()

        with self.assertRaises(AccessError):
            self.hr_document.with_user(self.producer).action_unarchive()
        self.assertFalse(self.hr_document.active)

    def test_cannot_replace_files_of_a_hidden_document(self):
        upload = self._make_attachment(self.env(user=self.producer), 'planted.pdf')

        with self.assertRaises(AccessError):
            self.hr_document.with_user(self.producer).action_upload_new_version(upload.id)

    def test_cannot_put_a_hidden_file_into_own_document_as_new_version(self):
        with self.assertRaises(AccessError):
            self.production_document.with_user(self.producer).action_upload_new_version(
                self.hr_document.file_ids.id)

    # --- moving folders -----------------------------------------------------

    def _folder_creator(self):
        return mail_new_test_user(
            self.env, 'dh_folder_creator', password=PASSWORD,
            groups='base.group_user,document_hub.group_document_hub_document_production,'
                   'document_hub.group_document_hub_folder_creator')

    def test_folder_creator_can_move_own_folder(self):
        creator = self._folder_creator()
        folder = self.env['document_hub.folder'].with_user(creator).create(
            {'name': 'Drafts', 'visibility_production': True})

        folder.write({'parent_folder_id': self.production_folder.id})

        self.assertEqual(folder.parent_folder_id, self.production_folder)

    def test_cannot_move_a_folder_under_a_hidden_folder(self):
        creator = self._folder_creator()
        folder = self.env['document_hub.folder'].with_user(creator).create(
            {'name': 'Drafts', 'visibility_production': True})

        with self.assertRaises(AccessError):
            folder.write({'parent_folder_id': self.hr_folder.id})

    def test_cannot_move_a_folder_into_its_own_subfolder(self):
        child = self.env['document_hub.folder'].create(
            {'name': 'Child', 'parent_folder_id': self.production_folder.id})

        with self.assertRaises(ValidationError):
            self.production_folder.write({'parent_folder_id': child.id})
