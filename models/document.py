# -*- coding: utf-8 -*-
import logging
import base64

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Document(models.Model):
    _name = 'document_hub.document'
    _description = 'Document hub: Document'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    file_ids = fields.Many2many('ir.attachment', string='Attachments', required=True)
    description = fields.Html(string='Description', tracking=True)
    tag_ids = fields.Many2many('document_hub.tag', string='Tags', copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    owner_id = fields.Many2one('res.users', string='Owner', default=lambda lm: lm.env.user.id, tracking=True)
    folder_id = fields.Many2one('document_hub.folder', string='Folder', ondelete='restrict', tracking=True, required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
    state = fields.Selection([('open', 'Open'), ('lock', 'Locked')], string='State', default='open', tracking=True, copy=False)
    privacy_doc = fields.Selection([('company', 'Company'), ('mail', 'Mail')], string='Privacy', default='mail', copy=True)
    rel_is_project = fields.Boolean(related='folder_id.is_project')
    rel_is_parent_folder_project = fields.Boolean(related='folder_id.parent_folder_id.is_project')
    
    rel_visibility_administration = fields.Boolean(related='folder_id.visibility_administration')
    rel_visibility_purchasing_and_logistics = fields.Boolean(related='folder_id.visibility_purchasing_and_logistics')
    rel_visibility_marketing = fields.Boolean(related='folder_id.visibility_marketing')
    rel_visibility_accounting = fields.Boolean(related='folder_id.visibility_accounting')
    rel_visibility_pm = fields.Boolean(related='folder_id.visibility_pm',)
    rel_visibility_hr = fields.Boolean(related='folder_id.visibility_hr',)
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(Document, self.sudo()).create(vals_list)
        return res
    
    
    def action_lock_document(self):
        self.state = 'lock'
        
    def action_open_document(self):
        self.state = 'open'
        
        