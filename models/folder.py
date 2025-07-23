# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Folder(models.Model):
    _name = 'document_hub.folder'
    _description = 'Document hub: Folder'
    _rec_name = 'parent_path'

    name = fields.Char(string='Name', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Html(string='Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one('res.company', string='Company', default=lambda lm: lm.env.company)
    parent_folder_id = fields.Many2one('document_hub.folder', string='Parent folder', ondelete='cascade')
    children_folder_ids = fields.One2many('document_hub.folder', 'parent_folder_id', string='Sub folder')
    document_ids = fields.One2many('document_hub.document', 'folder_id', string='Documents')
    parent_path = fields.Char(index=True, unaccent=False, compute='_compute_parent_path', store=True, translate=True)

    visibility_administration = fields.Boolean(string='Administration', default=False)
    visibility_purchasing_and_logistics = fields.Boolean(string='Purchasing and logistics', default=False)
    visibility_marketing = fields.Boolean(string='Marketing', default=False)
    visibility_accounting = fields.Boolean(string='Accounting', default=False)
    visibility_pm = fields.Boolean(string='PM', default=False)
    visibility_hr = fields.Boolean(string='HR', default=False)
    visibility_salesman = fields.Boolean(string='Sales', default=False)
    visibility_everyone = fields.Boolean(string='Everyone', default=False)
    
    is_project = fields.Boolean(string="Is project", default=False, help='Mark this option if you are sure this folder is for projects.')

    @api.depends('parent_folder_id', 'name')
    def _compute_parent_path(self):
        for rec in self:
            name = _(rec.name)
            
            if rec.parent_folder_id:
                parent_folder = _(rec.parent_folder_id.name)
                rec.parent_path = F"{parent_folder}: {name}"
            else:
                rec.parent_path = name

    @api.onchange('visibility_everyone')
    def _change_settings_everyone(self):
        if self.visibility_everyone:
            self.visibility_administration = False
            self.visibility_purchasing_and_logistics = False
            self.visibility_marketing = False
            self.visibility_accounting = False
            self.visibility_pm = False
            self.visibility_hr = False
            self.visibility_salesman = False
