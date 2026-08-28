# -*- coding: utf-8 -*-

from odoo import fields, models


class DocumentVersion(models.Model):
    _name = 'document_hub.document.version'
    _description = 'Document hub: Document version history'
    _order = 'version_number desc'

    document_id = fields.Many2one(
        'document_hub.document', string='Document', required=True, ondelete='cascade', index=True)
    attachment_id = fields.Many2one('ir.attachment', string='File', required=True, ondelete='restrict')
    version_number = fields.Integer(string='Version')
