/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { DocumentHubKanbanRenderer } from "./document_hub_kanban_renderer.esm";

export const documentHubKanbanView = {
    ...kanbanView,
    Renderer: DocumentHubKanbanRenderer,
};

registry.category("views").add("document_hub_kanban", documentHubKanbanView);
