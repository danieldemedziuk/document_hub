/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { checkFileSize } from "@web/core/utils/files";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { FileModel } from "@web/core/file_viewer/file_model";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ConfirmationDialog, deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { DocumentHubFolderTreeNode } from "./document_hub_folder_tree.esm";
import { DocumentHubVersionDialog } from "./document_hub_version_dialog.esm";
import { DocumentHubPdfThumbnail } from "./document_hub_pdf_thumbnail.esm";
import { DocumentHubVideoThumbnail } from "./document_hub_video_thumbnail.esm";
import { DocumentHubFolderPickerDialog } from "./document_hub_folder_picker_dialog.esm";
import { DocumentHubConfirmPurgeDialog } from "./document_hub_confirm_purge_dialog.esm";

/**
 * Windows-Explorer-style layout for document_hub.document: a folder tree on
 * the left, and in the main area a breadcrumb + the direct subfolders of the
 * selected folder as tiles, followed by its direct documents. Clicking a
 * document previews/downloads the underlying file directly; the form view is
 * only reached through the "Details" menu entry.
 *
 * This renders its own document tiles via a direct orm.searchRead call rather
 * than delegating to the stock KanbanRenderer/RelationalModel. That was tried
 * first, but the stock Controller already reloads props.list on every
 * searchModel change via its own onWillUpdateProps hook (see
 * @web/model/model.js), independently of anything this component does. Two
 * independent callers loading the same datapoint on the same event is a race:
 * whichever load() is *initiated* last wins (KeepLast discards the other),
 * and there is no reliable way from a child Renderer to guarantee its call
 * always comes after the stock one. Fetching and rendering documents
 * directly here avoids sharing that datapoint entirely, so there is nothing
 * to race with.
 */
export class DocumentHubKanbanRenderer extends Component {
    static template = "document_hub.DocumentHubKanbanRenderer";
    static components = { DocumentHubFolderTreeNode, Dropdown, DropdownItem, DocumentHubPdfThumbnail, DocumentHubVideoThumbnail };
    static props = ["archInfo", "list", "Compiler?", "deleteRecord", "openRecord", "readonly", "evalViewModifier",
        "forceGlobalClick?", "noContentHelp?", "scrollTop?", "canQuickCreate?",
        "quickCreateState?", "progressBarState?"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.http = useService("http");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.user = useService("user");
        this.fileViewer = useFileViewer();
        this.fileInputRef = useRef("fileInput");
        this.versionFileInputRef = useRef("versionFileInput");

        this.uploadFileLabel = _t("Upload file");
        this.uploadNewVersionLabel = _t("Upload new version");
        this.versionHistoryLabel = _t("Version history");
        this.uploadFailedLabel = _t("Upload failed.");
        this.newDocumentBlankLabel = _t("Create blank document");
        this.newDocumentDialogTitle = _t("New document");
        this.emptyFolderLabel = _t("This folder is empty.");
        this.emptyTrashLabel = _t("Trash is empty.");
        this.renameLabel = _t("Rename");
        this.duplicateLabel = _t("Duplicate");
        this.lockLabel = _t("Lock");
        this.unlockLabel = _t("Unlock");
        this.deleteLabel = _t("Delete");
        this.restoreLabel = _t("Restore");
        this.deletePermanentlyLabel = _t("Delete permanently");
        this.detailsLabel = _t("Details");
        this.trashLabel = _t("Trash");
        this.deleteFolderTitle = _t("Delete folder");
        this.deleteDocumentTitle = _t("Delete document");
        this.newFolderDefaultName = _t("New folder");
        this.addFolderLabel = _t("Add folder");
        this.moveToFolderLabel = _t("Move to folder…");
        this.cancelSelectionLabel = _t("Cancel selection");
        this.selectAllLabel = _t("Select all");
        this.deselectAllLabel = _t("Deselect all");
        this.purgeKeyword = _t("DELETE");
        this.lockedMoveSkippedLabel = _t("Locked documents were skipped - unlock them first to move them.");

        this.lastClickedId = null;
        this.state = useState({
            folders: [],
            tagsById: {},
            selectedFolderId: false,
            isTrashView: false,
            documents: [],
            renaming: null,
            isDraggingOver: false,
            canManageDocuments: false,
            canCreateFolders: false,
            isSystemAdmin: false,
            trashedFolders: [],
            selectedIds: new Set(),
            dragOverFolderId: false,
        });
        onWillStart(async () => {
            await this.loadFolders();
            // An action can open the explorer straight inside one folder by
            // putting its id in default_folder_id in the search model's context.
            const defaultFolderId = this.env.searchModel.context.default_folder_id;
            if (this.state.folders.some((folder) => folder.id === defaultFolderId)) {
                this.state.selectedFolderId = defaultFolderId;
            }
            await this.reloadDocuments();
            // Mirrors the server-side check in document_hub.document._check_management_permission():
            // lock/unlock/duplicate are restricted to the director tier. Hiding the menu entries for
            // everyone else is a UX nicety - the server enforces this independently either way.
            this.state.canManageDocuments = await this.user.hasGroup(
                "document_hub.group_document_hub_document_director"
            );
            // Mirrors ir.model.access.csv's perm_create on document_hub.folder: the
            // director tier already implies this group (see document_hub_security.xml),
            // so this one check covers both "explicitly granted" and "director+".
            this.state.canCreateFolders = await this.user.hasGroup(
                "document_hub.group_document_hub_folder_creator"
            );
            // Trash is only ever shown to a real system administrator: everyone
            // else's "Delete" only ever moves things there (see action_archive()
            // on both models) - permanently removing anything, or even seeing
            // what's pending removal, is reserved for base.group_system.
            this.state.isSystemAdmin = await this.user.hasGroup('base.group_system');
        });
        useBus(this.env.searchModel, "update", () => this.reloadDocuments());

        // Delete/F2/Ctrl+A on the current selection - window-level so they work
        // without first clicking into the tile grid, like a real file manager.
        // Skipped while focus is in a text input/textarea (rename field, search
        // bar, a dialog's own inputs) so typing there is never hijacked.
        this._onGlobalKeydown = (ev) => this.onGlobalKeydown(ev);
        onMounted(() => window.addEventListener("keydown", this._onGlobalKeydown));
        onWillUnmount(() => window.removeEventListener("keydown", this._onGlobalKeydown));
    }

