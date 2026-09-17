import * as THREE from "three";

const cameraVideo = document.getElementById("camera");
const canvas = document.getElementById("arCanvas");

const handValue = document.getElementById("handValue");
const gestureValue = document.getElementById("gestureValue");
const targetValue = document.getElementById("targetValue");
const selectedValue = document.getElementById("selectedValue");

const connectionStatus =
    document.getElementById("connectionStatus");

const commandText =
    document.getElementById("commandText");

const keyboard =
    document.getElementById("keyboard");

const typedText =
    document.getElementById("typedText");


// ============================================================
// THREE.JS
// ============================================================

const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true
});

renderer.setPixelRatio(
    Math.min(window.devicePixelRatio, 2)
);

renderer.setSize(
    window.innerWidth,
    window.innerHeight
);

renderer.setClearColor(0x000000, 0);


const scene = new THREE.Scene();


const camera = new THREE.PerspectiveCamera(
    45,
    window.innerWidth / window.innerHeight,
    0.01,
    100
);

camera.position.set(0, 0, 6);


const ambientLight = new THREE.AmbientLight(
    0xffffff,
    1.5
);

scene.add(ambientLight);


const directionalLight = new THREE.DirectionalLight(
    0xffffff,
    2
);

directionalLight.position.set(2, 4, 5);

scene.add(directionalLight);


// ============================================================
// HOLOGRAPHIC OBJECTS
// ============================================================

const objects = new Map();

let selectedObject = null;

let hoveredObject = null;


function createHologramCube(id = "cube-1") {

    const geometry =
        new THREE.BoxGeometry(1.15, 1.15, 1.15);

    const material =
        new THREE.MeshPhysicalMaterial({
            color: 0x00d9ff,
            emissive: 0x003b55,
            transparent: true,
            opacity: 0.72,
            roughness: 0.2,
            metalness: 0.4
        });

    const cube =
        new THREE.Mesh(
            geometry,
            material
        );

    cube.position.set(
        -1.4,
        0.3,
        0
    );

    cube.userData.virtualId = id;

    scene.add(cube);

    objects.set(id, cube);

    addHologramEdges(cube);

    return cube;
}


function createHologramSphere(id = "sphere-1") {

    const geometry =
        new THREE.SphereGeometry(
            0.75,
            32,
            32
        );

    const material =
        new THREE.MeshPhysicalMaterial({
            color: 0x8a5cff,
            emissive: 0x24105c,
            transparent: true,
            opacity: 0.68,
            roughness: 0.15,
            metalness: 0.3
        });

    const sphere =
        new THREE.Mesh(
            geometry,
            material
        );

    sphere.position.set(
        1.2,
        0.4,
        0
    );

    sphere.userData.virtualId = id;

    scene.add(sphere);

    objects.set(id, sphere);

    addHologramEdges(sphere);

    return sphere;
}


function addHologramEdges(mesh) {

    const edges =
        new THREE.EdgesGeometry(
            mesh.geometry
        );

    const lineMaterial =
        new THREE.LineBasicMaterial({
            color: 0x66eeff,
            transparent: true,
            opacity: 0.9
        });

    const lines =
        new THREE.LineSegments(
            edges,
            lineMaterial
        );

    lines.scale.setScalar(1.015);

    mesh.add(lines);
}


const cube =
    createHologramCube();

const sphere =
    createHologramSphere();


// ============================================================
// HOLOGRAM RINGS
// ============================================================

function addRing(object) {

    const geometry =
        new THREE.RingGeometry(
            0.82,
            0.85,
            64
        );

    const material =
        new THREE.MeshBasicMaterial({
            color: 0x00eaff,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });

    const ring =
        new THREE.Mesh(
            geometry,
            material
        );

    ring.rotation.x =
        Math.PI / 2;

    ring.position.y =
        -0.8;

    object.add(ring);

    return ring;
}

addRing(cube);
addRing(sphere);


// ============================================================
// RAYCASTING
// ============================================================

const raycaster =
    new THREE.Raycaster();

const pointer =
    new THREE.Vector2(
        0,
        0
    );


