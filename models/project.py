# -*- coding: utf-8 -*-

from odoo import fields, models


class Project(models.Model):
    _inherit = 'project.project'

    doc_count = fields.Integer(string="Document count", compute='compute_document_amount')

    def compute_document_amount(self):
        # Grouped in a single query: the field feeds the project form's smart
        # button, but any batch read (list view, export, another compute) used
        # to raise "Expected singleton" on `self.id` and would otherwise fire
        # one search_count per project.
        counts = {}
        if self.ids:
            groups = self.env['document_hub.document'].read_group(
                [('project_id', 'in', self.ids)], ['project_id'], ['project_id'])
            counts = {group['project_id'][0]: group['project_id_count'] for group in groups}
        for project in self:
            project.doc_count = counts.get(project.id, 0)
