/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Extra friction for the one irreversible action in the explorer: permanent
 * deletion. The confirm button stays disabled until the viewer types the
 * expected text (the item's own name for a single item, a fixed keyword for
 * a bulk purge where there's no single name to match) exactly.
 */
export class DocumentHubConfirmPurgeDialog extends Component {
    static template = "document_hub.ConfirmPurgeDialog";
    static components = { Dialog };
    static props = {
        title: String,
        expectedText: String,
        close: Function,
        onConfirm: Function,
    };

    setup() {
        this.confirmLabel = _t("Delete permanently");
        this.cancelLabel = _t("Cancel");
        this.instructionLabel = sprintf(
            _t("This cannot be undone. Type %s to confirm:"),
            this.props.expectedText
        );
        this.state = useState({ typed: "" });
    }

    get canConfirm() {
        return this.state.typed === this.props.expectedText;
    }

    confirm() {
        if (!this.canConfirm) {
            return;
        }
        this.props.onConfirm();
        this.props.close();
    }
}
