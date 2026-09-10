/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

/**
 * Shared base for the `document_hub.document` picker widgets.
 *
 * Renders linked documents as clickable cards. Clicking a card opens the
 * document form view in a dialog (same form as creation), where the file_ids
 * (attachments) can be edited directly. Provides three actions: create a new
 * document, search/link existing documents, and unlink (never delete).
 *
 * Subclasses adapt the widget to a field type by implementing the value
 * protocol below. Everything the two variants share -- the template, both
 * dialogs, the search dialog and the props -- lives here.
 *
 * Value protocol to implement:
 *   get allowsMultiple()  whether more than one document fits
 *   get cards()           normalized card view models, see makeCard()
 *   get linkedIds()       ids already linked, excluded from the search dialog
 *   link(resIds)          link the given documents
 *   unlink(card)          unlink a single card -- UNLINK, never DELETE: the
 *                         document itself must survive in the database
 *   onSavedNew(record)    the create dialog saved a brand new document
 *   onSavedExisting()     the edit dialog saved the currently open card
 */
export class DocumentPickerBase extends Component {
    static template = "document_hub.DocumentPickerCards";
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
        // isToMany only decides whether the dialog footer offers "Save & New".
        const isToMany = this.allowsMultiple;
        this.openExisting = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions,
            isToMany,
            fieldString: this.props.string,
            onRecordSaved: () => this.onSavedExisting(),
        });
        this.openNew = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions,
            isToMany,
            fieldString: this.props.string,
            onRecordSaved: (record) => this.onSavedNew(record),
        });
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    // Hides the create/search buttons once a single-valued field is taken
    get canAdd() {
        return this.allowsMultiple || !this.cards.length;
    }

    // Normalizes whatever a subclass holds into what the template renders.
    makeCard({ resId, displayName, topic, fileNames, record }) {
        return {
            key: resId,
            resId,
            displayName: displayName || "",
            topic: topic || "",
            fileNames: fileNames || "",
            record,
        };
    }

    editCard(card) {
        // Remember which card is open so onSavedExisting can refresh just it.
        this.editedCard = card;
        this.openExisting({ resId: card.resId, context: this.props.context });
    }

    addRecord() {
        this.openNew({ resId: false, context: this.props.context });
    }

    searchRecords() {
        // Exclude already-linked documents so they can't be picked twice.
        this.dialog.add(SelectCreateDialog, {
            title: _t("Select documents"),
            resModel: this.relation,
            context: this.props.context,
            domain: [["id", "not in", this.linkedIds]],
            multiSelect: this.allowsMultiple,
            noCreate: true,
            onSelected: (resIds) => this.link(resIds),
        });
    }
}

/**
 * Shared `extractProps` body. Both field descriptors read the same options, so
 * they delegate here instead of keeping two copies in sync.
 */
export function extractPickerProps({ options, string }, dynamicInfo) {
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
}
