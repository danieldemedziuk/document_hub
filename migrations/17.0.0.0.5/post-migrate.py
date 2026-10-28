# -*- coding: utf-8 -*-


def migrate(cr, version):
    # The help of "Authorized persons" now says they may not edit the document.
    # An update keeps the pl_PL text it already had, so it is dropped here and
    # the .po loaded right after this script fills in the new one.
    cr.execute("""
        UPDATE ir_model_fields SET help = jsonb_build_object('en_US', help->>'en_US')
         WHERE model = 'document_hub.document' AND name = 'authorized_user_ids'
    """)
