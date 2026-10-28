# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DocumentVersion(models.Model):
    _name = 'document_hub.document.version'
    _description = 'Document hub: Document version history'
    _order = 'version_number desc'

    document_id = fields.Many2one(
        'document_hub.document', string='Document', required=True, ondelete='cascade', index=True)
    attachment_id = fields.Many2one('ir.attachment', string='File', required=True, ondelete='restrict')
    version_number = fields.Integer(string='Version')
    file_size = fields.Integer(related='attachment_id.file_size', store=True, string='File size')
    # Used by the record rule: an old version is exactly as secret as its
    # document, so the rule asks the document's own rules instead of keeping
    # a copy of them here.
    is_document_readable = fields.Boolean(
        compute='_compute_is_document_readable', search='_search_is_document_readable')

    @api.depends_context('uid')
    def _compute_is_document_readable(self):
        readable = self.document_id.with_user(self.env.uid)._filter_access_rules('read')
        for version in self:
            version.is_document_readable = version.document_id in readable

    def _search_is_document_readable(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError()
        # with_user: record rules are evaluated as superuser, the documents
        # must be filtered as the user the rule is computed for.
        Document = self.env['document_hub.document'].with_user(self.env.uid).with_context(active_test=False)
        if Document.check_access_rights('read', raise_exception=False):
            readable = Document._search([])
        else:
            readable = []
        positive = (operator == '=') == value
        return [('document_id', 'in' if positive else 'not in', readable)]
