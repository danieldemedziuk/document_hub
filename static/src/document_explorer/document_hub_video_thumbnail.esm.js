/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Renders a document's cover attachment as a real video-frame thumbnail,
 * captured client-side via a hidden <video> element seeked partway in and
 * drawn to a canvas - the same "render once, cache the dataURL" shape as
 * DocumentHubPdfThumbnail, just without needing pdf.js. Falls back to the
 * generic video icon on any loading/decoding failure (unsupported codec,
 * CORS, etc).
 */
export class DocumentHubVideoThumbnail extends Component {
    static template = "document_hub.VideoThumbnail";
    static props = {
        attachmentId: Number,
    };

    setup() {
        this.state = useState({ dataUrl: null });
        // Not returned/awaited on purpose - see DocumentHubPdfThumbnail for why.
        onWillStart(() => {
            this.renderThumbnail();
        });
    }

    async renderThumbnail() {
        try {
            const video = document.createElement("video");
            video.muted = true;
            video.preload = "auto";
            video.src = `/web/content/${this.props.attachmentId}`;
            await new Promise((resolve, reject) => {
                video.addEventListener("loadedmetadata", resolve, { once: true });
                video.addEventListener("error", reject, { once: true });
            });
            await new Promise((resolve, reject) => {
                video.addEventListener("seeked", resolve, { once: true });
                video.addEventListener("error", reject, { once: true });
                video.currentTime = Math.min(1, (video.duration || 2) / 2);
            });
            const scale = 96 / video.videoWidth;
            const canvas = document.createElement("canvas");
            canvas.width = Math.round(video.videoWidth * scale);
            canvas.height = Math.round(video.videoHeight * scale);
            canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
            this.state.dataUrl = canvas.toDataURL();
        } catch {
            // Leave state.dataUrl null - the template falls back to the icon.
        }
    }
}
