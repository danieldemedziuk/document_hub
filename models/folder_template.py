from odoo import fields, models


class FolderTemplate(models.Model):
    _name = 'document_hub.folder.template'
    _description = 'Document hub: Folder template'

    name = fields.Char(string='Name', required=True, translate=True)
    line_ids = fields.One2many('document_hub.folder.template.line', 'template_id', string='Subfolders',
                               help='Subfolders created from this template, in this order.')

    def _create_subfolders(self, parent_folder):
        """Create a subfolder of parent_folder for every template line"""
        self.ensure_one()
        
        subfolders = self.env['document_hub.folder'].create([{
            'name': line.name,
            'sequence': line.sequence,
            'parent_folder_id': parent_folder.id,
            'company_id': parent_folder.company_id.id,
            'is_project': parent_folder.is_project,
            'template_line_id': line.id,
        } for line in self.line_ids])

        langs = ['en_US'] + [code for code, _lang_name in self.env['res.lang'].get_installed()]
        for line, subfolder in zip(self.line_ids, subfolders):
            subfolder.update_field_translations('name', {lang: line.with_context(lang=lang).name for lang in langs})

        return subfolders
