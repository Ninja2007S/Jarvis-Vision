export class VisionHUD {

    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");

        this.objects = [];
        this.pointer = null;
        this.selectedId = null;
    }

    resize() {
        const rect =
            this.canvas.getBoundingClientRect();

        const dpr =
            window.devicePixelRatio || 1;

        this.canvas.width =
            rect.width * dpr;

        this.canvas.height =
            rect.height * dpr;

        this.ctx.setTransform(
            dpr,
            0,
            0,
            dpr,
            0,
            0
        );
    }

    update(data) {

        this.objects =
            data.objects || [];

        this.pointer =
            data.pointer || null;

        this.selectedId =
            data.selected_id ?? null;

        this.draw();
    }

    draw() {

        const ctx = this.ctx;

        const width =
            this.canvas.clientWidth;

        const height =
            this.canvas.clientHeight;

        ctx.clearRect(
            0,
            0,
            width,
            height
        );

        for (
            const object of this.objects
        ) {

            this.drawObject(
                object,
                width,
                height
            );
        }

        if (this.pointer) {

            this.drawPointer(
                this.pointer.x,
                this.pointer.y,
                width,
                height
            );
        }
    }

    drawObject(
        object,
        width,
        height
    ) {

        const box = object.box;

        const x = box.x1;
        const y = box.y1;

        const w =
            box.x2 - box.x1;

        const h =
            box.y2 - box.y1;

        const selected =
            object.id === this.selectedId;

        const ctx = this.ctx;

        ctx.lineWidth =
            selected ? 4 : 2;

        ctx.strokeStyle =
            selected
                ? "#ffffff"
                : "#55d9ff";

        ctx.strokeRect(
            x,
            y,
            w,
            h
        );

        ctx.font =
            "600 14px Arial";

        ctx.fillStyle =
            "#ffffff";

        ctx.fillText(
            `${object.label} ${(object.confidence * 100).toFixed(0)}%`,
            x,
            Math.max(
                18,
                y - 8
            )
        );
    }

    drawPointer(
        x,
        y
    ) {

        const ctx = this.ctx;

        ctx.beginPath();

        ctx.arc(
            x,
            y,
            9,
            0,
            Math.PI * 2
        );

        ctx.strokeStyle =
            "#ffffff";

        ctx.lineWidth = 2;

        ctx.stroke();

        ctx.beginPath();

        ctx.arc(
            x,
            y,
            3,
            0,
            Math.PI * 2
        );

        ctx.fillStyle =
            "#ffffff";

        ctx.fill();
    }
}