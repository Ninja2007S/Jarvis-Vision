/* ============================================================
   JARVIS REAL 3D HOLOGRAPHIC ENGINE
   ============================================================ */

"use strict";


/* ============================================================
   GLOBALS
   ============================================================ */

let scene;
let camera;
let renderer;

let socket = null;

let cameraImage;

let virtualObjects = new Map();

let particles;

let raycaster;

let pointerNDC =
    new THREE.Vector2();

let pointerScreen =
    new THREE.Vector2();

let selectedObjectId = null;

let grabbedObjectId = null;

let currentGesture =
    "unknown";

let createMode = false;

let lastStateTime = 0;

let clock =
    new THREE.Clock();


/* ============================================================
   MATERIALS
   ============================================================ */

function hologramMaterial(
    color = 0x00eaff,
    opacity = 0.82
) {

    return new THREE.MeshStandardMaterial({

        color,

        emissive:
            color,

        emissiveIntensity:
            1.6,

        transparent:
            true,

        opacity,

        metalness:
            0.15,

        roughness:
            0.25,

        depthWrite:
            false,

        side:
            THREE.DoubleSide

    });

}


function hologramWireMaterial(
    color = 0x00ffff
) {

    return new THREE.MeshBasicMaterial({

        color,

        wireframe:
            true,

        transparent:
            true,

        opacity:
            0.9,

        depthWrite:
            false

    });

}


/* ============================================================
   INITIALIZE
   ============================================================ */

function init() {

    cameraImage =
        document.getElementById(
            "camera"
        );


    /* --------------------------------------------------------
       Scene
       -------------------------------------------------------- */

    scene =
        new THREE.Scene();


    /* --------------------------------------------------------
       Camera
       -------------------------------------------------------- */

    camera =
        new THREE.PerspectiveCamera(
            45,
            window.innerWidth /
                window.innerHeight,
            0.01,
            100
        );

    camera.position.set(
        0,
        0,
        7
    );


    /* --------------------------------------------------------
       Renderer
       -------------------------------------------------------- */

    renderer =
        new THREE.WebGLRenderer({

            canvas:
                document.getElementById(
                    "three"
                ),

            alpha:
                true,

            antialias:
                true,

            powerPreference:
                "high-performance"

        });


    renderer.setPixelRatio(
        Math.min(
            window.devicePixelRatio,
            2
        )
    );

    renderer.setSize(
        window.innerWidth,
        window.innerHeight
    );


    renderer.outputColorSpace =
        THREE.SRGBColorSpace;


    /* --------------------------------------------------------
       Lighting
       -------------------------------------------------------- */

    const ambient =
        new THREE.AmbientLight(
            0x88ffff,
            1.8
        );

    scene.add(
        ambient
    );


    const pointLight =
        new THREE.PointLight(
            0x00ffff,
            8,
            20
        );

    pointLight.position.set(
        0,
        2,
        4
    );

    scene.add(
        pointLight
    );


    const purpleLight =
        new THREE.PointLight(
            0xaa44ff,
            5,
            15
        );

    purpleLight.position.set(
        -3,
        -2,
        2
    );

    scene.add(
        purpleLight
    );


    /* --------------------------------------------------------
       Raycaster
       -------------------------------------------------------- */

    raycaster =
        new THREE.Raycaster();


    /* --------------------------------------------------------
       Particle field
       -------------------------------------------------------- */

    createParticleField();


    /* --------------------------------------------------------
       Resize
       -------------------------------------------------------- */

    window.addEventListener(
        "resize",
        resize
    );


    /* --------------------------------------------------------
       Keyboard
       -------------------------------------------------------- */

    buildKeyboard();


    /* --------------------------------------------------------
       WebSocket
       -------------------------------------------------------- */

    connect();


    /* --------------------------------------------------------
       Render
       -------------------------------------------------------- */

    animate();

}


/* ============================================================
   PARTICLE FIELD
   ============================================================ */

