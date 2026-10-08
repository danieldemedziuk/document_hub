# -*- coding: utf-8 -*-
from odoo import api, models


class IrAttachment(models.Model):
    """A file of a document is readable by whoever may read the document.

    Files synced from offers or HR document flows stay bound to their source
    record, which the reader of the document may not see. The document's own
    rules (privacy, company) still decide who reads it.
    """
    _inherit = 'ir.attachment'

    def _document_hub_readable(self, ids):
        """The given attachment ids that belong to a document the user may read."""
        Document = self.env['document_hub.document']
        if not ids or not Document.check_access_rights('read', raise_exception=False):
            return set()
        Document.flush_model(['file_ids'])
        self.env.cr.execute("""
            SELECT ir_attachment_id, document_hub_document_id
              FROM document_hub_document_ir_attachment_rel
             WHERE ir_attachment_id IN %s
        """, [tuple(ids)])
        rows = self.env.cr.fetchall()
        if not rows:
            return set()
        readable = set(Document.browse({doc for _att, doc in rows})._filter_access_rules('read').ids)
        return {att for att, doc in rows if doc in readable}

    @api.model
    def check(self, mode, values=None):
        if mode != 'read' or not self or self.env.is_superuser():
            return super().check(mode, values)
        granted = self._document_hub_readable(self.ids)
        return super(IrAttachment, self - self.browse(granted)).check(mode, values)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        query = super()._search(domain, offset, limit, order, access_rights_uid)
        # Only the lookup by ids - how the document's file field and
        # /web/content read files - is widened; listings are left as they are.
        if self.env.su or len(domain) != 1 or tuple(domain[0][:2]) != ('id', 'in'):
            return query
        wanted = [id_ for id_ in domain[0][2] if isinstance(id_, int)]
        found = list(query)
        missing = set(wanted) - set(found)
        granted = self._document_hub_readable(list(missing))
        if not granted:
            return query
        return self.browse(found + [id_ for id_ in wanted if id_ in granted])._as_query(order)
