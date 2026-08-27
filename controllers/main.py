# -*- coding: utf-8 -*-
import io
import os
import zipfile

from odoo import http
from odoo.http import content_disposition, request


class DocumentHubController(http.Controller):

    @http.route('/document_hub/folder/<int:folder_id>/zip', type='http', auth='user')
    def download_folder_zip(self, folder_id, **kwargs):
        folder = request.env['document_hub.folder'].browse(folder_id)
        folder.check_access_rights('read')
        folder.check_access_rule('read')
        if not folder.exists():
            return request.not_found()

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            self._add_folder_to_zip(archive, folder, '', set())

        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Length', len(buffer.getvalue())),
            ('Content-Disposition', content_disposition(f'{folder.name}.zip')),
        ]
        return request.make_response(buffer.getvalue(), headers)

    def _add_folder_to_zip(self, archive, folder, path, used_paths):
        # documents/attachments are fetched through the current (non-sudo) user
        # environment, so ir.rule keeps applying: a user only ever gets the
        # files they already have access to, folder by folder.
        documents = request.env['document_hub.document'].search([('folder_id', '=', folder.id)])
        for document in documents:
            for attachment in document.file_ids:
                name = attachment.name or 'file'
                base, ext = os.path.splitext(name)
                candidate = f'{path}{name}'
                counter = 1
                while candidate in used_paths:
                    candidate = f'{path}{base}_{counter}{ext}'
                    counter += 1
                used_paths.add(candidate)
                archive.writestr(candidate, attachment.raw or b'')
        for child in folder.children_folder_ids:
            self._add_folder_to_zip(archive, child, f'{path}{child.name}/', used_paths)