function createParticleField() {

    const count = 700;

    const positions =
        new Float32Array(
            count * 3
        );

    for (
        let i = 0;
        i < count;
        i++
    ) {

        positions[i * 3] =
            (Math.random() - 0.5) *
            14;

        positions[i * 3 + 1] =
            (Math.random() - 0.5) *
            8;

        positions[i * 3 + 2] =
            (Math.random() - 0.5) *
            8;

    }

    const geometry =
        new THREE.BufferGeometry();

    geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
            positions,
            3
        )
    );


    const material =
        new THREE.PointsMaterial({

            color:
                0x38eaff,

            size:
                0.012,

            transparent:
                true,

            opacity:
                0.55,

            depthWrite:
                false

        });


    particles =
        new THREE.Points(
            geometry,
            material
        );

    scene.add(
        particles
    );

}


/* ============================================================
   CREATE REAL 3D GEOMETRY
   ============================================================ */

function createGeometry(
    type
) {

    switch (
        type.toLowerCase()
    ) {

        case "cube":

            return new THREE.BoxGeometry(
                1.45,
                1.45,
                1.45,
                4,
                4,
                4
            );


        case "sphere":

            return new THREE.IcosahedronGeometry(
                1.05,
                3
            );


        case "icosphere":

            return new THREE.IcosahedronGeometry(
                1.05,
                4
            );


        case "pyramid":

            return new THREE.ConeGeometry(
                1.15,
                1.8,
                4,
                4
            );


        case "diamond":

            return new THREE.OctahedronGeometry(
                1.25,
                2
            );


        case "ring":

            return new THREE.TorusGeometry(
                1.05,
                0.25,
                12,
                48
            );


        case "torus":

            return new THREE.TorusGeometry(
                1.0,
                0.30,
                16,
                64
            );


        case "torusknot":

            return new THREE.TorusKnotGeometry(
                0.8,
                0.22,
                96,
                16,
                2,
                3
            );


        case "cone":

            return new THREE.ConeGeometry(
                1.0,
                1.8,
                32,
                8
            );


        case "cylinder":

            return new THREE.CylinderGeometry(
                0.85,
                0.85,
                1.7,
                32,
                8
            );


        case "octahedron":

            return new THREE.OctahedronGeometry(
                1.2,
                2
            );


        case "dodecahedron":

            return new THREE.DodecahedronGeometry(
                1.15,
                2
            );


        case "icosahedron":

            return new THREE.IcosahedronGeometry(
                1.15,
                2
            );


        default:

            return new THREE.IcosahedronGeometry(
                1.1,
                2
            );

    }

}


/* ============================================================
   CREATE REAL HOLOGRAM
   ============================================================ */

