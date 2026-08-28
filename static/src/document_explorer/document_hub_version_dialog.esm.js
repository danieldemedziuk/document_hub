/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { Dialog } from "@web/core/dialog/dialog";

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
        this.state = useState({ versions: [] });
        onWillStart(async () => {
            this.state.versions = await this.orm.searchRead(
                "document_hub.document.version",
                [["document_id", "=", this.props.documentId]],
                ["attachment_id", "version_number", "create_uid", "create_date"],
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
