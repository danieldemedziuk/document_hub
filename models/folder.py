# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Folder(models.Model):
    _name = 'document_hub.folder'
    _description = 'Document hub: Folder'
    _rec_name = 'parent_path'

    name = fields.Char(string='Name', required=True, translation=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Html(string='Description')
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda lm: lm.env.company)
    parent_folder_id = fields.Many2one(
        'document_hub.folder', string='Parent folder', ondelete='cascade')
    children_folder_ids = fields.One2many(
        'document_hub.folder', 'parent_folder_id', string='Sub folder')
    document_ids = fields.One2many(
        'document_hub.document', 'folder_id', string='Documents')
    parent_path = fields.Char(
        index=True, unaccent=False, compute='_compute_parent_path')

    visibility_administration = fields.Boolean(
        string='Administration', default=False)
    visibility_purchasing_and_logistics = fields.Boolean(
        string='Purchasing and logistics', default=False)
    visibility_marketing = fields.Boolean(string='Marketing', default=False)
    visibility_accounting = fields.Boolean(string='Accounting', default=False)
    visibility_pm = fields.Boolean(string='PM', default=False)
    visibility_hr = fields.Boolean(string='HR', default=False)
    is_project = fields.Boolean(string="Is project", default=False,
                                help='Mark this option if you are sure this folder is for projects.')

    @api.depends('parent_folder_id', 'name')
    def _compute_parent_path(self):
        print('COMPUTE PARENT PATH')
        for rec in self:
            if rec.parent_folder_id:
                print('1')
                rec.parent_path = f"{rec.parent_folder_id.name} > {rec.name}"
            else:
                print('2')
                rec.parent_path = rec.name

            print("PARENT PATH", rec.parent_path)