function setPointer(
    normalizedX,
    normalizedY
) {

    pointer.x =
        normalizedX * 2 - 1;

    pointer.y =
        -(normalizedY * 2 - 1);
}


function findVirtualObject(
    normalizedX,
    normalizedY
) {

    setPointer(
        normalizedX,
        normalizedY
    );

    raycaster.setFromCamera(
        pointer,
        camera
    );

    const meshes =
        Array.from(objects.values());

    const hits =
        raycaster.intersectObjects(
            meshes,
            true
        );

    if (!hits.length) {
        return null;
    }

    let object =
        hits[0].object;

    while (
        object &&
        !object.userData.virtualId
    ) {
        object =
            object.parent;
    }

    return object || null;
}


// ============================================================
// HAND STATE
// ============================================================

const handState = {

    left: {
        visible: false,
        x: 0.5,
        y: 0.5,
        gesture: "none",
        pinch: false
    },

    right: {
        visible: false,
        x: 0.5,
        y: 0.5,
        gesture: "none",
        pinch: false
    }
};


let activeHand = "right";

let dragging = false;

let dragObject = null;

let dragDepth = 0;


// ============================================================
// POINTER → WORLD
// ============================================================

function pointerToWorld(
    x,
    y,
    depth = 0
) {

    setPointer(x, y);

    const vector =
        new THREE.Vector3(
            pointer.x,
            pointer.y,
            0.5
        );

    vector.unproject(camera);

    const direction =
        vector
            .sub(camera.position)
            .normalize();

    const distance =
        (depth - camera.position.z) /
        direction.z;

    return camera.position
        .clone()
        .add(
            direction.multiplyScalar(
                distance
            )
        );
}


// ============================================================
// DRAGGING
// ============================================================

function startDrag(
    object,
    x,
    y
) {

    if (!object) {
        return;
    }

    selectedObject = object;

    dragObject = object;

    dragging = true;

    dragDepth =
        object.position.z;

    selectedValue.textContent =
        object.userData.virtualId;

    commandText.textContent =
        "GRABBED " +
        object.userData.virtualId;

    sendEvent(
        "three.object_selected",
        {
            object_id:
                object.userData.virtualId
        }
    );
}


function updateDrag(
    x,
    y
) {

    if (
        !dragging ||
        !dragObject
    ) {
        return;
    }

    const position =
        pointerToWorld(
            x,
            y,
            dragDepth
        );

    dragObject.position.x =
        position.x;

    dragObject.position.y =
        position.y;

    sendEvent(
        "three.object_moved",
        {
            object_id:
                dragObject.userData.virtualId,

            x:
                dragObject.position.x,

            y:
                dragObject.position.y,

            z:
                dragObject.position.z
        }
    );
}


function endDrag() {

    if (!dragging) {
        return;
    }

    dragging = false;

    dragObject = null;

    commandText.textContent =
        "OBJECT RELEASED";
}


// ============================================================
// TARGET PROCESSING
// ============================================================

function processPointer(
    x,
    y,
    gesture,
    pinch
) {

    const object =
        findVirtualObject(
            x,
            y
        );

    hoveredObject =
        object;

    if (object) {

        targetValue.textContent =
            object.userData.virtualId;

        highlightObject(
            object,
            true
        );

    } else {

        targetValue.textContent =
            "NONE";
    }


    if (
        pinch &&
        !dragging &&
        object
    ) {

        startDrag(
            object,
            x,
            y
        );
    }


    if (
        pinch &&
        dragging
    ) {

        updateDrag(
            x,
            y
        );
    }


    if (
        !pinch &&
        dragging
    ) {

        endDrag();
    }
}


// ============================================================
// HIGHLIGHTING
// ============================================================

function highlightObject(
    object,
    active
) {

    if (
        !object.material ||
        !object.material.emissive
    ) {
        return;
    }

    if (active) {

        object.material.emissiveIntensity =
            2;

        object.scale.setScalar(
            1.05
        );

    } else {

        object.material.emissiveIntensity =
            1;

        object.scale.setScalar(
            1
        );
    }
}


function clearHighlights() {

    for (
        const object
        of objects.values()
    ) {

        if (
            object === selectedObject
        ) {
            continue;
        }

        highlightObject(
            object,
            false
        );
    }
}


