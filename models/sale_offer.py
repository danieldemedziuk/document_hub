# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import ValidationError


class SaleOffer(models.Model):
    _inherit = 'sale_offer'
    
    def sync_attachments_to_document_hub(self):
        self.ensure_one()
        
        Document = self.env['document_hub.document']

        doc = Document.sudo().search([('topic', '=', self.name)], limit=1)
        offer_attachment_ids = self.attachment_ids.ids
        inbox_folder_id = self.env.ref('document_hub.folder_administration_inbox')
        project_folder_id = self.env.ref('document_hub.folder_project')
        
        if not doc:
            if self.project_id:
                Document.sudo().create({
                    'topic': self.name,
                    'folder_id': project_folder_id.id,
                    'project_id': self.project_id.id,
                    'file_ids': [(6, 0, offer_attachment_ids)],
                })
                return
            else:
                Document.sudo().create({
                    'topic': self.name,
                    'folder_id': inbox_folder_id.id,
                    'file_ids': [(6, 0, offer_attachment_ids)],
                })
                return

        doc_attachment_ids = doc.file_ids.ids
        attachments_to_add = list(set(offer_attachment_ids) - set(doc_attachment_ids))

        if attachments_to_add:
            doc.write({
                'file_ids': [(4, att_id) for att_id in attachments_to_add],
            })
    
    def unplug_attachment(self):
        self.ensure_one()
        
        Document = self.env['document_hub.document']
        doc = Document.sudo().search([('topic', '=', self.name)], limit=1)
        
        if doc:
            doc.sudo().write({
                'file_ids': [(5, 0, 0)],
            })
            
    def action_mark_to_implement(self):
        super(SaleOffer, self).action_mark_to_implement()
        self.sync_attachments_to_document_hub()
    
    def action_draft(self):
        super(SaleOffer, self).action_draft()
        self.unplug_attachment()
        
    