function createHologram(
    data
) {

    const group =
        new THREE.Group();


    const geometry =
        createGeometry(
            data.object_type
        );


    const material =
        hologramMaterial();


    const mesh =
        new THREE.Mesh(
            geometry,
            material
        );


    group.add(
        mesh
    );


    /* --------------------------------------------------------
       REAL WIREFRAME
       -------------------------------------------------------- */

    const wireGeometry =
        geometry.clone();

    const wireMaterial =
        hologramWireMaterial(
            0x7fffff
        );

    const wire =
        new THREE.Mesh(
            wireGeometry,
            wireMaterial
        );

    wire.scale.setScalar(
        1.002
    );

    group.add(
        wire
    );


    /* --------------------------------------------------------
       Outer glow shell
       -------------------------------------------------------- */

    const glowGeometry =
        geometry.clone();

    const glowMaterial =
        new THREE.MeshBasicMaterial({

            color:
                0x00dfff,

            transparent:
                true,

            opacity:
                0.08,

            side:
                THREE.BackSide,

            depthWrite:
                false

        });


    const glow =
        new THREE.Mesh(
            glowGeometry,
            glowMaterial
        );

    glow.scale.setScalar(
        1.10
    );

    group.add(
        glow
    );


    /* --------------------------------------------------------
       Orbital ring
       -------------------------------------------------------- */

    const ringGeometry =
        new THREE.TorusGeometry(
            1.45,
            0.012,
            8,
            64
        );

    const ringMaterial =
        new THREE.MeshBasicMaterial({

            color:
                0x00ffff,

            transparent:
                true,

            opacity:
                0.7,

            depthWrite:
                false

        });


    const ring =
        new THREE.Mesh(
            ringGeometry,
            ringMaterial
        );

    ring.rotation.x =
        Math.PI / 2;

    group.add(
        ring
    );


    /* --------------------------------------------------------
       Second orbital ring
       -------------------------------------------------------- */

    const ring2 =
        new THREE.Mesh(
            ringGeometry.clone(),
            ringMaterial.clone()
        );

    ring2.rotation.x =
        Math.PI / 3;

    ring2.rotation.z =
        Math.PI / 5;

    ring2.scale.setScalar(
        0.75
    );

    group.add(
        ring2
    );


    /* --------------------------------------------------------
       Data beams
       -------------------------------------------------------- */

    const beamMaterial =
        new THREE.LineBasicMaterial({

            color:
                0x65ffff,

            transparent:
                true,

            opacity:
                0.35,

            depthWrite:
                false

        });


    const beamGeometry =
        new THREE.BufferGeometry().setFromPoints([

            new THREE.Vector3(
                0,
                -1.8,
                0
            ),

            new THREE.Vector3(
                0,
                1.8,
                0
            )

        ]);


    const beam =
        new THREE.Line(
            beamGeometry,
            beamMaterial
        );

    group.add(
        beam
    );


    /* --------------------------------------------------------
       User data
       -------------------------------------------------------- */

    group.userData =
        {

            id:
                data.id,

            objectType:
                data.object_type,

            selected:
                false,

            grabbed:
                false,

            phase:
                Math.random() *
                Math.PI *
                2,

            baseRotation:
                0

        };


    scene.add(
        group
    );


    virtualObjects.set(
        data.id,
        group
    );


    return group;

}


/* ============================================================
   UPDATE OBJECT
   ============================================================ */

function updateHologram(
    data
) {

    let object =
        virtualObjects.get(
            data.id
        );


    if (!object) {

        object =
            createHologram(
                data
            );

    }


    /* --------------------------------------------------------
       Position
       -------------------------------------------------------- */

    object.position.x =
        normalizedXToWorld(
            data.x
        );

    object.position.y =
        normalizedYToWorld(
            data.y
        );


    /* --------------------------------------------------------
       Scale
       -------------------------------------------------------- */

    const targetScale =
        data.scale || 1;

    object.scale.setScalar(
        targetScale
    );


    /* --------------------------------------------------------
       Rotation
       -------------------------------------------------------- */

    object.rotation.y =
        THREE.MathUtils.degToRad(
            data.rotation || 0
        );


    /* --------------------------------------------------------
       Selection
       -------------------------------------------------------- */

    const selected =
        Number(data.id) ===
        Number(selectedObjectId);


    object.userData.selected =
        selected;

    object.userData.grabbed =
        Number(data.id) ===
        Number(grabbedObjectId);


    const mesh =
        object.children[0];

    const wire =
        object.children[1];

    const glow =
        object.children[2];


    if (selected) {

        mesh.material.color.set(
            0x8fffff
        );

        mesh.material.emissive.set(
            0x00ffff
        );

        mesh.material.emissiveIntensity =
            2.8;

        wire.material.color.set(
            0xffffff
        );

        wire.material.opacity =
            1.0;

        glow.material.opacity =
            0.15;

    } else {

        mesh.material.color.set(
            0x00dfff
        );

        mesh.material.emissive.set(
            0x00bcd4
        );

        mesh.material.emissiveIntensity =
            1.6;

        wire.material.color.set(
            0x4defff
        );

        wire.material.opacity =
            0.72;

        glow.material.opacity =
            0.07;

    }

}


