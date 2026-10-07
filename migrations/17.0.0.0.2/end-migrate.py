import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create the folders of active projects and move their documents there."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_project_folders(env)
    _move_documents_to_project_folders(env)


def _create_project_folders(env):
    """Create the folder of every active project."""
    projects = env['project.project'].search([])
    projects._create_document_folder()

    _logger.info('Created the document folders of %s projects.', len(projects))


def _move_documents_to_project_folders(env):
    """Move every document of an active project, archived ones too, from the Project root tree to its project folder."""
    Folder = env['document_hub.folder'].with_context(active_test=False)

    project_folders = Folder.search([('project_id', '!=', False)])
    project_folder_trees = Folder.search([('id', 'child_of', project_folders.ids)])
    source_folders = Folder.search([('id', 'child_of', env.ref('document_hub.folder_project').id)]) - project_folder_trees

    documents = env['document_hub.document'].with_context(active_test=False).search([
        ('folder_id', 'in', source_folders.ids),
        ('project_id.active', '=', True),
    ])

    folder_by_project = {folder.project_id: folder for folder in project_folders}
    for project, project_documents in documents.grouped('project_id').items():
        project_documents.write({'folder_id': folder_by_project[project].id})
        
    _logger.info('Moved %s documents to the folders of their projects.', len(documents))
