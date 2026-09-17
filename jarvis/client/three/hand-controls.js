export class Hand3DController {

    constructor(scene) {

        this.scene =
            scene;

        this.selected =
            null;

        this.lastX = null;
        this.lastY = null;

        this.dragging = false;
    }

    select(object) {

        this.selected =
            object;

        if (!object) {
            return;
        }

        this.lastX = null;
        this.lastY = null;
    }

    startDrag(
        x,
        y
    ) {

        if (!this.selected) {
            return;
        }

        this.dragging = true;

        this.lastX = x;
        this.lastY = y;
    }

    move(
        x,
        y
    ) {

        if (
            !this.dragging ||
            !this.selected
        ) {
            return;
        }

        if (
            this.lastX === null ||
            this.lastY === null
        ) {
            this.lastX = x;
            this.lastY = y;
            return;
        }

        const dx =
            x - this.lastX;

        const dy =
            y - this.lastY;

        this.selected.rotation.y +=
            dx * 0.01;

        this.selected.rotation.x +=
            dy * 0.01;

        this.lastX = x;
        this.lastY = y;
    }

    endDrag() {

        this.dragging = false;

        this.lastX = null;
        this.lastY = null;
    }
}