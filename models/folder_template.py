from odoo import fields, models


class FolderTemplate(models.Model):
    _name = 'document_hub.folder.template'
    _description = 'Document hub: Folder template'

    name = fields.Char(string='Name', required=True, translate=True)
    line_ids = fields.One2many('document_hub.folder.template.line', 'template_id', string='Subfolders',
                               help='Subfolders created from this template, in this order.')
