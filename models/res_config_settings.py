# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    imap_active = fields.Boolean(default=False)
    imap_host = fields.Char(string='Host')
    imap_port = fields.Integer(string='Port', default=465)
    imap_user = fields.Char(string='User')
    imap_password = fields.Char(string='Password')
    imap_folder = fields.Many2one('document_hub.folder', string="Folder", default=lambda lm: lm.env.ref('document_hub.folder_administration_inbox'))
    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('document_hub.active', self.imap_active)
        
        if not self.imap_active:
            self.env['ir.config_parameter'].set_param('document_hub.imap_host', False)
            self.env['ir.config_parameter'].set_param('document_hub.imap_port', 0)
            self.env['ir.config_parameter'].set_param('document_hub.imap_user', False)
            self.env['ir.config_parameter'].set_param('document_hub.imap_password', False)
            self.env['ir.config_parameter'].set_param('document_hub.imap_folder', False)
        else:  
            self.env['ir.config_parameter'].set_param('document_hub.imap_host', self.imap_host)
            self.env['ir.config_parameter'].set_param('document_hub.imap_port', self.imap_port)
            self.env['ir.config_parameter'].set_param('document_hub.imap_user', self.imap_user)
            self.env['ir.config_parameter'].set_param('document_hub.imap_password', self.imap_password)
            self.env['ir.config_parameter'].set_param('document_hub.imap_folder', self.imap_folder.id if self.imap_folder else '')

        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        imap_active = ICPSudo.get_param('document_hub.active', False)
        imap_host = ICPSudo.get_param('document_hub.imap_host', False)
        imap_port = ICPSudo.get_param('document_hub.imap_port', default=0)
        imap_user = ICPSudo.get_param('document_hub.imap_user', False)
        imap_password = ICPSudo.get_param('document_hub.imap_password', False)
        imap_folder_id_raw  = ICPSudo.get_param('document_hub.imap_folder', False)

        try:
            imap_folder_id = int(imap_folder_id_raw)
        except (ValueError, TypeError):
            imap_folder_id = False
        
        res.update(
            imap_active=bool(imap_active),
            imap_host=imap_host,
            imap_port=int(imap_port) if imap_port else 0,
            imap_user=imap_user,
            imap_password=imap_password,
            imap_folder=self.env['document_hub.folder'].browse(imap_folder_id) if imap_folder_id else False,
        )

        return res