// ============================================================
// TWO-HAND CONTROL
// ============================================================

let twoHandActive = false;

let previousTwoHandDistance = null;

let previousTwoHandAngle = null;


function processTwoHands() {

    const left =
        handState.left;

    const right =
        handState.right;


    if (
        !left.visible ||
        !right.visible
    ) {

        twoHandActive = false;

        previousTwoHandDistance =
            null;

        previousTwoHandAngle =
            null;

        return;
    }


    const dx =
        right.x - left.x;

    const dy =
        right.y - left.y;

    const distance =
        Math.sqrt(
            dx * dx +
            dy * dy
        );

    const angle =
        Math.atan2(
            dy,
            dx
        );


    if (
        previousTwoHandDistance === null
    ) {

        previousTwoHandDistance =
            distance;

        previousTwoHandAngle =
            angle;

        twoHandActive = true;

        return;
    }


    if (
        !selectedObject
    ) {

        previousTwoHandDistance =
            distance;

        previousTwoHandAngle =
            angle;

        return;
    }


    const scaleRatio =
        distance /
        previousTwoHandDistance;


    if (
        Number.isFinite(scaleRatio) &&
        Math.abs(scaleRatio - 1) > 0.005
    ) {

        const newScale =
            THREE.MathUtils.clamp(
                selectedObject.scale.x *
                    scaleRatio,
                0.25,
                4
            );

        selectedObject.scale.setScalar(
            newScale
        );
    }


    let angleDelta =
        angle -
        previousTwoHandAngle;


    while (
        angleDelta > Math.PI
    ) {
        angleDelta -=
            Math.PI * 2;
    }


    while (
        angleDelta < -Math.PI
    ) {
        angleDelta +=
            Math.PI * 2;
    }


    selectedObject.rotation.z +=
        angleDelta;


    previousTwoHandDistance =
        distance;

    previousTwoHandAngle =
        angle;
}


// ============================================================
// KEYBOARD
// ============================================================

let typingMode = false;

let textBuffer = "";


function showKeyboard() {

    typingMode = true;

    keyboard.classList.remove(
        "hidden"
    );

    commandText.textContent =
        "VIRTUAL KEYBOARD";
}


function hideKeyboard() {

    typingMode = false;

    keyboard.classList.add(
        "hidden"
    );
}


function updateKeyboardDisplay() {

    typedText.textContent =
        textBuffer;
}


function typeKey(key) {

    if (key === "BACKSPACE") {

        textBuffer =
            textBuffer.slice(
                0,
                -1
            );

    } else if (
        key === "SPACE"
    ) {

        textBuffer += " ";

    } else if (
        key === "ENTER"
    ) {

        sendEvent(
            "user.command",
            {
                text:
                    textBuffer
            }
        );

        commandText.textContent =
            "SENT: " +
            textBuffer;

        textBuffer = "";

    } else {

        textBuffer += key;
    }

    updateKeyboardDisplay();
}


for (
    const button
    of document.querySelectorAll(
        "#keyboard button"
    )
) {

    button.addEventListener(
        "click",
        () => {

            typeKey(
                button.dataset.key
            );

            button.classList.add(
                "pressed"
            );

            setTimeout(
                () => {
                    button.classList.remove(
                        "pressed"
                    );
                },
                100
            );
        }
    );
}


// ============================================================
// PINCH KEYBOARD SELECTION
// ============================================================

let lastKeyboardKey = null;

let keyboardPinchLock = false;


function processKeyboard(
    x,
    y,
    pinch
) {

    if (!typingMode) {
        return;
    }

    const element =
        document.elementFromPoint(
            x * window.innerWidth,
            y * window.innerHeight
        );


    const button =
        element?.closest(
            "#keyboard button"
        );


    document
        .querySelectorAll(
            "#keyboard button"
        )
        .forEach(
            b =>
                b.classList.remove(
                    "hover"
                )
        );


    if (!button) {

        lastKeyboardKey =
            null;

        return;
    }


    button.classList.add(
        "hover"
    );


    if (
        pinch &&
        !keyboardPinchLock
    ) {

        keyboardPinchLock =
            true;

        lastKeyboardKey =
            button.dataset.key;

        typeKey(
            button.dataset.key
        );
    }


    if (!pinch) {

        keyboardPinchLock =
            false;
    }
}


