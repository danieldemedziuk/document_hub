/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

// Loaded once and shared across every thumbnail on the page - pdf.js is a
// large (~80k line) bundle, so it's kept out of web.assets_backend and only
// pulled in lazily here, the first time a PDF tile actually needs it.
let pdfJsLibPromise = null;
function ensurePdfJsLib() {
    if (!pdfJsLibPromise) {
        pdfJsLibPromise = loadBundle("web.pdf_js_lib");
    }
    return pdfJsLibPromise;
}

/**
 * Renders a document's cover attachment as a real first-page-of-PDF
 * thumbnail, rasterized client-side via pdf.js (bundled by Odoo core, same
 * library @web/core/file_viewer already uses for full-page preview, and the
 * same render-to-canvas approach as website_slides' slides_upload.js). Falls
 * back to the generic PDF icon - the tile's previous behavior - on any
 * loading/rendering failure, so a corrupt or unusually large PDF degrades
 * gracefully instead of breaking the tile.
 */
export class DocumentHubPdfThumbnail extends Component {
    static template = "document_hub.PdfThumbnail";
    static props = {
        attachmentId: Number,
    };

    setup() {
        this.state = useState({ dataUrl: null });
        // Not returned/awaited on purpose: rendering a PDF thumbnail must not
        // block the rest of the tile grid from appearing. It resolves later
        // and updates state.dataUrl reactively.
        onWillStart(() => {
            this.renderThumbnail();
        });
    }

    async renderThumbnail() {
        try {
            await ensurePdfJsLib();
            // pdf.js' bundled `Util` global can be shadowed by Bootstrap's own
            // `Util` depending on script load order - reset it right before use
            // (same fix applied in website_slides' slides_upload.js).
            window.Util = window.pdfjsLib.Util;
            const pdf = await window.pdfjsLib.getDocument({
                url: `/web/content/${this.props.attachmentId}`,
            }).promise;
            const page = await pdf.getPage(1);
            const baseViewport = page.getViewport({ scale: 1 });
            const scale = 96 / baseViewport.width;
            const viewport = page.getViewport({ scale });
            const canvas = document.createElement("canvas");
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
            this.state.dataUrl = canvas.toDataURL();
        } catch {
            // Leave state.dataUrl null - the template falls back to the icon.
        }
    }
}
