export class GrabController {

    constructor() {

        this.object = null;

        this.offset = {
            x: 0,
            y: 0
        };

        this.active = false;
    }

    grab(
        object,
        pointerX,
        pointerY
    ) {

        if (!object) {
            return;
        }

        this.object = object;

        this.active = true;

        this.offset.x =
            object.position.x -
            pointerX;

        this.offset.y =
            object.position.y -
            pointerY;
    }

    move(
        pointerX,
        pointerY
    ) {

        if (
            !this.active ||
            !this.object
        ) {
            return;
        }

        this.object.position.x =
            pointerX +
            this.offset.x;

        this.object.position.y =
            pointerY +
            this.offset.y;
    }

    release() {

        this.active = false;

        this.object = null;
    }
}