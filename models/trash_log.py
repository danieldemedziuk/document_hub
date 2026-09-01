# -*- coding: utf-8 -*-

from odoo import fields, models


class TrashLog(models.Model):
    _name = 'document_hub.trash_log'
    _description = 'Document hub: Trash activity log'
    _order = 'create_date desc'

    action = fields.Selection([
        ('deleted', 'Moved to trash'),
        ('restored', 'Restored from trash'),
        ('purged', 'Permanently deleted'),
    ], required=True)
    res_model = fields.Selection([
        ('document_hub.document', 'Document'),
        ('document_hub.folder', 'Folder'),
    ], required=True)
    res_name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)

    def log_action(self, records, action):
        """Snapshot-log a trash action for a recordset of document_hub.document
        or document_hub.folder records. Deliberately not linked to the
        original record by id: a "purged" entry must still make sense after
        that record no longer exists.
        """
        name_field = 'topic' if records._name == 'document_hub.document' else 'name'
        vals_list = [{
            'action': action,
            'res_model': records._name,
            'res_name': record[name_field],
            'user_id': self.env.uid,
        } for record in records]
        if vals_list:
            self.sudo().create(vals_list)
