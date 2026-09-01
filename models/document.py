# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Document(models.Model):
    _name = 'document_hub.document'
    _description = 'Document hub: Document'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', default=lambda self: _('New'), copy=False, readonly=True, tracking=True)
    topic = fields.Char(string='Topic', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    file_ids = fields.Many2many('ir.attachment', string='Attachments', required=True)
    file_names = fields.Char(string='Attachment Names', compute='_compute_file_names',
                             help='Newline-separated names of the attached files.')
    cover_attachment_id = fields.Many2one('ir.attachment', string='Cover file', compute='_compute_cover_attachment_id',
                                          store=True, help='First attachment, used as the kanban card thumbnail.')
    cover_mimetype = fields.Char(related='cover_attachment_id.mimetype', string='Cover file type')
    description = fields.Html(string='Description', tracking=True)
    tag_ids = fields.Many2many('document_hub.tag', string='Tags', copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    project_id = fields.Many2one('project.project', string='Project', domain="[('active', 'in', (True, False))]", tracking=True)
    owner_id = fields.Many2one('res.users', string='Owner', default=lambda lm: lm.env.user.id, tracking=True)
    folder_id = fields.Many2one('document_hub.folder', string='Folder', ondelete='restrict', tracking=True, required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
    state = fields.Selection([('open', 'Open'), ('lock', 'Locked')], string='State', default='open', tracking=True, copy=False)
    privacy_doc = fields.Selection([('company', 'Company'), ('mail', 'Mail')], string='Privacy', default='mail', copy=True)
    rel_is_project = fields.Boolean(related='folder_id.is_project')
    rel_is_parent_folder_project = fields.Boolean(related='folder_id.parent_folder_id.is_project')
    is_admin = fields.Boolean(compute='compute_admin_group')
    
    rel_visibility_administration = fields.Boolean(related='folder_id.visibility_administration')
    rel_visibility_purchasing_and_logistics = fields.Boolean(related='folder_id.visibility_purchasing_and_logistics')
    rel_visibility_marketing = fields.Boolean(related='folder_id.visibility_marketing')
    rel_visibility_production = fields.Boolean(related='folder_id.visibility_production')
    rel_visibility_accounting = fields.Boolean(related='folder_id.visibility_accounting')
    rel_visibility_pm = fields.Boolean(related='folder_id.visibility_pm',)
    rel_visibility_hr = fields.Boolean(related='folder_id.visibility_hr',)
    rel_visibility_salesman = fields.Boolean(related='folder_id.visibility_salesman',)
    rel_visibility_everyone = fields.Boolean(related='folder_id.visibility_everyone',)
    version_ids = fields.One2many('document_hub.document.version', 'document_id', string='Versions')

    @api.depends('file_ids', 'file_ids.name')
    def _compute_file_names(self):
        for document in self:
            document.file_names = '\n'.join(document.file_ids.mapped('name'))

    @api.depends('file_ids')
    def _compute_cover_attachment_id(self):
        for document in self:
            document.cover_attachment_id = document.file_ids[:1]

    # Fields the form already treats as readonly once state == 'lock'
    # (see document_hub_document_form_view). Enforced here too: readonly on
    # the form is a UI hint only, not a guarantee against a direct write().
    _LOCKED_PROTECTED_FIELDS = {
        'topic', 'privacy_doc', 'folder_id', 'project_id', 'file_ids',
        'owner_id', 'partner_id', 'company_id', 'description',
    }

    @api.model_create_multi
    def create(self, vals_list):
        auto_tags = None
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (self.env['ir.sequence'].next_by_code('document_hub.document'))
            if not vals.get('tag_ids') and vals.get('topic'):
                if auto_tags is None:
                    auto_tags = self.env['document_hub.tag'].search([('keywords', '!=', False)])
                topic = vals['topic'].lower()
                matched = auto_tags.filtered(
                    lambda tag: any(
                        keyword.strip().lower() in topic
                        for keyword in tag.keywords.split(',')
                        if keyword.strip()
                    )
                )
                if matched:
                    vals['tag_ids'] = [(6, 0, matched.ids)]

        res = super(Document, self.sudo()).create(vals_list)
        return res

    def write(self, vals):
        # self.env.su: skip for trusted system automation (e.g. the sale_offer
        # attachment sync in sale_offer.py, which runs sudo()'d) - locking is
        # meant to stop casual user edits, not break existing integrations.
        if not self.env.su and self._LOCKED_PROTECTED_FIELDS.intersection(vals) \
                and any(document.state == 'lock' for document in self):
            raise UserError(_('You cannot modify a locked document. Unlock it first.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            if any(document.state == 'lock' for document in self):
                raise UserError(_('You cannot delete a locked document. Unlock it first.'))
            if not self.env.user.has_group('base.group_system'):
                raise UserError(_('Only a system administrator can permanently delete documents from the trash.'))
        self.env['document_hub.trash_log'].log_action(self, 'purged')
        return super(Document, self.sudo()).unlink()

    def action_archive(self):
        # "Delete" in the explorer moves a document to the trash (active=False)
        # instead of unlink()'ing it. sudo() here mirrors create(): several
        # department groups only have perm_write=0 on this model in
        # ir.model.access.csv, relying on the row-level ir.rule for what they
        # can see rather than the ACL for what they can write - same
        # already-flagged gap create() works around, applied consistently.
        if not self.env.su and any(document.state == 'lock' for document in self):
            raise UserError(_('You cannot delete a locked document. Unlock it first.'))
        res = super(Document, self.sudo()).action_archive()
        self.env['document_hub.trash_log'].log_action(self, 'deleted')
        return res

    def action_unarchive(self):
        res = super(Document, self.sudo()).action_unarchive()
        self.env['document_hub.trash_log'].log_action(self, 'restored')
        return res

    def _check_management_permission(self):
        # Locking and duplicating are elevated actions: restricted to the
        # director tier (director/manager/administrator, via implied_ids),
        # not the department groups that only get read/write on their own
        # visible documents.
        if not self.env.su and not self.env.user.has_group('document_hub.group_document_hub_document_director'):
            raise UserError(_('You do not have permission to lock, unlock or duplicate documents.'))

    def action_lock_document(self):
        self._check_management_permission()
        self.write({
            'state': 'lock'
        })

    def action_open_document(self):
        self._check_management_permission()
        self.write({
            'state': 'open'
        })

    def copy(self, default=None):
        self._check_management_permission()
        return super().copy(default=default)

    def action_upload_new_version(self, attachment_id):
        # Also used to "restore" an old version: the caller passes that
        # version's attachment_id, which becomes current again while what
        # was current gets snapshotted - same operation either way.
        self.ensure_one()
        if not self.env.su and self.state == 'lock':
            raise UserError(_('You cannot modify a locked document. Unlock it first.'))
        next_version = max(self.sudo().version_ids.mapped('version_number'), default=0) + 1
        version_vals = [{
            'document_id': self.id,
            'attachment_id': attachment.id,
            'version_number': next_version,
        } for attachment in self.file_ids]
        if version_vals:
            self.env['document_hub.document.version'].sudo().create(version_vals)
        self.sudo().write({'file_ids': [(6, 0, [attachment_id])]})

    @api.onchange('owner_id')
    def compute_admin_group(self):
        if self.env.user.has_group('document_hub.group_document_hub_document_administrator'):
            self.is_admin = True
        else:
            self.is_admin = False
            