/* ============================================================
   NORMALIZED CAMERA -> 3D WORLD
   ============================================================ */

function normalizedXToWorld(
    x
) {

    return (
        (x - 0.5) *
        7.2
    );

}


function normalizedYToWorld(
    y
) {

    return (
        -(y - 0.5) *
        4.0
    );

}


/* ============================================================
   REMOVE OLD OBJECTS
   ============================================================ */

function synchronizeObjects(
    objects
) {

    const active =
        new Set();

    for (
        const data of objects
    ) {

        active.add(
            Number(data.id)
        );

        updateHologram(
            data
        );

    }


    for (
        const [
            id,
            object
        ] of virtualObjects
    ) {

        if (
            !active.has(
                Number(id)
            )
        ) {

            scene.remove(
                object
            );

            object.traverse(
                child => {

                    if (
                        child.geometry
                    ) {

                        child.geometry.dispose();

                    }

                    if (
                        child.material
                    ) {

                        child.material.dispose();

                    }

                }
            );

            virtualObjects.delete(
                id
            );

        }

    }

}


/* ============================================================
   POINTER
   ============================================================ */

function updatePointer(
    point
) {

    const reticle =
        document.getElementById(
            "reticle"
        );


    if (!point) {

        reticle.classList.add(
            "hidden"
        );

        return;

    }


    const x =
        point.x;

    const y =
        point.y;


    reticle.classList.remove(
        "hidden"
    );


    reticle.style.left =
        `${x}px`;

    reticle.style.top =
        `${y}px`;


    pointerScreen.set(
        x,
        y
    );


    const ndcX =
        (
            x /
            window.innerWidth
        ) *
        2 -
        1;


    const ndcY =
        -(
            y /
            window.innerHeight
        ) *
        2 +
        1;


    pointerNDC.set(
        ndcX,
        ndcY
    );

}


/* ============================================================
   THREE RAYCAST
   ============================================================ */

function raycastVirtualObjects() {

    raycaster.setFromCamera(
        pointerNDC,
        camera
    );


    const meshes = [];


    for (
        const object
        of virtualObjects.values()
    ) {

        const mesh =
            object.children[0];

        meshes.push(
            mesh
        );

    }


    const hits =
        raycaster.intersectObjects(
            meshes,
            true
        );


    if (!hits.length) {

        return null;

    }


    let hit =
        hits[0].object;


    while (
        hit &&
        hit.parent
    ) {

        if (
            hit.userData &&
            hit.userData.id
        ) {

            return hit;

        }

        hit =
            hit.parent;

    }


    return hits[0].object;

}


/* ============================================================
   WEBSOCKET
   ============================================================ */

function connect() {

    const protocol =
        location.protocol === "https:"
            ? "wss:"
            : "ws:";


    socket =
        new WebSocket(
            `${protocol}//${location.host}/ws/ar`
        );


    socket.onopen =
        () => {

            setStatus(
                "WEBGL CONNECTED"
            );


            socket.send(
                JSON.stringify({
                    type:
                        "ar.ready",

                    data:
                        {
                            renderer:
                                "Three.js WebGL",

                            version:
                                "real-3d"
                        }
                })
            );

        };


    socket.onmessage =
        event => {

            try {

                const message =
                    JSON.parse(
                        event.data
                    );


                handleMessage(
                    message
                );

            } catch (
                error
            ) {

                console.error(
                    error
                );

            }

        };


    socket.onclose =
        () => {

            setStatus(
                "RECONNECTING..."
            );


            setTimeout(
                connect,
                1000
            );

        };


    socket.onerror =
        error => {

            console.warn(
                "AR WebSocket error",
                error
            );

        };

}


/* ============================================================
   MESSAGE HANDLER
   ============================================================ */

