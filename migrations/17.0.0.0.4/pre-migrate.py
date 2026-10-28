# -*- coding: utf-8 -*-
import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)



def migrate(cr, version):
    if column_exists(cr, 'document_hub_document', 'privacy_doc') \
            and not column_exists(cr, 'document_hub_document', 'confidentiality'):
        # privacy_doc ('mail' / 'company') becomes the four-level confidentiality.
        # 'company' was meant for the Manager tier only: now Strictly confidential.
        cr.execute("ALTER TABLE document_hub_document RENAME COLUMN privacy_doc TO confidentiality")
        cr.execute("""
            UPDATE document_hub_document
               SET confidentiality = CASE WHEN confidentiality = 'company' THEN 'strictly_confidential'
                                          ELSE 'internal' END
        """)
        cr.execute("SELECT confidentiality, count(*) FROM document_hub_document GROUP BY 1")
        _logger.info("document_hub: confidentiality levels after migration: %s", dict(cr.fetchall()))

    # The record rules had become noupdate, so later changes to their XML never
    # reached the database: the rules there no longer filtered privacy_doc at
    # all, and every department saw the 'company' documents of its folders.
    # From now on the XML is the source of truth again.
    cr.execute("""
        UPDATE ir_model_data SET noupdate = false
         WHERE module = 'document_hub' AND model = 'ir.rule' AND noupdate
     RETURNING name
    """)
    _logger.info("document_hub: record rules reloaded from XML: %s", [row[0] for row in cr.fetchall()])
