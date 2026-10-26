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
 * for state.folders instead of each maintaining their own copy. Expansion
 * state lives there too, so "collapse/expand all" can reach every node.
 */
export class DocumentHubFolderTreeNode extends Component {
    static template = "document_hub.FolderTreeNode";
    static props = {
        folder: Object,
        childrenByParent: Object,
        selectedFolderId: [Number, Boolean],
        renamingId: [Number, Boolean],
        canCreateFolders: Boolean,
        collapsedIds: Set,
        onToggleExpand: Function,
        matchIds: Set,
        documentCounts: Object,
        onFolderDragStart: Function,
        onFolderDragEnd: Function,
        onDropFolder: Function,
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
        this.state = useState({ isDragOver: false });
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

    get isExpanded() {
        return !this.props.collapsedIds.has(this.props.folder.id);
    }

    get isMatch() {
        return this.props.matchIds.has(this.props.folder.id);
    }

    get documentCount() {
        return this.props.documentCounts[this.props.folder.id] || 0;
    }

    get isRenaming() {
        return this.props.renamingId === this.props.folder.id;
    }

    toggleExpand(ev) {
        ev.stopPropagation();
        this.props.onToggleExpand(this.props.folder.id);
    }

    _isInternalDrag(ev) {
        const types = ev.dataTransfer.types;
        return types.includes("application/x-document-hub-ids") || types.includes("application/x-document-hub-folder");
    }

    onDragEnter(ev) {
        if (this._isInternalDrag(ev)) {
            this.state.isDragOver = true;
        }
    }

    onDragLeave(ev) {
        // dragleave also fires when moving onto a child element of the row.
        if (!ev.currentTarget.contains(ev.relatedTarget)) {
            this.state.isDragOver = false;
        }
    }

    onDrop(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.isDragOver = false;
        if (ev.dataTransfer.types.includes("application/x-document-hub-folder")) {
            this.props.onDropFolder(this.props.folder.id);
        } else if (ev.dataTransfer.types.includes("application/x-document-hub-ids")) {
            this.props.onDropDocuments(this.props.folder.id);
        }
    }
}
DocumentHubFolderTreeNode.components = {
    DocumentHubFolderTreeNode,
    Dropdown,
    DropdownItem,
};