    onGlobalKeydown(ev) {
        const tag = (ev.target.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select" || ev.target.isContentEditable) {
            return;
        }
        if (ev.key === "Delete") {
            if (this.state.selectedIds.size) {
                ev.preventDefault();
                if (this.state.isTrashView) {
                    this.bulkDeletePermanently();
                } else {
                    this.bulkDelete();
                }
            }
        } else if (ev.key === "F2" && !this.state.isTrashView && this.state.selectedIds.size === 1) {
            const [id] = this.state.selectedIds;
            const doc = this.state.documents.find((d) => d.id === id);
            if (doc && doc.state !== "lock") {
                ev.preventDefault();
                this.startRenameDocument(doc);
            }
        } else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "a" && this.state.documents.length) {
            ev.preventDefault();
            this.state.selectedIds = new Set(this.state.documents.map((doc) => doc.id));
        }
    }

    async loadFolders() {
        this.state.folders = await this.orm.searchRead(
            "document_hub.folder",
            [],
            ["name", "parent_folder_id"],
            { order: "sequence, name" }
        );
    }

    get childrenByParent() {
        const map = new Map();
        for (const folder of this.state.folders) {
            const parentId = folder.parent_folder_id ? folder.parent_folder_id[0] : false;
            if (!map.has(parentId)) {
                map.set(parentId, []);
            }
            map.get(parentId).push(folder);
        }
        return map;
    }

    get rootFolders() {
        return this.childrenByParent.get(false) || [];
    }

    get selectedFolder() {
        return this.state.folders.find((folder) => folder.id === this.state.selectedFolderId) || null;
    }

    get subfolders() {
        if (this.state.isTrashView) {
            return [];
        }
        return this.childrenByParent.get(this.state.selectedFolderId) || [];
    }

    get emptyStateLabel() {
        return this.state.isTrashView ? this.emptyTrashLabel : this.emptyFolderLabel;
    }

    get breadcrumbFolders() {
        const chain = [];
        let current = this.selectedFolder;
        while (current) {
            chain.unshift(current);
            const parentId = current.parent_folder_id ? current.parent_folder_id[0] : false;
            current = this.state.folders.find((folder) => folder.id === parentId) || null;
        }
        return chain;
    }

    tagNames(tagIds) {
        return tagIds.map((id) => this.state.tagsById[id]).filter(Boolean);
    }

    async selectFolder(folderId) {
        if (!this.state.isTrashView && this.state.selectedFolderId === folderId) {
            return;
        }
        this.state.isTrashView = false;
        this.state.selectedFolderId = folderId;
        this.clearSelection();
        await this.reloadDocuments();
    }

    async selectTrash() {
        if (!this.state.isSystemAdmin || this.state.isTrashView) {
            return;
        }
        this.state.isTrashView = true;
        this.state.selectedFolderId = false;
        this.clearSelection();
        await this.reloadDocuments();
    }

    async reloadDocuments() {
        const fields = ["name", "topic", "state", "cover_attachment_id", "cover_mimetype", "tag_ids", "owner_id"];
        if (this.state.isTrashView) {
            // Only the "root" of what was deleted: a folder whose own parent is
            // still active (its whole subtree moved to trash together with it -
            // see Folder.action_archive() - so the nested pieces don't also show
            // up here individually), and likewise a document whose folder is
            // still active (one deleted on its own, not via a folder cascade).
            const folderDomain = [
                ["active", "=", false],
                "|", ["parent_folder_id", "=", false], ["parent_folder_id.active", "=", true],
            ];
            const documentDomain = Domain.and([
                this.env.searchModel.domain,
                [["active", "=", false], ["folder_id.active", "=", true]],
            ]).toList();
            [this.state.trashedFolders, this.state.documents] = await Promise.all([
                this.orm.searchRead("document_hub.folder", folderDomain, ["name"]),
                this.orm.searchRead("document_hub.document", documentDomain, [...fields, "folder_id"]),
            ]);
            await this._syncTagCache();
            return;
        }
        this.state.trashedFolders = [];
        if (!this.state.selectedFolderId) {
            this.state.documents = [];
            return;
        }
        const domain = Domain.and([
            this.env.searchModel.domain,
            [["folder_id", "=", this.state.selectedFolderId]],
        ]).toList();
        this.state.documents = await this.orm.searchRead("document_hub.document", domain, fields);
        await this._syncTagCache();
    }

    async _syncTagCache() {
        const unknownTagIds = [...new Set(this.state.documents.flatMap((doc) => doc.tag_ids))].filter(
            (id) => !(id in this.state.tagsById)
        );
        if (unknownTagIds.length) {
            const tags = await this.orm.read("document_hub.tag", unknownTagIds, ["name"]);
            for (const tag of tags) {
                this.state.tagsById[tag.id] = tag.name;
            }
        }
    }

    // --- Folder actions ---------------------------------------------------

    get renamingFolderId() {
        return this.state.renaming && this.state.renaming.kind === "folder" ? this.state.renaming.id : false;
    }

    startRenameFolder(folder) {
        this.state.renaming = { kind: "folder", id: folder.id };
    }

    commitRenameFolder(ev, folder) {
        return this.commitRename(ev, "folder", folder.id);
    }

    async duplicateFolder(folder) {
        await this.orm.call("document_hub.folder", "copy", [folder.id]);
        await this.loadFolders();
    }

    downloadFolder(folder) {
        this.action.doAction({
            type: "ir.actions.act_url",
            url: `/document_hub/folder/${folder.id}/zip`,
            target: "self",
        });
    }

    async createSubfolder(parentFolder) {
        const [folderId] = await this.orm.create("document_hub.folder", [{
            name: this.newFolderDefaultName,
            parent_folder_id: parentFolder.id,
        }]);
        await this.loadFolders();
        this.state.renaming = { kind: "folder", id: folderId };
    }

    createSubfolderInCurrentFolder() {
        if (this.selectedFolder) {
            this.createSubfolder(this.selectedFolder);
        }
    }

    deleteFolder(folder) {
        this.dialog.add(ConfirmationDialog, {
            title: this.deleteFolderTitle,
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.orm.call("document_hub.folder", "action_archive", [folder.id]);
                await this.loadFolders();
                if (this.state.selectedFolderId === folder.id) {
                    this.state.selectedFolderId = false;
                    this.state.documents = [];
                }
            },
        });
    }

    async restoreFolder(folder) {
        await this.orm.call("document_hub.folder", "action_unarchive", [folder.id]);
        await this.loadFolders();
        await this.reloadDocuments();
    }

    deleteFolderPermanently(folder) {
        this.dialog.add(DocumentHubConfirmPurgeDialog, {
            title: this.deleteFolderTitle,
            expectedText: folder.name,
            onConfirm: async () => {
                await this.orm.unlink("document_hub.folder", [folder.id]);
                await this.reloadDocuments();
            },
        });
    }

    // --- Document actions ---------------------------------------------------

    startRenameDocument(doc) {
        this.state.renaming = { kind: "document", id: doc.id };
    }

    async duplicateDocument(doc) {
        await this.orm.call("document_hub.document", "copy", [doc.id]);
        await this.reloadDocuments();
    }

    async toggleLock(doc) {
        const method = doc.state === "lock" ? "action_open_document" : "action_lock_document";
        await this.orm.call("document_hub.document", method, [doc.id]);
        await this.reloadDocuments();
    }

    deleteDocument(doc) {
        this.dialog.add(ConfirmationDialog, {
            title: this.deleteDocumentTitle,
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.orm.call("document_hub.document", "action_archive", [doc.id]);
                await this.reloadDocuments();
            },
        });
    }

    async restoreDocument(doc) {
        await this.orm.call("document_hub.document", "action_unarchive", [doc.id]);
        await this.reloadDocuments();
    }

    deleteDocumentPermanently(doc) {
        this.dialog.add(DocumentHubConfirmPurgeDialog, {
            title: this.deleteDocumentTitle,
            expectedText: doc.topic,
            onConfirm: async () => {
                await this.orm.unlink("document_hub.document", [doc.id]);
                await this.reloadDocuments();
            },
        });
    }

    // --- Multi-select / bulk actions ----------------------------------------

    get selectionCountLabel() {
        return sprintf(_t("%s selected"), this.state.selectedIds.size);
    }

    isSelected(docId) {
        return this.state.selectedIds.has(docId);
    }

    toggleSelect(docId) {
        if (this.state.selectedIds.has(docId)) {
            this.state.selectedIds.delete(docId);
        } else {
            this.state.selectedIds.add(docId);
        }
        this.lastClickedId = docId;
    }

    selectRange(docId) {
        if (this.lastClickedId === null) {
            this.toggleSelect(docId);
            return;
        }
        const ids = this.state.documents.map((doc) => doc.id);
        const start = ids.indexOf(this.lastClickedId);
        const end = ids.indexOf(docId);
        if (start === -1 || end === -1) {
            this.toggleSelect(docId);
            return;
        }
        const [from, to] = start < end ? [start, end] : [end, start];
        for (const id of ids.slice(from, to + 1)) {
            this.state.selectedIds.add(id);
        }
    }

    clearSelection() {
        this.state.selectedIds.clear();
        this.lastClickedId = null;
    }

    get allSelected() {
        return this.state.documents.length > 0
            && this.state.documents.every((doc) => this.state.selectedIds.has(doc.id));
    }

    toggleSelectAll() {
        if (this.allSelected) {
            this.clearSelection();
        } else {
            this.state.selectedIds = new Set(this.state.documents.map((doc) => doc.id));
        }
    }

    onTileClick(ev, doc) {
        if (ev.shiftKey) {
            this.selectRange(doc.id);
            return;
        }
        if (this.state.selectedIds.size > 0) {
            this.toggleSelect(doc.id);
            return;
        }
        this.openDocument(doc);
    }

    async bulkMove() {
        this.dialog.add(DocumentHubFolderPickerDialog, {
            folders: this.state.folders,
            excludeFolderId: this.state.selectedFolderId,
            onSelected: async (folderId) => {
                await this.moveDocumentsToFolder([...this.state.selectedIds], folderId);
            },
        });
    }

    async bulkDuplicate() {
        for (const id of this.state.selectedIds) {
            await this.orm.call("document_hub.document", "copy", [id]);
        }
        this.clearSelection();
        await this.reloadDocuments();
    }

    bulkDelete() {
        this.dialog.add(ConfirmationDialog, {
            title: this.deleteDocumentTitle,
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.orm.call("document_hub.document", "action_archive", [[...this.state.selectedIds]]);
                this.clearSelection();
                await this.reloadDocuments();
            },
        });
    }

    async bulkRestore() {
        await this.orm.call("document_hub.document", "action_unarchive", [[...this.state.selectedIds]]);
        this.clearSelection();
        await this.reloadDocuments();
    }

    bulkDeletePermanently() {
        this.dialog.add(DocumentHubConfirmPurgeDialog, {
            title: this.deleteDocumentTitle,
            expectedText: this.purgeKeyword,
            onConfirm: async () => {
                await this.orm.unlink("document_hub.document", [...this.state.selectedIds]);
                this.clearSelection();
                await this.reloadDocuments();
            },
        });
    }

    // --- Drag & drop move (documents -> folders) ----------------------------

    onDocumentDragStart(ev, doc) {
        if (doc.state === "lock" && !this.state.selectedIds.has(doc.id)) {
            ev.preventDefault();
            return;
        }
        // Dragging a tile that's part of the active selection drags the whole
        // selection; dragging an unselected tile drags just that one document.
        this._draggedDocumentIds = this.state.selectedIds.has(doc.id)
            ? [...this.state.selectedIds]
            : [doc.id];
        ev.dataTransfer.effectAllowed = "move";
        // The actual id list lives in the JS property above, not in the
        // dataTransfer payload itself (simpler than serializing/parsing it,
        // and this app never needs to drag across browser windows/tabs).
        // This custom type only serves as a marker other drop targets can
        // check for during dragover/drop to tell "a document is being
        // dragged" apart from an OS file being dragged in for upload.
        ev.dataTransfer.setData("application/x-document-hub-ids", "1");
    }

    onDocumentDragEnd() {
        this._draggedDocumentIds = null;
        this.state.dragOverFolderId = false;
    }

    onSubfolderDragOver(ev) {
        if (this._draggedDocumentIds) {
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    onSubfolderDragEnter(ev, folder) {
        if (this._draggedDocumentIds) {
            this.state.dragOverFolderId = folder.id;
        }
    }

    onSubfolderDragLeave(ev, folder) {
        if (this.state.dragOverFolderId === folder.id) {
            this.state.dragOverFolderId = false;
        }
    }

    async onSubfolderDrop(ev, folder) {
        this.state.dragOverFolderId = false;
        if (!this._draggedDocumentIds) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        await this.moveDocumentsToFolder(this._draggedDocumentIds, folder.id);
        this._draggedDocumentIds = null;
    }

    async moveDocumentsToFolderById(folderId) {
        const ids = this._draggedDocumentIds;
        this._draggedDocumentIds = null;
        if (ids) {
            await this.moveDocumentsToFolder(ids, folderId);
        }
    }

    async moveDocumentsToFolder(ids, folderId) {
        // A locked document's folder_id is server-side protected (see
        // Document.write()/_LOCKED_PROTECTED_FIELDS) - filtering it out here
        // up front means the rest of the batch still moves instead of the
        // whole write() failing, and the user gets a clear reason why.
        const lockedCount = this.state.documents.filter(
            (doc) => ids.includes(doc.id) && doc.state === "lock"
        ).length;
        const movableIds = lockedCount
            ? ids.filter((id) => !this.state.documents.some((doc) => doc.id === id && doc.state === "lock"))
            : ids;
        if (lockedCount) {
            this.notification.add(this.lockedMoveSkippedLabel, { type: "warning" });
        }
        if (!movableIds.length || (movableIds.length === 1 && this.state.selectedFolderId === folderId)) {
            return;
        }
        await this.orm.write("document_hub.document", movableIds, { folder_id: folderId });
        this.clearSelection();
        await this.reloadDocuments();
    }

    buildFileModel(doc) {
        if (!doc.cover_attachment_id) {
            return null;
        }
        return Object.assign(new FileModel(), {
            id: doc.cover_attachment_id[0],
            name: doc.cover_attachment_id[1],
            mimetype: doc.cover_mimetype,
        });
    }

    openDocument(doc) {
        const file = this.buildFileModel(doc);
        if (!file) {
            this.openDocumentDetails(doc.id);
            return;
        }
        if (file.isViewable) {
            this.fileViewer.open(file);
        } else {
            this.action.doAction({ type: "ir.actions.act_url", url: file.downloadUrl, target: "self" });
        }
    }

    openDocumentDetails(docId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "document_hub.document",
            res_id: docId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    createBlankDocument() {
        this.dialog.add(FormViewDialog, {
            resModel: "document_hub.document",
            resId: false,
            title: this.newDocumentDialogTitle,
            context: { default_folder_id: this.state.selectedFolderId },
            onRecordSaved: () => this.reloadDocuments(),
        });
    }

    // --- Inline rename ---------------------------------------------------------

    isRenaming(kind, id) {
        return !!this.state.renaming && this.state.renaming.kind === kind && this.state.renaming.id === id;
    }

    onRenameKeydown(ev) {
        if (ev.key === "Enter") {
            ev.target.blur();
        } else if (ev.key === "Escape") {
            this._cancelRename = true;
            ev.target.blur();
        }
    }

    async commitRename(ev, kind, id) {
        this.state.renaming = null;
        if (this._cancelRename) {
            this._cancelRename = false;
            return;
        }
        const value = ev.target.value.trim();
        if (!value) {
            return;
        }
        if (kind === "folder") {
            await this.orm.write("document_hub.folder", [id], { name: value });
            await this.loadFolders();
        } else {
            await this.orm.write("document_hub.document", [id], { topic: value });
            await this.reloadDocuments();
        }
    }

    // --- Upload (button or drag & drop) ----------------------------------------

    pickFiles() {
        this.fileInputRef.el.click();
    }

    onFileInputChange(ev) {
        const files = [...ev.target.files];
        ev.target.value = null;
        if (files.length) {
            this.uploadAndCreateDocuments(files);
        }
    }

    onDragOver() {
        if (this.state.selectedFolderId && !this._draggedDocumentIds) {
            this.state.isDraggingOver = true;
        }
    }

    onDragLeave() {
        this.state.isDraggingOver = false;
    }

    async onDrop(ev) {
        this.state.isDraggingOver = false;
        if (this._draggedDocumentIds) {
            // Dropped on open canvas rather than a specific subfolder/tree
            // target: since a document tile is only visible while its own
            // folder is open, this is always the folder it's already in -
            // nothing to move.
            this._draggedDocumentIds = null;
            return;
        }
        if (!this.state.selectedFolderId || !ev.dataTransfer.files.length) {
            return;
        }
        await this.uploadAndCreateDocuments([...ev.dataTransfer.files]);
    }

    async uploadAndCreateDocuments(files) {
        for (const file of files) {
            if (!checkFileSize(file.size, this.notification)) {
                return;
            }
        }
        const response = await this.http.post(
            "/web/binary/upload_attachment",
            { csrf_token: odoo.csrf_token, ufile: files, model: "document_hub.document", id: 0 },
            "text"
        );
        const uploaded = JSON.parse(response);
        const privacyDoc = this.env.searchModel.context.default_privacy_doc || "mail";
        for (const uploadedFile of uploaded) {
            if (uploadedFile.error) {
                this.notification.add(uploadedFile.error, { type: "danger" });
                continue;
            }
            const [docId] = await this.orm.create("document_hub.document", [{
                topic: uploadedFile.filename,
                folder_id: this.state.selectedFolderId,
                privacy_doc: privacyDoc,
                file_ids: [[6, 0, [uploadedFile.id]]],
            }]);
            // /web/binary/upload_attachment uploads with res_id=0 (no document exists
            // yet to attach to). An attachment with res_id=0 is only readable by its
            // own creator (see ir.attachment.check(): res_id falsy => allowed only for
            // create_uid == uid). Repointing it at the saved document makes its access
            // follow the document's own read rules, so other users who can see the
            // document can also open its file.
            await this.orm.write("ir.attachment", [uploadedFile.id], {
                res_model: "document_hub.document",
                res_id: docId,
            });
        }
        await this.reloadDocuments();
    }

    // --- Versioning -----------------------------------------------------------

    uploadNewVersion(doc) {
        this._versionUploadDocId = doc.id;
        this.versionFileInputRef.el.click();
    }

    async onVersionFileInputChange(ev) {
        const files = [...ev.target.files];
        ev.target.value = null;
        const docId = this._versionUploadDocId;
        this._versionUploadDocId = null;
        if (!files.length || !docId) {
            return;
        }
        const file = files[0];
        if (!checkFileSize(file.size, this.notification)) {
            return;
        }
        // Unlike uploadAndCreateDocuments(), the document already exists: passing
        // its real id straight to upload_attachment attaches the file with the
        // right res_model/res_id from the start, no res_id=0 repointing needed.
        const response = await this.http.post(
            "/web/binary/upload_attachment",
            { csrf_token: odoo.csrf_token, ufile: [file], model: "document_hub.document", id: docId },
            "text"
        );
        const [uploadedFile] = JSON.parse(response);
        if (!uploadedFile || uploadedFile.error) {
            this.notification.add(uploadedFile ? uploadedFile.error : this.uploadFailedLabel, { type: "danger" });
            return;
        }
        await this.orm.call("document_hub.document", "action_upload_new_version", [docId, uploadedFile.id]);
        await this.reloadDocuments();
    }

    openVersionHistory(doc) {
        this.dialog.add(DocumentHubVersionDialog, {
            documentId: doc.id,
            onRestored: () => this.reloadDocuments(),
        });
    }
}