function handleMessage(
    message
) {

    if (
        message.type ===
        "ar.connected"
    ) {

        setStatus(
            "JARVIS WEBGL ONLINE"
        );

        hideLoading();

        return;

    }


    if (
        message.type ===
        "camera.frame"
    ) {

        cameraImage.src =
            "data:image/jpeg;base64," +
            message.data;

        return;

    }


    if (
        message.type ===
        "vision.state"
    ) {

        handleVisionState(
            message.data
        );

    }

}


/* ============================================================
   VISION STATE
   ============================================================ */

function handleVisionState(
    state
) {

    lastStateTime =
        performance.now();


    currentGesture =
        state.gesture ||
        "unknown";


    createMode =
        Boolean(
            state.createMode
        );


    selectedObjectId =
        state.selectedId;


    grabbedObjectId =
        state.grabbedId;


    updatePointer(
        state.pointer
    );


    synchronizeObjects(
        state.virtualObjects ||
        []
    );


    updateHUD(
        state
    );


    updateKeyboard(
        state.pointer,
        state.gesture
    );

}


/* ============================================================
   HUD
   ============================================================ */

function updateHUD(
    state
) {

    const gesture =
        document.getElementById(
            "gesture"
        );

    const mode =
        document.getElementById(
            "mode"
        );


    gesture.textContent =
        "GESTURE // " +
        (
            state.gesture ||
            "UNKNOWN"
        ).toUpperCase();


    if (
        state.grabbedId !== null &&
        state.grabbedId !== undefined
    ) {

        mode.textContent =
            "3D OBJECT // GRABBING";

    } else if (
        state.createMode
    ) {

        mode.textContent =
            "PEACE // CREATE MODE";

    } else if (
        state.selectedId !== null &&
        state.selectedId !== undefined
    ) {

        mode.textContent =
            "3D OBJECT // SELECTED";

    } else {

        mode.textContent =
            "SYSTEM READY";

    }


    const create =
        document.getElementById(
            "createMode"
        );


    if (state.createMode) {

        create.classList.remove(
            "hidden"
        );

    } else {

        create.classList.add(
            "hidden"
        );

    }

}


/* ============================================================
   STATUS
   ============================================================ */

function setStatus(
    text
) {

    document.getElementById(
        "status"
    ).textContent =
        text;

}


function hideLoading() {

    const loading =
        document.getElementById(
            "loading"
        );

    loading.style.opacity =
        "0";

    loading.style.pointerEvents =
        "none";

    setTimeout(
        () => {

            loading.style.display =
                "none";

        },
        500
    );

}


/* ============================================================
   KEYBOARD
   ============================================================ */

const keyboardRows = [

    [
        "1","2","3","4","5",
        "6","7","8","9","0"
    ],

    [
        "Q","W","E","R","T",
        "Y","U","I","O","P"
    ],

    [
        "A","S","D","F","G",
        "H","J","K","L"
    ],

    [
        "Z","X","C","V","B",
        "N","M"
    ],

    [
        "SPACE",
        "BACK",
        "ENTER"
    ]

];


let keyboardText = "";


function buildKeyboard() {

    const container =
        document.getElementById(
            "keys"
        );


    container.innerHTML = "";


    keyboardRows.forEach(
        row => {

            const rowElement =
                document.createElement(
                    "div"
                );

            rowElement.className =
                "key-row";


            row.forEach(
                key => {

                    const element =
                        document.createElement(
                            "div"
                        );

                    element.className =
                        "key";

                    element.dataset.key =
                        key;

                    element.textContent =
                        key;

                    if (
                        key === "SPACE"
                    ) {

                        element.style.width =
                            "120px";

                    } else if (
                        key === "BACK"
                    ) {

                        element.style.width =
                            "70px";

                    } else if (
                        key === "ENTER"
                    ) {

                        element.style.width =
                            "75px";

                    }


                    rowElement.appendChild(
                        element
                    );

                }
            );


            container.appendChild(
                rowElement
            );

        }
    );

}


