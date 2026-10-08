# -*- coding: utf-8 -*-

from odoo import api, fields, models


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

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        projects._create_document_folder()
        return projects

    def _create_document_folder(self):
        """Create the folder of each project under the Project root folder, with the project template subfolders."""
        root_folder = self.env.ref('document_hub.folder_project')
        template_lines = self.env.ref('document_hub.folder_template_project').sudo().line_ids

        for project in self:
            project_folder = self.env['document_hub.folder'].sudo().create({
                'name': project.display_name,
                'parent_folder_id': root_folder.id,
                'company_id': project.company_id.id,
                'is_project': True,
                'project_id': project.id,
            })
            template_lines._create_folders(project_folder)
