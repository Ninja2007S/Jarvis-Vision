export class TwoHandZoom {

    constructor() {

        this.initialDistance = null;
        this.initialScale = 1;
    }

    distance(
        a,
        b
    ) {

        const dx =
            a.x - b.x;

        const dy =
            a.y - b.y;

        return Math.sqrt(
            dx * dx +
            dy * dy
        );
    }

    begin(
        hand1,
        hand2,
        object
    ) {

        this.initialDistance =
            this.distance(
                hand1,
                hand2
            );

        this.initialScale =
            object.scale.x;
    }

    update(
        hand1,
        hand2,
        object
    ) {

        if (
            this.initialDistance === null
        ) {
            return;
        }

        const distance =
            this.distance(
                hand1,
                hand2
            );

        const ratio =
            distance /
            this.initialDistance;

        const scale =
            this.initialScale *
            ratio;

        const safeScale =
            Math.max(
                0.2,
                Math.min(
                    scale,
                    5
                )
            );

        object.scale.set(
            safeScale,
            safeScale,
            safeScale
        );
    }

    end() {

        this.initialDistance =
            null;
    }
}