function updateKeyboard(
    pointer,
    gesture
) {

    const keys =
        document.querySelectorAll(
            ".key"
        );


    keys.forEach(
        key => {

            key.classList.remove(
                "hover"
            );

        }
    );


    if (
        !pointer
    ) {

        return;

    }


    const rect =
        document
            .getElementById(
                "keyboard"
            )
            .getBoundingClientRect();


    if (
        pointer.x < rect.left ||
        pointer.x > rect.right ||
        pointer.y < rect.top ||
        pointer.y > rect.bottom
    ) {

        return;

    }


    const target =
        document.elementFromPoint(
            pointer.x,
            pointer.y
        );


    if (
        !target ||
        !target.classList.contains(
            "key"
        )
    ) {

        return;

    }


    target.classList.add(
        "hover"
    );


    if (
        gesture === "pinch"
    ) {

        pressKey(
            target.dataset.key
        );

    }

}


let lastKeyboardPress =
    0;


function pressKey(
    key
) {

    const now =
        performance.now();


    if (
        now - lastKeyboardPress <
        220
    ) {

        return;

    }


    lastKeyboardPress =
        now;


    if (
        key === "SPACE"
    ) {

        keyboardText +=
            " ";

    } else if (
        key === "BACK"
    ) {

        keyboardText =
            keyboardText.slice(
                0,
                -1
            );

    } else if (
        key === "ENTER"
    ) {

        keyboardText +=
            "\n";

    } else {

        keyboardText +=
            key;

    }


    keyboardText =
        keyboardText.slice(
            -40
        );


    document.getElementById(
        "keyboard-text"
    ).textContent =
        keyboardText;


    if (
        socket &&
        socket.readyState ===
        WebSocket.OPEN
    ) {

        socket.send(
            JSON.stringify({

                type:
                    "keyboard.input",

                data:
                    {
                        key,
                        text:
                            keyboardText
                    }

            })
        );

    }

}


/* ============================================================
   ANIMATION
   ============================================================ */

function animate() {

    requestAnimationFrame(
        animate
    );


    const elapsed =
        clock.getElapsedTime();


    /* --------------------------------------------------------
       Particle movement
       -------------------------------------------------------- */

    if (particles) {

        particles.rotation.y =
            elapsed *
            0.015;

        particles.rotation.x =
            Math.sin(
                elapsed * 0.1
            ) *
            0.03;

    }


    /* --------------------------------------------------------
       Animate holograms
       -------------------------------------------------------- */

    for (
        const object
        of virtualObjects.values()
    ) {

        const data =
            object.userData;


        const mesh =
            object.children[0];

        const wire =
            object.children[1];

        const glow =
            object.children[2];

        const ring =
            object.children[3];

        const ring2 =
            object.children[4];


        /* -----------------------------------------------
           Don't override user rotation.
           Add idle rotation around Y.
           ----------------------------------------------- */

        if (
            !data.grabbed
        ) {

            mesh.rotation.y +=
                0.003;

            wire.rotation.y +=
                0.003;

        }


        ring.rotation.z +=
            0.008;

        ring2.rotation.y +=
            0.006;


        const pulse =
            1 +
            Math.sin(
                elapsed * 2.2 +
                data.phase
            ) *
            0.035;


        glow.scale.setScalar(
            1.10 *
            pulse
        );


        glow.material.opacity =
            data.selected
                ? 0.17
                : 0.07;


        /* -----------------------------------------------
           Selected animation
           ----------------------------------------------- */

        if (
            data.selected
        ) {

            ring.scale.setScalar(
                1.0 +
                Math.sin(
                    elapsed * 3
                ) *
                0.08
            );

        }

    }


    renderer.render(
        scene,
        camera
    );

}


/* ============================================================
   RESIZE
   ============================================================ */

function resize() {

    camera.aspect =
        window.innerWidth /
        window.innerHeight;


    camera.updateProjectionMatrix();


    renderer.setSize(
        window.innerWidth,
        window.innerHeight
    );

}


init();