# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Document(models.Model):
    _name = 'document_hub'
    _description = 'Document hub'
    _order = 'id desc'
    _inherit = ['mail.thred', 'mail.activity']
    
    name = fields.Char(string='Name')
    active = fields.Boolean(string="Active", default=True)
    attachment_id = fields.Many2one('ir.attachment', ondelete='cascade', auto_join=True, copy=False)
    attachment_name = fields.Char(string='Attachment name', related='attachment_id.name', readonly=False)
    attachment_type = fields.Selection(string='Attachment Type', related='attachment_id.type', readonly=False)
    file_extension = fields.Char(string='File extension', readonly=False, copy=True, store=True)
    file_size = fields.Integer(related='attachment_id.file_size', store=True)
    file_type = fields.Selection([('url', 'URL'), ('binary', 'File'), ('empty', 'Request')], string='Type', required=True, store=True, default='empty', change_default=True)
    file_description = fields.Text(string='Description', related='attachment_id.description', readonly=False)
    tag_ids = fields.Many2many('document_hub.tag', string="Tags", copy=False)
    partner_id = fields.Many2one('res.partner', string="Contact", tracking=True)
    owner_id = fields.Many2one('res.users', string="Owner", default=lambda lm: lm.env.user.id, tracking=True)
    folder_id = fields.Many2one('documents.folder', string="Workspace", ondelete="restrict", tracking=True, required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
    
    _sql_constraints = [
        ('attachment_unique', 'unique (attachment_id)', "This attachment is already in the database!"),
    ]
    