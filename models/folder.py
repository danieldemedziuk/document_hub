# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class Folder(models.Model):
    _name = 'document_hub.folder'
    _description = 'Document hub: Folder'
    _rec_name = 'parent_path'
    _rec_names_search = ['name', 'parent_path']
    _parent_name = 'parent_folder_id'

    name = fields.Char(string='Name', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Html(string='Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
    parent_folder_id = fields.Many2one('document_hub.folder', string='Parent folder', ondelete='cascade')
    children_folder_ids = fields.One2many('document_hub.folder', 'parent_folder_id', string='Sub folder')
    document_ids = fields.One2many('document_hub.document', 'folder_id', string='Documents')
    parent_path = fields.Char(index=True, unaccent=False, compute='_compute_parent_path', store=True, translate=True)

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

    def _folder_path_name(self):
        """Path of the folder, in the language of the current environment."""
        self.ensure_one()
        parent_name = self.parent_folder_id.name
        return f"{parent_name}: {self.name}" if parent_name else self.name

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