// ============================================================
// AIR DRAWING
// ============================================================

const drawingPoints = [];

let drawingEnabled = false;

let currentDrawing = null;


function startDrawing() {

    drawingEnabled = true;

    commandText.textContent =
        "AIR DRAWING";

    currentDrawing = new THREE.Line(
        new THREE.BufferGeometry(),
        new THREE.LineBasicMaterial({
            color: 0x00ffff,
            transparent: true,
            opacity: 0.9
        })
    );

    scene.add(
        currentDrawing
    );

    drawingPoints.length = 0;
}


function updateDrawing(
    x,
    y
) {

    if (
        !drawingEnabled ||
        !currentDrawing
    ) {
        return;
    }

    const point =
        pointerToWorld(
            x,
            y,
            0
        );

    drawingPoints.push(
        point.clone()
    );


    if (
        drawingPoints.length < 2
    ) {
        return;
    }


    const positions =
        new Float32Array(
            drawingPoints.length * 3
        );


    for (
        let i = 0;
        i < drawingPoints.length;
        i++
    ) {

        positions[i * 3] =
            drawingPoints[i].x;

        positions[i * 3 + 1] =
            drawingPoints[i].y;

        positions[i * 3 + 2] =
            drawingPoints[i].z;
    }


    currentDrawing.geometry.dispose();

    currentDrawing.geometry =
        new THREE.BufferGeometry();

    currentDrawing.geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
            positions,
            3
        )
    );
}


function stopDrawing() {

    drawingEnabled = false;

    currentDrawing = null;
}


// ============================================================
// WEBSOCKET
// ============================================================

let socket = null;

let reconnectTimer = null;


