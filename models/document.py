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
    
    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active', default=True)
    file_ids = fields.Many2many('ir.attachment', string='Attachments', required=True)
    description = fields.Html(string='Description')
    tag_ids = fields.Many2many('document_hub.tag', string='Tags', copy=False)
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    owner_id = fields.Many2one('res.users', string='Owner', default=lambda lm: lm.env.user.id, tracking=True)
    folder_id = fields.Many2one('document_hub.folder', string='Folder', ondelete='restrict', tracking=True, required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
        
    