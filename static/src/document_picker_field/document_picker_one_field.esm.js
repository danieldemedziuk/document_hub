/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { DocumentPickerBase, extractPickerProps } from "./document_picker_common.esm";

const CARD_FIELDS = ["display_name", "topic", "file_names"];

/**
 * Many2one widget for `document_hub.document`.
 *
 * Same card UI as the many2many variant, but a many2one datapoint is the plain
 * tuple `[id, display_name]`, so `relatedFields` cannot carry the extra card
 * data: the read spec for many2one is fixed to `display_name` and the parser
 * collapses the value to that tuple. The card data is therefore fetched here.
 *
 * Once a document is linked, the create/search buttons are hidden.
 *
 * Labels and the available actions are configurable through field options:
 *   options="{'add_label': '...', 'search_label': '...', 'empty_label': '...',
 *             'show_filenames': True, 'no_create': True, 'no_search': True}"
 */
export class DocumentPickerOneField extends DocumentPickerBase {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ card: null });
        // Refetch only when the linked id actually changes, otherwise the
        // observer would loop on its own state writes.
        this.loadedId = undefined;
        useRecordObserver(async (record, props) => {
            const value = record.data[props.name];
            const resId = value ? value[0] : false;
            if (resId === this.loadedId) {
                return;
            }
            this.loadedId = resId;
            this.state.card = resId ? await this.fetchCard(resId) : null;
        });
    }

    get allowsMultiple() {
        return false;
    }

    get resId() {
        const value = this.props.record.data[this.props.name];
        return value ? value[0] : false;
    }

    get cards() {
        return this.state.card ? [this.state.card] : [];
    }

    get linkedIds() {
        return this.resId ? [this.resId] : [];
    }

    async fetchCard(resId) {
        const records = await this.orm.read(this.relation, [resId], CARD_FIELDS, {
            context: this.props.context,
        });
        if (!records.length) {
            // The document is gone. Render as empty rather than crashing.
            return null;
        }
        const data = records[0];
        return this.makeCard({
            resId,
            displayName: data.display_name,
            topic: data.topic,
            fileNames: data.file_names,
        });
    }

    link(resIds) {
        // The display name is left out on purpose: the model resolves it for a
        // [id, undefined] tuple, so no extra name_get is needed here.
        return this.props.record.update({ [this.props.name]: [resIds[0], undefined] });
    }

    unlink() {
        return this.props.record.update({ [this.props.name]: false });
    }

    onSavedNew(record) {
        return this.link([record.resId]);
    }

    async onSavedExisting() {
        // The linked id did not change, so the observer will not fire: refetch
        // straight away to pick up the edited topic and attachments.
        const resId = this.resId;
        if (!resId) {
            return;
        }
        this.loadedId = resId;
        this.state.card = await this.fetchCard(resId);
    }
}

export const documentPickerOneField = {
    component: DocumentPickerOneField,
    supportedTypes: ["many2one"],
    extractProps: extractPickerProps,
};

registry.category("fields").add("document_hub_document", documentPickerOneField);
