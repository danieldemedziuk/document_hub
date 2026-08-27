/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Flattens the folder tree (already loaded by the Explorer) into a single
 * depth-first, depth-indexed list, so the picker can render it as one
 * scrollable indented list instead of a recursive tree component - simpler,
 * and all that's needed for a pick-one-and-confirm dialog.
 */
function buildIndentedList(folders) {
    const childrenByParent = new Map();
    for (const folder of folders) {
        const parentId = folder.parent_folder_id ? folder.parent_folder_id[0] : false;
        if (!childrenByParent.has(parentId)) {
            childrenByParent.set(parentId, []);
        }
        childrenByParent.get(parentId).push(folder);
    }
    const rows = [];
    const visit = (parentId, depth) => {
        for (const folder of childrenByParent.get(parentId) || []) {
            rows.push({ id: folder.id, name: folder.name, depth });
            visit(folder.id, depth + 1);
        }
    };
    visit(false, 0);
    return rows;
}

/**
 * A friendlier, on-brand replacement for the generic SelectCreateDialog list
 * view when picking a destination folder for a bulk move: the same folder
 * tree the Explorer sidebar already shows, indented and with folder icons,
 * click-to-select-then-confirm.
 */
export class DocumentHubFolderPickerDialog extends Component {
    static template = "document_hub.FolderPickerDialog";
    static components = { Dialog };
    static props = {
        folders: Array,
        close: Function,
        onSelected: Function,
        excludeFolderId: { type: [Number, { value: false }], optional: true },
    };

    setup() {
        this.title = _t("Move to folder");
        this.moveLabel = _t("Move");
        this.cancelLabel = _t("Cancel");
        this.noFoldersLabel = _t("No folders available.");
        this.state = useState({ selectedId: false });
        this.rows = buildIndentedList(this.props.folders).filter(
            (folder) => folder.id !== this.props.excludeFolderId
        );
    }

    select(folderId) {
        this.state.selectedId = folderId;
    }

    confirm() {
        if (!this.state.selectedId) {
            return;
        }
        this.props.onSelected(this.state.selectedId);
        this.props.close();
    }
}
