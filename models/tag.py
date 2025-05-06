# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Tag(models.Model):
    _name = 'document_hub.tag'
    _description = 'Document hub: Tag'
    
    name = fields.Char(string='Name', required=True, tracking=True, translation=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    