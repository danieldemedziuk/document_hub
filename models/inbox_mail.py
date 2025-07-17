# -*- coding: utf-8 -*-
import imaplib
import email
import ssl
import base64
from email.header import decode_header
from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class InboxMail(models.Model):
    _inherit = 'document_hub.document'

    def check_mailbox(self):
        try:
            # technical condition for localhost
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if base_url and 'localhost' in base_url:
                return
            
            ICPSudo = self.env['ir.config_parameter'].sudo()
            imap_active = ICPSudo.get_param('document_hub.active', default='False') == 'True'
            if not imap_active:
                _logger.info("IMAP check skipped: not active.")
                return

            imap_host = ICPSudo.get_param('document_hub.imap_host')
            imap_port = int(ICPSudo.get_param('document_hub.imap_port', default=993))
            imap_user = ICPSudo.get_param('document_hub.imap_user')
            imap_password = ICPSudo.get_param('document_hub.imap_password')
            imap_folder_id = ICPSudo.get_param('document_hub.imap_folder')

            folder = self.env['document_hub.folder'].browse(int(imap_folder_id)) if imap_folder_id else False

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=context) as mail:
                mail.login(imap_user, imap_password)
                mail.select("INBOX")

                status, messages = mail.search(None, 'UNSEEN')
                if status != 'OK':
                    _logger.warning("No unseen emails found.")
                    return

                for num in messages[0].split():
                    res, msg_data = mail.fetch(num, '(RFC822)')
                    if res != 'OK' or not msg_data or not msg_data[0]:
                        _logger.warning(f"Failed to fetch message {num}")
                        continue

                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = self._decode_header(msg.get('Subject'))
                    sender = msg.get('From')
                    
                    for part in msg.walk():
                        # content_type = part.get_content_type()
                        content_disposition = part.get("Content-Disposition", "")

                        # if content_type == "text/plain" and not content_disposition:
                        #     payload = part.get_payload(decode=True)
                        #     charset = part.get_content_charset() or 'utf-8'
                        #     try:
                        #         message = payload.decode(charset, errors='replace').strip()
                        #     except Exception as e:
                        #         _logger.warning(f"Failed to decode message body: {e}")
                        #         message = ''
                        
                        # elif "attachment" in content_disposition.lower():
                        
                        if "attachment" in content_disposition.lower():
                            filename = self._decode_header(part.get_filename())
                            payload = part.get_payload(decode=True)
                            
                            if filename and payload:
                                attachment = self.env['ir.attachment'].create({
                                    'name': filename,
                                    'type': 'binary',
                                    'datas': base64.b64encode(payload),
                                    'res_model': 'document_hub.document',
                                    'res_id': 0,
                                })

                                document = self.env['document_hub.document'].create({
                                    'topic': subject,
                                    'description': _("Email from: <b>%s</b>, Subject: <b>%s</b>") % (sender, subject),
                                    'folder_id': folder.id if folder else False,
                                    'file_ids': [(6, 0, [attachment.id])],
                                    'tag_ids': [(6, 0, [self.env.ref('document_hub.tag_email').id])],
                                })

                                attachment.write({
                                    'res_id': document.id
                                })
                                _logger.info("Document created!")

                    mail.store(num, '+FLAGS', '\\Seen')

        except Exception as e:
            _logger.exception(f"IMAP fetch failed: {e}")

    def _decode_header(self, value):
        if not value:
            return ''
        decoded = decode_header(value)
        return ''.join([
            fragment.decode(
                encoding or 'utf-8') if isinstance(fragment, bytes) else fragment
            for fragment, encoding in decoded
        ])
