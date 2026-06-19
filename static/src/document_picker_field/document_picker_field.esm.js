/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

/**
 * Universal Many2many widget for `document_hub.document`.
 *
 * Renders the linked documents as clickable cards. Clicking a card opens the
 * document form view in a dialog (same form as creation), where the file_ids
 * (attachments) can be edited directly. Provides three actions: create a new
 * document, search/link existing documents, and unlink (never delete).
 *
 * Labels and the available actions are configurable through field options:
 *   options="{'add_label': '...', 'search_label': '...', 'empty_label': '...',
 *             'no_create': True, 'no_search': True}"
 */
export class DocumentPickerField extends Component {
    static template = "document_hub.DocumentPickerField";
    static props = {
        ...standardFieldProps,
        context: { type: Object, optional: true },
        canCreate: { type: Boolean, optional: true },
        canSearch: { type: Boolean, optional: true },
        showFilenames: { type: Boolean, optional: true },
        addLabel: { type: String, optional: true },
        searchLabel: { type: String, optional: true },
        emptyLabel: { type: String, optional: true },
        string: { type: String, optional: true },
    };

    setup() {
        const self = this;
        this.dialog = useService("dialog");
        // Read at call-time by useOpenMany2XRecord, so getters keep them live.
        const activeActions = {
            get create() {
                return self.props.canCreate && !self.props.readonly;
            },
            get write() {
                return !self.props.readonly;
            },
        };
        // Editing an existing document: reload the edited record datapoint so the
        // card reflects the changes. list.load() skips already-cached records, so
        // we reload the specific record (which refetches its related fields).
        this.openExisting = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions,
            isToMany: true,
            fieldString: this.props.string,
            onRecordSaved: () => this.editedRecord && this.editedRecord.load(),
        });
        // Creating a new document: link the freshly saved record.
        this.openNew = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions,
            isToMany: true,
            fieldString: this.props.string,
            onRecordSaved: (record) => this.list.linkTo(record.resId),
        });
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get records() {
        return this.list.records;
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    editRecord(record) {
        // Remember which datapoint is open so onRecordSaved can reload just it.
        this.editedRecord = record;
        this.openExisting({ resId: record.resId, context: this.props.context });
    }

    addRecord() {
        this.openNew({ resId: false, context: this.props.context });
    }

    searchRecords() {
        // Exclude already-linked documents so they can't be picked twice.
        const linkedIds = this.records.map((rec) => rec.resId);
        this.dialog.add(SelectCreateDialog, {
            title: _t("Select documents"),
            resModel: this.relation,
            context: this.props.context,
            domain: [["id", "not in", linkedIds]],
            multiSelect: true,
            noCreate: true,
            onSelected: (resIds) => this.list.addAndRemove({ add: resIds }),
        });
    }

    removeRecord(record) {
        // UNLINK (forget), not DELETE — never remove the document from the database.
        this.list.forget(record);
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
    extractProps({ options, string }, dynamicInfo) {
        return {
            context: dynamicInfo.context,
            canCreate: !options.no_create,
            canSearch: !options.no_search,
            showFilenames: Boolean(options.show_filenames),
            addLabel: options.add_label || _t("Add document"),
            searchLabel: options.search_label || _t("Search documents"),
            emptyLabel: options.empty_label || _t("No documents yet."),
            string,
        };
    },
};

registry.category("fields").add("document_hub_documents", documentPickerField);
