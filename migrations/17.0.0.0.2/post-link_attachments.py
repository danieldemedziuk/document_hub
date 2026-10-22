# -*- coding: utf-8 -*-
"""Bind the files uploaded before their record was saved to that record.

Without a res_id only the uploader can open such a file (and files left on
ir.ui.view were still public); it went unnoticed while every attachment was
public. A file shared by several records goes to the oldest one.
"""
import logging

_logger = logging.getLogger(__name__)

FIELDS = [('document_hub.document', 'document_hub_document_ir_attachment_rel', 'document_hub_document_id')]


def migrate(cr, version):
    for model, table, owner in FIELDS:
        cr.execute(f"""
            UPDATE ir_attachment a
               SET res_model = %(model)s, res_id = r.owner_id, public = FALSE
              FROM (SELECT ir_attachment_id, MIN({owner}) AS owner_id
                      FROM {table}
                     GROUP BY ir_attachment_id) r
             WHERE a.id = r.ir_attachment_id
               AND COALESCE(a.res_id, 0) = 0
               AND COALESCE(a.res_model, %(model)s) IN (%(model)s, 'ir.ui.view')
               AND a.res_field IS NULL
        """, {'model': model})
        _logger.info("%s: %s attachments bound to their record", model, cr.rowcount)
