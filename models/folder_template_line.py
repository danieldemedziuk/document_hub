from odoo import fields, models


class FolderTemplateLine(models.Model):
    _name = 'document_hub.folder.template.line'
    _description = 'Document hub: Folder template line'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'document_hub.folder.template', string='Template', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Name', required=True, translate=True)
