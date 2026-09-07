/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { sprintf } from "@web/core/utils/strings";
import { Dialog } from "@web/core/dialog/dialog";

const SIZE_UNITS = ["B", "KB", "MB", "GB"];

function formatBytes(bytes) {
    if (!bytes) {
        return "0 B";
    }
    let value = bytes;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < SIZE_UNITS.length - 1) {
        value /= 1024;
        unitIndex++;
    }
    return `${value.toFixed(unitIndex ? 1 : 0)} ${SIZE_UNITS[unitIndex]}`;
}

/**
 * Read-only history of the attachments that used to be the current file for
 * a document_hub.document, with a "Restore" action per row. Restoring simply
 * calls the same server method used to upload a fresh new version, passing
 * the old attachment's id back in - see document_hub.document.action_upload_new_version().
 */
export class DocumentHubVersionDialog extends Component {
    static template = "document_hub.VersionDialog";
    static components = { Dialog };
    static props = {
        documentId: Number,
        close: Function,
        onRestored: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.title = _t("Version history");
        this.restoreLabel = _t("Restore");
        this.closeLabel = _t("Close");
        this.noVersionsLabel = _t("No earlier versions yet.");
        this.currentVersionLabel = _t("Current");
        this.state = useState({ versions: [], currentFile: null });
        onWillStart(async () => {
            const [doc] = await this.orm.read("document_hub.document", [this.props.documentId], ["file_ids"]);
            if (doc.file_ids.length) {
                const [attachment] = await this.orm.read("ir.attachment", [doc.file_ids[0]], ["name", "file_size"]);
                this.state.currentFile = attachment;
            }
            this.state.versions = await this.orm.searchRead(
                "document_hub.document.version",
                [["document_id", "=", this.props.documentId]],
                ["attachment_id", "version_number", "create_uid", "create_date", "file_size"],
                { order: "version_number desc" }
            );
        });
    }

    downloadUrl(attachmentId) {
        return `/web/content/${attachmentId}?download=true`;
    }

    avatarUrl(userId) {
        return `/web/image/res.users/${userId}/avatar_128`;
    }

    formatVersionDate(version) {
        return formatDateTime(deserializeDateTime(version.create_date));
    }

    formatSize(bytes) {
        return formatBytes(bytes);
    }

    // Size delta compared to the row above (the next-newer version, or
    // "Current" for the first historical row) - a lightweight, honest stand-in
    // for a real content diff, which isn't meaningful for arbitrary binary files.
    sizeDeltaLabel(index) {
        const newerSize = index === 0 ? (this.state.currentFile && this.state.currentFile.file_size) : this.state.versions[index - 1].file_size;
        if (newerSize === undefined || newerSize === null) {
            return "";
        }
        const delta = this.state.versions[index].file_size - newerSize;
        if (!delta) {
            return _t("(same size)");
        }
        return sprintf(delta > 0 ? _t("(+%s)") : _t("(-%s)"), formatBytes(Math.abs(delta)));
    }

    async restore(version) {
        await this.orm.call("document_hub.document", "action_upload_new_version", [
            this.props.documentId,
            version.attachment_id[0],
        ]);
        if (this.props.onRestored) {
            this.props.onRestored();
        }
        this.props.close();
    }
}
