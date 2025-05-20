# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    imap_host = fields.Char(string='SMTP Host')
    imap_port = fields.Integer(string='SMTP Port', default=465)

    imap_user = fields.Char(string='SMTP User')
    imap_password = fields.Char(string='SMTP Password')
    imap_sender = fields.Char(string='SMTP Sender')

    imap_folder = fields.Many2one('document_hub.folder', default=lambda self: self.ref(''))
    active = fields.Boolean(default=True)
    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('mj_settings.smtp_mj_host', self.smtp_mj_host)
        self.env['ir.config_parameter'].set_param('mj_settings.smtp_mj_port', self.smtp_mj_port)

        self.env['ir.config_parameter'].set_param('mj_settings.smtp_mj_user', self.smtp_mj_user)
        self.env['ir.config_parameter'].set_param('mj_settings.smtp_mj_pwd', self.smtp_mj_pwd)
        self.env['ir.config_parameter'].set_param('mj_settings.smtp_mj_sender', self.smtp_mj_sender)

        self.env['ir.config_parameter'].set_param('mj_settings.smtp_recruitment_user', self.smtp_recruitment_user)
        self.env['ir.config_parameter'].set_param('mj_settings.smtp_recruitment_pwd', self.smtp_recruitment_pwd)
        self.env['ir.config_parameter'].set_param('mj_settings.smtp_recruitment_sender', self.smtp_recruitment_sender)

        self.env['ir.config_parameter'].set_param('mj_settings.erp_server', self.erp_server)
        self.env['ir.config_parameter'].set_param('mj_settings.erp_db', self.erp_db)
        self.env['ir.config_parameter'].set_param('mj_settings.erp_user', self.erp_user)
        self.env['ir.config_parameter'].set_param('mj_settings.erp_pwd', self.erp_pwd)

        self.env['ir.config_parameter'].set_param('mj_settings.prod_serv_host', self.prod_serv_host)
        self.env['ir.config_parameter'].set_param('mj_settings.prod_serv_port', self.prod_serv_port)
        self.env['ir.config_parameter'].set_param('mj_settings.prod_serv_db', self.prod_serv_db)
        self.env['ir.config_parameter'].set_param('mj_settings.prod_serv_user', self.prod_serv_user)
        self.env['ir.config_parameter'].set_param('mj_settings.prod_serv_pwd', self.prod_serv_pwd)

        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        smtp_host = ICPSudo.get_param('mj_settings.smtp_mj_host', False)
        smtp_port = ICPSudo.get_param('mj_settings.smtp_mj_port', default=0)

        smtp_usr = ICPSudo.get_param('mj_settings.smtp_mj_user', False)
        smtp_pwd = ICPSudo.get_param('mj_settings.smtp_mj_pwd', False)
        smtp_sender = ICPSudo.get_param('mj_settings.smtp_mj_sender', False)

        smtp_rec_usr = ICPSudo.get_param('mj_settings.smtp_recruitment_user', False)
        smtp_rec_pwd = ICPSudo.get_param('mj_settings.smtp_recruitment_pwd', False)
        smtp_rec_sender = ICPSudo.get_param('mj_settings.smtp_recruitment_sender', False)

        erp_server = ICPSudo.get_param('mj_settings.erp_server', False)
        erp_db = ICPSudo.get_param('mj_settings.erp_db', False)
        erp_user = ICPSudo.get_param('mj_settings.erp_user', False)
        erp_pwd = ICPSudo.get_param('mj_settings.erp_pwd', False)

        prod_serv_host = ICPSudo.get_param('mj_settings.prod_serv_host', False)
        prod_serv_port = ICPSudo.get_param('mj_settings.prod_serv_port', False)
        prod_serv_db = ICPSudo.get_param('mj_settings.prod_serv_db', False)
        prod_serv_user = ICPSudo.get_param('mj_settings.prod_serv_user', False)
        prod_serv_pwd = ICPSudo.get_param('mj_settings.prod_serv_pwd', False)

        res.update(
            smtp_mj_host=smtp_host,
            smtp_mj_port=int(smtp_port),
            smtp_mj_user=smtp_usr,
            smtp_mj_pwd=smtp_pwd,
            smtp_mj_sender=smtp_sender,

            smtp_recruitment_user=smtp_rec_usr,
            smtp_recruitment_pwd=smtp_rec_pwd,
            smtp_recruitment_sender=smtp_rec_sender,

            erp_server=erp_server,
            erp_db=erp_db,
            erp_user=erp_user,
            erp_pwd=erp_pwd,

            prod_serv_host=prod_serv_host,
            prod_serv_port=prod_serv_port,
            prod_serv_db=prod_serv_db,
            prod_serv_user=prod_serv_user,
            prod_serv_pwd=prod_serv_pwd,
        )

        return res

