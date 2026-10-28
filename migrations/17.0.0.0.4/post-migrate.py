# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # A folder that only ever held 'company' documents keeps filing new ones as
    # Strictly confidential; every other folder starts at Internal (the old default).
    cr.execute("""
        UPDATE document_hub_folder folder
           SET default_confidentiality = 'strictly_confidential'
         WHERE EXISTS (SELECT 1 FROM document_hub_document d WHERE d.folder_id = folder.id)
           AND NOT EXISTS (SELECT 1 FROM document_hub_document d
                            WHERE d.folder_id = folder.id AND d.confidentiality != 'strictly_confidential')
     RETURNING id
    """)
    _logger.info("document_hub: folders defaulting to Strictly confidential: %s", [row[0] for row in cr.fetchall()])

    # "Mail" became "Documents": an update keeps the old pl_PL ("Korespondencja"),
    # so the translations are dropped here and the .po loaded right after refills them.
    for table, xmlid in (('ir_ui_menu', 'menu_document_hub_mail_documents'),
                         ('ir_act_window', 'document_hub_mail_document_act')):
        cr.execute(f"""
            UPDATE {table} SET name = jsonb_build_object('en_US', name->>'en_US')
             WHERE id = (SELECT res_id FROM ir_model_data WHERE module = 'document_hub' AND name = %s)
        """, [xmlid])
