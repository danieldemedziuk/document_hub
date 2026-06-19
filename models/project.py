# -*- coding: utf-8 -*-

from odoo import fields, models


class Project(models.Model):
    _inherit = 'project.project'
    
    doc_count = fields.Integer(string="Document count", compute='compute_document_amount')
    
    def compute_document_amount(self):
        number = self.env['document_hub.document'].search_count([('project_id', '=', self.id)])
        self.doc_count = number or 0
        