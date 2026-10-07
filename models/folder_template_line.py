from odoo import fields, models


class FolderTemplateLine(models.Model):
    _name = 'document_hub.folder.template.line'
    _description = 'Document hub: Folder template line'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'document_hub.folder.template', string='Template', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Name', required=True, translate=True)

    def _create_folders(self, parent_folder):
        """Create a subfolder of parent_folder for every line."""
        folders = self.env['document_hub.folder'].create([{
            'name': line.name,
            'sequence': line.sequence,
            'parent_folder_id': parent_folder.id,
            'company_id': parent_folder.company_id.id,
            'is_project': parent_folder.is_project,
            'template_line_id': line.id,
        } for line in self])

        langs = ['en_US'] + [code for code, _lang_name in self.env['res.lang'].get_installed()]
        for line, folder in zip(self, folders):
            folder.update_field_translations('name', {lang: line.with_context(lang=lang).name for lang in langs})

        return folders
