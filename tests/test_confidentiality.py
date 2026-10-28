import base64

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user

GROUP = 'document_hub.group_document_hub_document_'
PASSWORD = 'document-hub-test-password-2026'
LEVELS = ('public', 'internal', 'confidential', 'strictly_confidential')


@tagged('post_install', '-at_install')
class TestConfidentiality(TransactionCase):
    """Who reads a document of each confidentiality level, and who may change it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = cls._user('dh_conf_hr', 'hr')
        cls.producer = cls._user('dh_conf_producer', 'production')
        cls.director = cls._user('dh_conf_director', 'director')
        cls.manager = cls._user('dh_conf_manager', 'manager')
        cls.owner = cls._user('dh_conf_owner', 'everyone')
        cls.hr_folder = cls.env['document_hub.folder'].create({'name': 'HR confidential', 'visibility_hr': True})
        cls.documents = {
            level: cls.env['document_hub.document'].create({
                'topic': level,
                'folder_id': cls.hr_folder.id,
                'owner_id': cls.owner.id,
                'confidentiality': level,
                'file_ids': [Command.set(cls._attachment(f'{level}.pdf').ids)],
            }) for level in LEVELS
        }

    @classmethod
    def _user(cls, login, group):
        return mail_new_test_user(cls.env, login, password=PASSWORD, groups=f'base.group_user,{GROUP}{group}')

    @classmethod
    def _attachment(cls, name):
        return cls.env['ir.attachment'].create({'name': name, 'datas': base64.b64encode(b'%PDF-1.4 test')})

    def _visible_levels(self, user):
        ids = [document.id for document in self.documents.values()]
        visible = self.env['document_hub.document'].with_user(user).search([('id', 'in', ids)])
        return set(visible.mapped('confidentiality'))

    # --- reading ------------------------------------------------------------

    def test_who_reads_which_level(self):
        expected = {
            self.producer: {'public'},
            self.hr_user: {'public', 'internal'},
            self.director: {'public', 'internal', 'confidential'},
            self.manager: set(LEVELS),
            self.owner: set(LEVELS),
        }
        for user, levels in expected.items():
            with self.subTest(user=user.login):
                self.assertEqual(self._visible_levels(user), levels)

    def test_authorized_person_reads_whatever_the_level_and_folder(self):
        strict = self.documents['strictly_confidential']
        strict.authorized_user_ids = self.producer

        self.assertIn('strictly_confidential', self._visible_levels(self.producer))
        self.assertTrue(strict.with_user(self.producer).file_ids.with_user(self.producer).raw)

    def test_authorized_person_may_read_but_not_edit(self):
        # The everyone group has write access on documents.
        reader = self._user('dh_conf_reader', 'everyone')
        confidential = self.documents['confidential']
        confidential.authorized_user_ids = reader

        self.assertEqual(confidential.with_user(reader).topic, 'confidential')
        with self.assertRaises(AccessError):
            confidential.with_user(reader).topic = 'renamed'

    def test_hidden_level_hides_files_and_versions(self):
        strict = self.documents['strictly_confidential']
        strict.action_upload_new_version(self._attachment('strict-v2.pdf').id)
        old_file = strict.version_ids.attachment_id

        with self.assertRaises(AccessError):
            strict.file_ids.with_user(self.hr_user).check('read')
        with self.assertRaises(AccessError):
            old_file.with_user(self.hr_user).check('read')
        Version = self.env['document_hub.document.version']
        self.assertFalse(Version.with_user(self.hr_user).search([('document_id', '=', strict.id)]))
        self.assertTrue(Version.with_user(self.manager).search([('document_id', '=', strict.id)]))

    # --- defaults -----------------------------------------------------------

    def test_folder_default_level_is_used_and_inherited(self):
        Folder = self.env['document_hub.folder']
        parent = Folder.create({'name': 'Payroll', 'visibility_hr': True,
                                'default_confidentiality': 'strictly_confidential'})
        child = Folder.create({'name': 'Payroll 2026', 'parent_folder_id': parent.id})

        document = self.env['document_hub.document'].create({
            'topic': 'Payslips', 'folder_id': child.id,
            'file_ids': [Command.set(self._attachment('payslips.pdf').ids)],
        })

        self.assertEqual(child.default_confidentiality, 'strictly_confidential')
        self.assertEqual(document.confidentiality, 'strictly_confidential')

    # --- changing the level -------------------------------------------------

    def test_editor_may_raise_but_not_lower_the_level(self):
        # The HR group has write access on documents.
        internal = self.documents['internal'].with_user(self.hr_user)
        public = self.documents['public'].with_user(self.hr_user)

        with self.assertRaises(UserError):
            internal.confidentiality = 'public'
        public.confidentiality = 'internal'

        self.assertEqual(self.documents['public'].confidentiality, 'internal')

    def test_editor_may_not_widen_access_by_other_means(self):
        internal = self.documents['internal'].with_user(self.hr_user)

        with self.assertRaises(UserError):
            internal.authorized_user_ids = self.producer
        with self.assertRaises(UserError):
            internal.owner_id = self.hr_user

    def test_owner_and_manager_may_lower_the_level(self):
        self.documents['confidential'].with_user(self.owner).confidentiality = 'public'
        self.documents['strictly_confidential'].with_user(self.manager).write({
            'confidentiality': 'internal', 'authorized_user_ids': [Command.set(self.producer.ids)]})

        self.assertEqual(self.documents['confidential'].confidentiality, 'public')
        self.assertEqual(self.documents['strictly_confidential'].confidentiality, 'internal')