function connectSocket() {

    try {

        socket =
            new WebSocket(
                "ws://127.0.0.1:8000/ws/vision"
            );


        socket.onopen = () => {

            connectionStatus.textContent =
                "JARVIS ONLINE";

            connectionStatus.className =
                "status online";

            sendEvent(
                "vision.client_connected",
                {}
            );
        };


        socket.onclose = () => {

            connectionStatus.textContent =
                "RECONNECTING";

            connectionStatus.className =
                "status offline";

            clearTimeout(
                reconnectTimer
            );

            reconnectTimer =
                setTimeout(
                    connectSocket,
                    1500
                );
        };


        socket.onerror = () => {

            connectionStatus.textContent =
                "OFFLINE";
        };


        socket.onmessage = event => {

            try {

                const message =
                    JSON.parse(
                        event.data
                    );

                handleServerEvent(
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

    } catch (
        error
    ) {

        console.error(
            error
        );
    }
}


function sendEvent(
    type,
    data
) {

    if (
        !socket ||
        socket.readyState !==
            WebSocket.OPEN
    ) {
        return;
    }


    socket.send(
        JSON.stringify({
            type,
            data
        })
    );
}


function handleServerEvent(
    message
) {

    if (
        message.type ===
        "jarvis.command"
    ) {

        commandText.textContent =
            message.data?.text ||
            "";
    }
}


// ============================================================
// PYTHON VISION EVENTS
// ============================================================

function handleVisionEvent(
    message
) {

    const type =
        message.type;

    const data =
        message.data || {};


    if (
        type ===
        "vision.pointing"
    ) {

        const hand =
            data.hand?.toLowerCase() ===
            "left"
                ? "left"
                : "right";


        activeHand =
            hand;


        handState[hand].visible =
            true;

        handState[hand].x =
            data.x;

        handState[hand].y =
            data.y;

        handState[hand].gesture =
            data.gesture ||
            "point";


        processPointer(
            data.x,
            data.y,
            data.gesture ||
                "point",
            handState[hand].pinch
        );


        if (
            typingMode
        ) {

            processKeyboard(
                data.x,
                data.y,
                handState[hand].pinch
            );
        }
    }


    if (
        type ===
        "hand.gesture"
    ) {

        const hand =
            data.hand?.toLowerCase() ===
            "left"
                ? "left"
                : "right";


        activeHand =
            hand;


        handState[hand].gesture =
            data.current ||
            data.raw ||
            "none";


        handValue.textContent =
            data.hand ||
            "NONE";

        gestureValue.textContent =
            handState[hand].gesture;


        if (
            handState[hand].gesture ===
            "pinch"
        ) {

            handState[hand].pinch =
                true;

        } else {

            handState[hand].pinch =
                false;
        }
    }


    if (
        type ===
        "hand.pinch_start"
    ) {

        const hand =
            data.hand?.toLowerCase() ===
            "left"
                ? "left"
                : "right";

        handState[hand].pinch =
            true;
    }


    if (
        type ===
        "hand.pinch_end"
    ) {

        const hand =
            data.hand?.toLowerCase() ===
            "left"
                ? "left"
                : "right";

        handState[hand].pinch =
            false;

        if (
            hand === activeHand
        ) {

            endDrag();
        }
    }


    if (
        type ===
        "vision.object_selected"
    ) {

        selectedValue.textContent =
            data.label ||
            data.object_id ||
            "OBJECT";

        commandText.textContent =
            "SELECTED " +
            (
                data.label ||
                "OBJECT"
            );
    }
}


function handleIncoming(
    message
) {

    if (
        message.type?.startsWith(
            "vision."
        ) ||
        message.type?.startsWith(
            "hand."
        )
    ) {

        handleVisionEvent(
            message
        );
    }
}


// Replace the normal socket message handler
// with our unified handler.
const originalConnectSocket =
    connectSocket;


// ============================================================
// CAMERA
// ============================================================

async function startCamera() {

    try {

        const stream =
            await navigator.mediaDevices
                .getUserMedia({
                    video: {
                        facingMode:
                            "user",

                        width: {
                            ideal: 1280
                        },

                        height: {
                            ideal: 720
                        }
                    },

                    audio: false
                });


        cameraVideo.srcObject =
            stream;


        await cameraVideo.play();


        commandText.textContent =
            "CAMERA ONLINE";

    } catch (
        error
    ) {

        console.error(
            "Camera error:",
            error
        );

        commandText.textContent =
            "CAMERA ACCESS REQUIRED";
    }
}


// ============================================================
// SERVER MESSAGE PATCH
// ============================================================

function setupSocketMessageHandling() {

    if (!socket) {
        return;
    }

    socket.onmessage = event => {

        try {

            const message =
                JSON.parse(
                    event.data
                );

            handleIncoming(
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
}


// ============================================================
// ANIMATION
// ============================================================

const clock =
    new THREE.Clock();


function animate() {

    requestAnimationFrame(
        animate
    );


    const elapsed =
        clock.getElapsedTime();


    cube.rotation.x +=
        0.003;

    cube.rotation.y +=
        0.005;


    sphere.rotation.y -=
        0.004;


    for (
        const object
        of objects.values()
    ) {

        const ring =
            object.children.find(
                child =>
                    child.geometry instanceof
                    THREE.RingGeometry
            );


        if (ring) {

            ring.rotation.z =
                elapsed * 0.8;
        }
    }


    processTwoHands();


    clearHighlights();


    renderer.render(
        scene,
        camera
    );
}


// ============================================================
// RESIZE
// ============================================================

window.addEventListener(
    "resize",
    () => {

        camera.aspect =
            window.innerWidth /
            window.innerHeight;

        camera.updateProjectionMatrix();


        renderer.setSize(
            window.innerWidth,
            window.innerHeight
        );
    }
);


// ============================================================
// KEYBOARD TOGGLE
// ============================================================

window.addEventListener(
    "keydown",
    event => {

        if (
            event.key ===
            "k"
        ) {

            if (
                typingMode
            ) {

                hideKeyboard();

            } else {

                showKeyboard();
            }
        }


        if (
            event.key ===
            "d"
        ) {

            if (
                drawingEnabled
            ) {

                stopDrawing();

            } else {

                startDrawing();
            }
        }
    }
);


// ============================================================
// START
// ============================================================

async function start() {

    await startCamera();

    connectSocket();

    setupSocketMessageHandling();

    animate();
}


start();