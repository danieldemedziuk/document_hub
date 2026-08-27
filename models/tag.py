# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Tag(models.Model):
    _name = 'document_hub.tag'
    _description = 'Document hub: Tag'
    
    name = fields.Char(string='Name', required=True, tracking=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    keywords = fields.Char(
        string='Keywords', tracking=True,
        help='Comma-separated keywords. When a new document is created without an explicit '
             'tag, its topic/filename is matched (case-insensitively) against these keywords '
             'to apply this tag automatically.',
    )

    