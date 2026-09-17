import * as THREE from
    "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";

export class Jarvis3DScene {

    constructor(container) {

        this.container =
            container;

        this.scene =
            new THREE.Scene();

        this.camera =
            new THREE.PerspectiveCamera(
                50,
                container.clientWidth /
                    container.clientHeight,
                0.1,
                1000
            );

        this.camera.position.z = 6;

        this.renderer =
            new THREE.WebGLRenderer({
                antialias: true,
                alpha: true
            });

        this.renderer.setPixelRatio(
            Math.min(
                window.devicePixelRatio,
                2
            )
        );

        this.renderer.setSize(
            container.clientWidth,
            container.clientHeight
        );

        container.appendChild(
            this.renderer.domElement
        );

        this.setupLights();

        this.objects = new Map();

        window.addEventListener(
            "resize",
            () => this.resize()
        );

        this.animate();
    }

    setupLights() {

        const ambient =
            new THREE.AmbientLight(
                0xffffff,
                1.5
            );

        this.scene.add(
            ambient
        );

        const directional =
            new THREE.DirectionalLight(
                0xffffff,
                2
            );

        directional.position.set(
            4,
            5,
            6
        );

        this.scene.add(
            directional
        );
    }

    createCube(
        id = "cube"
    ) {

        if (
            this.objects.has(id)
        ) {
            return this.objects.get(id);
        }

        const geometry =
            new THREE.BoxGeometry(
                1.5,
                1.5,
                1.5
            );

        const material =
            new THREE.MeshStandardMaterial({
                metalness: 0.6,
                roughness: 0.25
            });

        const cube =
            new THREE.Mesh(
                geometry,
                material
            );

        this.scene.add(
            cube
        );

        this.objects.set(
            id,
            cube
        );

        return cube;
    }

    remove(id) {

        const object =
            this.objects.get(id);

        if (!object) {
            return;
        }

        this.scene.remove(
            object
        );

        object.geometry.dispose();
        object.material.dispose();

        this.objects.delete(id);
    }

    resize() {

        const width =
            this.container.clientWidth;

        const height =
            this.container.clientHeight;

        this.camera.aspect =
            width / height;

        this.camera.updateProjectionMatrix();

        this.renderer.setSize(
            width,
            height
        );
    }

    animate() {

        requestAnimationFrame(
            () => this.animate()
        );

        for (
            const object
            of this.objects.values()
        ) {

            object.rotation.y += 0.005;
        }

        this.renderer.render(
            this.scene,
            this.camera
        );
    }
}