# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

GROUP_PREFIX = 'document_hub.group_document_hub_document_'

# Ordered from the least to the most restricted: the position is what tells
# raising a document's level from lowering it (see Document.write()).
CONFIDENTIALITY_LEVELS = [
    ('public', 'Public'),
    ('internal', 'Internal'),
    ('confidential', 'Confidential'),
    ('strictly_confidential', 'Strictly confidential'),
]
CONFIDENTIALITY_RANK = {level: rank for rank, (level, _label) in enumerate(CONFIDENTIALITY_LEVELS)}


class Folder(models.Model):
    _name = 'document_hub.folder'
    _description = 'Document hub: Folder'
    _rec_name = 'parent_path'
    _rec_names_search = ['name', 'parent_path']
    _parent_name = 'parent_folder_id'

    name = fields.Char(string='Name', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True)
    # Separate from active: active=False is the trash (system administrators
    # only), while an archived folder only drops out of the explorer tree -
    # its documents stay readable, searchable and editable as before.
    is_archived = fields.Boolean(string='Archived', default=False, copy=False, index=True,
                                 help='Hidden from the folder tree together with its subfolders. '
                                      'Its documents stay available.')
    description = fields.Html(string='Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
    parent_folder_id = fields.Many2one('document_hub.folder', string='Parent folder', ondelete='cascade')
    children_folder_ids = fields.One2many('document_hub.folder', 'parent_folder_id', string='Sub folder')
    document_ids = fields.One2many('document_hub.document', 'folder_id', string='Documents')
    parent_path = fields.Char(index=True, unaccent=False, compute='_compute_parent_path', store=True, translate=True)

    default_confidentiality = fields.Selection(
        CONFIDENTIALITY_LEVELS, string='Default confidentiality', required=True, default='internal',
        help='Confidentiality level given to documents uploaded into this folder. '
             'New subfolders take it over from their parent. It can still be changed on each document.')

    visibility_administration = fields.Boolean(string='Administration', default=False)
    visibility_purchasing_and_logistics = fields.Boolean(string='Purchasing and logistics', default=False)
    visibility_marketing = fields.Boolean(string='Marketing', default=False)
    visibility_production = fields.Boolean(string='Production', default=False)
    visibility_accounting = fields.Boolean(string='Accounting', default=False)
    visibility_pm = fields.Boolean(string='PM', default=False)
    visibility_hr = fields.Boolean(string='HR', default=False)
    visibility_salesman = fields.Boolean(string='Sales', default=False)
    visibility_everyone = fields.Boolean(string='Everyone', default=False)
    
    is_project = fields.Boolean(string="Is project", default=False, help='Mark this option if you are sure this folder is for projects.')
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null', index=True, copy=False,
                                 readonly=True, help='Project whose main folder this is.')
    template_line_id = fields.Many2one('document_hub.folder.template.line', string='Template line', ondelete='set null',
                                       copy=False, readonly=True, help='Folder template line this folder was created from.')

    # visibility_x flag -> the department group it opens the folder to
    _VISIBILITY_GROUPS = {
        'visibility_administration': f'{GROUP_PREFIX}administration',
        'visibility_purchasing_and_logistics': f'{GROUP_PREFIX}purchasing_and_logistics',
        'visibility_marketing': f'{GROUP_PREFIX}marketing',
        'visibility_production': f'{GROUP_PREFIX}production',
        'visibility_accounting': f'{GROUP_PREFIX}accounting',
        'visibility_pm': f'{GROUP_PREFIX}pm',
        'visibility_hr': f'{GROUP_PREFIX}hr',
        'visibility_salesman': f'{GROUP_PREFIX}salesman',
        'visibility_everyone': f'{GROUP_PREFIX}everyone',
    }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not any(field in vals for field in self._VISIBILITY_GROUPS):
                vals.update(self._default_visibility_values(vals.get('parent_folder_id')))
            if 'default_confidentiality' not in vals and vals.get('parent_folder_id'):
                vals['default_confidentiality'] = self.sudo().browse(
                    vals['parent_folder_id']).default_confidentiality
        return super().create(vals_list)

    def write(self, vals):
        # Moving a folder (drag and drop in the explorer) must not hang it
        # under a folder its mover cannot see.
        if vals.get('parent_folder_id') and not self.env.su:
            self.browse(vals['parent_folder_id']).check_access_rule('read')
        result = super().write(vals)
        if vals.get('parent_folder_id'):
            self._update_documents_project()
        return result

    def _update_documents_project(self):
        """Documents in the folders and their subfolders take the project of their nearest project folder, if any."""
        documents = self.env['document_hub.document'].sudo().with_context(active_test=False).search(
            [('folder_id', 'child_of', self.ids)])
        for document in documents:
            project = document.folder_id._get_project()
            if project and document.project_id != project:
                document.project_id = project

    def action_folder_archive(self):
        self._set_archived(True)

    def action_folder_unarchive(self):
        self._set_archived(False)

    def _set_archived(self, archived):
        if not self.env.su and not self.env.user.has_group('document_hub.group_document_hub_folder_creator'):
            raise AccessError(_('You do not have permission to archive folders.'))
        self.write({'is_archived': archived})

    @api.constrains('parent_folder_id')
    def _check_parent_folder_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('A folder cannot be moved into itself or one of its subfolders.'))

    @api.model
    def _default_visibility_values(self, parent_folder_id):
        """Returns a dict of visibility_x flags to set on a new folder, based on the
        parent folder's flags or the creator's department groups if parent has none.
        
        Returns `{visibility_everyone: True}` if the creator has no department of their own."""
        if parent_folder_id:
            parent = self.sudo().browse(parent_folder_id)
            inherited = {field: True for field in self._VISIBILITY_GROUPS if parent[field]}
            if inherited:
                return inherited
        user = self.env.user
        own = {
            field: True for field, group in self._VISIBILITY_GROUPS.items()
            if field != 'visibility_everyone' and user.has_group(group)
        }
        if not own and user.has_group(self._VISIBILITY_GROUPS['visibility_everyone']):
            own = {'visibility_everyone': True}
        return own

    def _folder_path_name(self):
        """Path of the folder, in the language of the current environment."""
        self.ensure_one()
        parent_name = self.parent_folder_id.name
        return f"{parent_name}: {self.name}" if parent_name else self.name

    def _get_project(self):
        """Project of the nearest main folder of a project: this folder or any folder above it."""
        folder = self
        while folder and not folder.project_id:
            folder = folder.parent_folder_id
        return folder.project_id

    @api.depends('parent_folder_id.name', 'name')
    def _compute_parent_path(self):
        for rec in self:
            rec.parent_path = rec._folder_path_name()

    @api.depends('parent_folder_id.name', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._folder_path_name()

    def unlink(self):
        if not self.env.su and not self.env.user.has_group('base.group_system'):
            raise UserError(_('Only a system administrator can permanently delete folders from the trash.'))
        for folder in self:
            # active_test=False: an archived (trashed) document/subfolder still
            # holds a real FK to this folder and would otherwise cause a
            # ForeignKeyViolation once Postgres' ON DELETE CASCADE on
            # parent_folder_id reaches it - checking only active children let
            # that slip through.
            ctx_folder = folder.with_context(active_test=False)
            if ctx_folder.document_ids:
                raise UserError(_(
                    'You cannot delete folder "%s" while it still contains documents. '
                    'Move, restore or permanently delete them first.'
                ) % folder.name)
            if ctx_folder.children_folder_ids:
                raise UserError(_(
                    'You cannot delete folder "%s" while it still contains subfolders. '
                    'Delete them first.'
                ) % folder.name)
        self.env['document_hub.trash_log'].log_action(self, 'purged')
        return super(Folder, self.sudo()).unlink()

    def action_archive(self):
        # "Delete" in the explorer moves a folder to the trash instead of
        # unlink()'ing it, cascading to its whole subtree so nothing is left
        # dangling under a now-hidden parent. Guarding each recursive call on
        # a non-empty recordset is required, not just tidy: calling
        # action_archive() on an already-empty recordset would otherwise
        # recurse into its (also empty) children_folder_ids forever.
        res = super().action_archive()
        self.env['document_hub.trash_log'].log_action(self, 'deleted')
        children = self.children_folder_ids
        if children:
            children.action_archive()
        documents = self.document_ids
        if documents:
            documents.action_archive()
        return res

    def action_unarchive(self):
        # Mirrors action_archive(): restoring a folder restores its whole
        # subtree together. This can also resurface something that was
        # separately trashed before the folder itself was - an accepted
        # trade-off given only a system administrator can reach this action
        # in the first place, and nothing is destroyed by it either way.
        res = super().action_unarchive()
        self.env['document_hub.trash_log'].log_action(self, 'restored')
        ctx_self = self.with_context(active_test=False)
        children = ctx_self.children_folder_ids
        if children:
            children.action_unarchive()
        documents = ctx_self.document_ids
        if documents:
            documents.action_unarchive()
        return res

    @api.onchange('parent_folder_id')
    def _onchange_parent_folder_id(self):
        # New folders only
        if self._origin or not self.parent_folder_id:
            return
        self.default_confidentiality = self.parent_folder_id.default_confidentiality
        values = self._default_visibility_values(self.parent_folder_id._origin.id)
        if values:
            for field in self._VISIBILITY_GROUPS:
                self[field] = values.get(field, False)

    @api.onchange('visibility_everyone')
    def _change_settings_everyone(self):
        if self.visibility_everyone:
            self.visibility_administration = False
            self.visibility_purchasing_and_logistics = False
            self.visibility_marketing = False
            self.visibility_accounting = False
            self.visibility_pm = False
            self.visibility_hr = False
            self.visibility_salesman = False
