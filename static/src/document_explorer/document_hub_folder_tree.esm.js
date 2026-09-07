/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * One node of the folder tree in the document explorer sidebar. Recursive:
 * a node renders its own children as more DocumentHubFolderTreeNode instances.
 *
 * Folder mutations (rename, download, create subfolder) are not implemented
 * here: they're delegated to the parent DocumentHubKanbanRenderer via props,
 * so the tree and the main-area subfolder tiles share one source of truth
 * for state.folders instead of each maintaining their own copy.
 */
export class DocumentHubFolderTreeNode extends Component {
    static template = "document_hub.FolderTreeNode";
    static props = {
        folder: Object,
        childrenByParent: Object,
        selectedFolderId: [Number, Boolean],
        renamingId: [Number, Boolean],
        canCreateFolders: Boolean,
        onSelect: Function,
        onRenameStart: Function,
        onRenameKeydown: Function,
        onRenameCommit: Function,
        onDownload: Function,
        onCreateSubfolder: Function,
        onDelete: Function,
        onDropDocuments: Function,
    };

    setup() {
        this.state = useState({ expanded: true });
        this.renameLabel = _t("Rename");
        this.downloadLabel = _t("Download");
        this.newFolderLabel = _t("New folder");
        this.deleteLabel = _t("Delete");
    }

    get children() {
        return this.props.childrenByParent.get(this.props.folder.id) || [];
    }

    get isSelected() {
        return this.props.selectedFolderId === this.props.folder.id;
    }

    get isRenaming() {
        return this.props.renamingId === this.props.folder.id;
    }

    toggleExpand(ev) {
        ev.stopPropagation();
        this.state.expanded = !this.state.expanded;
    }

    onDrop(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (ev.dataTransfer.types.includes("application/x-document-hub-ids")) {
            this.props.onDropDocuments(this.props.folder.id);
        }
    }
}
DocumentHubFolderTreeNode.components = {
    DocumentHubFolderTreeNode,
    Dropdown,
    DropdownItem,
};
