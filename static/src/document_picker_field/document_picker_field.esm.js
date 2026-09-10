/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DocumentPickerBase, extractPickerProps } from "./document_picker_common.esm";

/**
 * Many2many widget for `document_hub.document`.
 *
 * Card data comes from `relatedFields` below, which the framework loads onto
 * each linked record datapoint.
 *
 * Labels and the available actions are configurable through field options:
 *   options="{'add_label': '...', 'search_label': '...', 'empty_label': '...',
 *             'show_filenames': True, 'no_create': True, 'no_search': True}"
 */
export class DocumentPickerField extends DocumentPickerBase {
    get allowsMultiple() {
        return true;
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get cards() {
        return this.list.records.map((record) =>
            this.makeCard({
                resId: record.resId,
                displayName: record.data.display_name,
                topic: record.data.topic,
                fileNames: record.data.file_names,
                record,
            })
        );
    }

    get linkedIds() {
        return this.list.records.map((record) => record.resId);
    }

    link(resIds) {
        return this.list.addAndRemove({ add: resIds });
    }

    unlink(card) {
        return this.list.forget(card.record);
    }

    onSavedNew(record) {
        return this.list.linkTo(record.resId);
    }

    onSavedExisting() {
        // list.load() skips already-cached records, so reload the specific
        // datapoint instead (which refetches its related fields).
        return this.editedCard && this.editedCard.record.load();
    }
}

export const documentPickerField = {
    component: DocumentPickerField,
    supportedTypes: ["many2many"],
    relatedFields: () => [
        { name: "display_name", type: "char" },
        { name: "topic", type: "char" },
        { name: "file_names", type: "char" },
    ],
    extractProps: extractPickerProps,
};

registry.category("fields").add("document_hub_documents", documentPickerField);
