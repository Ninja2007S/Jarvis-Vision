/* Jarvis client — Phase 2.
   Adds push-to-talk voice on top of the Phase 1 text socket: a mic capture
   pipeline that streams 16kHz PCM to the core, and a playback queue that
   plays synthesized audio back gaplessly as sentences arrive. */

import {
    Jarvis3DScene
} from "./three/scene.js";

const thread = document.getElementById("thread");
const empty = document.getElementById("empty");
const form = document.getElementById("compose");
const input = document.getElementById("input");
const send = document.getElementById("send");
const stateLabel = document.getElementById("state");
const dot = document.getElementById("dot");
const nameEl = document.getElementById("name");
const talkButton = document.getElementById("talk");
const talkLabel = document.getElementById("talk-label");


// ---- 3D Jarvis scene ---------------------------------------------------

const threeContainer =
    document.getElementById(
        "three-container"
    );

let jarvis3D = null;

if (threeContainer) {

    jarvis3D =
        new Jarvis3DScene(
            threeContainer
        );

    // Temporary test cube
    const cube =
        jarvis3D.createCube(
            "test-cube"
        );

    cube.position.set(
        0,
        0,
        0
    );
}


// ---- socket -------------------------------------------------------------

let socket = null;
let reconnectDelay = 500;
let current = null;
let keepalive = null;


// ---- transcript -------------------------------------------------------

function setState(value, live) {
    stateLabel.textContent = value;
    document.body.dataset.state = value;
    dot.dataset.live = live;
}

function addTurn(kind, text) {
    if (empty) empty.remove();

    const p = document.createElement("p");

    p.className = `turn ${kind}`;
    p.textContent = text;

    thread.appendChild(p);

    thread.scrollTop =
        thread.scrollHeight;

    return p;
}


// ---- playback: a small gapless queue for streamed TTS -----------------

const playback = {
    ctx: null,
    nextStart: 0,
    pendingRate: null,
};

function playbackContext() {
    if (!playback.ctx) {
        playback.ctx =
            new (
                window.AudioContext ||
                window.webkitAudioContext
            )();
    }

    return playback.ctx;
}

function enqueuePCM(
    bytes,
    sampleRate
) {
    const ctx =
        playbackContext();

    const pcm16 =
        new Int16Array(
            bytes.buffer,
            bytes.byteOffset,
            bytes.byteLength / 2
        );

    const buffer =
        ctx.createBuffer(
            1,
            pcm16.length,
            sampleRate
        );

    const channel =
        buffer.getChannelData(0);

    for (
        let i = 0;
        i < pcm16.length;
        i++
    ) {
        channel[i] =
            pcm16[i] / 32768;
    }

    const source =
        ctx.createBufferSource();

    source.buffer = buffer;

    source.connect(
        ctx.destination
    );

    const now =
        ctx.currentTime;

    const startAt =
        Math.max(
            now,
            playback.nextStart
        );

    source.start(
        startAt
    );

    playback.nextStart =
        startAt +
        buffer.duration;
}


// ---- mic capture: AudioWorklet downsamples to 16kHz Int16 PCM ---------

const mic = {
    ctx: null,
    node: null,
    stream: null,
    ready: false,
};

async function armMic() {

    if (mic.ready) {
        return true;
    }

    try {

        mic.stream =
            await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    channelCount: 1,
                },
            });

        mic.ctx =
            new (
                window.AudioContext ||
                window.webkitAudioContext
            )();

        await mic.ctx.audioWorklet.addModule(
            "/worklets/mic-capture.js"
        );

        const source =
            mic.ctx.createMediaStreamSource(
                mic.stream
            );

        mic.node =
            new AudioWorkletNode(
                mic.ctx,
                "mic-capture"
            );

        source.connect(
            mic.node
        );

        mic.node.port.onmessage =
            (event) => {

                if (
                    socket &&
                    socket.readyState ===
                        WebSocket.OPEN &&
                    talkButton.dataset.armed ===
                        "yes"
                ) {

                    socket.send(
                        event.data
                    );
                }
            };

        mic.ready = true;

        return true;

    } catch (err) {

        addTurn(
            "fault",
            "Couldn't reach the microphone. Check the browser's permission for this site."
        );

        return false;
    }
}

async function startTalking() {

    const ok =
        await armMic();

    if (
        !ok ||
        !socket ||
        socket.readyState !==
            WebSocket.OPEN
    ) {
        return;
    }

    if (
        mic.ctx.state ===
        "suspended"
    ) {
        await mic.ctx.resume();
    }

    talkButton.dataset.armed =
        "yes";

    socket.send(
        JSON.stringify({
            type: "voice_start",
        })
    );
}

function stopTalking() {

    if (
        talkButton.dataset.armed !==
        "yes"
    ) {
        return;
    }

    talkButton.dataset.armed =
        "no";

    if (
        socket &&
        socket.readyState ===
            WebSocket.OPEN
    ) {

        socket.send(
            JSON.stringify({
                type: "voice_end",
            })
        );
    }
}

talkButton.addEventListener(
    "pointerdown",
    (event) => {

        event.preventDefault();

        talkButton.setPointerCapture(
            event.pointerId
        );

        startTalking();
    }
);

[
    "pointerup",
    "pointercancel",
    "pointerleave",
].forEach(
    (eventName) =>
        talkButton.addEventListener(
            eventName,
            stopTalking
        )
);


// ---- socket -------------------------------------------------------------

function connect() {

    const scheme =
        location.protocol ===
        "https:"
            ? "wss"
            : "ws";

    socket =
        new WebSocket(
            `${scheme}://${location.host}/ws`
        );

    socket.onopen = () => {

        reconnectDelay = 500;

        setState(
            "listening",
            "yes"
        );

        send.disabled = false;

        talkButton.disabled = false;

        keepalive =
            setInterval(
                () => {

                    if (
                        socket.readyState ===
                        WebSocket.OPEN
                    ) {

                        socket.send(
                            JSON.stringify({
                                type: "ping",
                            })
                        );
                    }

                },
                25000
            );
    };

    socket.onmessage =
        async (event) => {

            if (
                event.data instanceof Blob
            ) {

                const bytes =
                    new Uint8Array(
                        await event.data.arrayBuffer()
                    );

                if (
                    playback.pendingRate
                ) {

                    enqueuePCM(
                        bytes,
                        playback.pendingRate
                    );
                }

                return;
            }

            const msg =
                JSON.parse(
                    event.data
                );

            if (
                msg.type ===
                "hello"
            ) {

                nameEl.textContent =
                    msg.name;

                document.title =
                    msg.name;

                if (!msg.online) {

                    addTurn(
                        "fault",
                        `The language core is not responding. Start Ollama and pull ${msg.model}.`
                    );

                    setState(
                        "no model",
                        "fault"
                    );
                }

                if (
                    !msg.tts_configured
                ) {

                    talkLabel.textContent =
                        "Hold to talk (text replies only)";
                }

                return;
            }

            if (
                msg.type ===
                "state"
            ) {

                setState(
                    msg.value,
                    "yes"
                );

                return;
            }

            if (
                msg.type ===
                "transcript"
            ) {

                addTurn(
                    "operator",
                    msg.text
                );

                return;
            }

            if (
                msg.type ===
                "chunk"
            ) {

                if (!current) {

                    current =
                        addTurn(
                            "core",
                            ""
                        );

                    current.classList.add(
                        "caret"
                    );
                }

                current.textContent +=
                    msg.text;

                thread.scrollTop =
                    thread.scrollHeight;

                return;
            }

            if (
                msg.type ===
                "audio"
            ) {

                playback.pendingRate =
                    msg.sample_rate;

                return;
            }

            if (
                msg.type ===
                "done"
            ) {

                if (current) {
                    current.classList.remove(
                        "caret"
                    );
                }

                current = null;

                return;
            }

            if (
                msg.type ===
                "error"
            ) {

                if (current) {

                    current.classList.remove(
                        "caret"
                    );
                }

                current = null;

                addTurn(
                    "fault",
                    msg.message
                );

                setState(
                    "fault",
                    "fault"
                );
            }
        };

    socket.onclose = () => {

        clearInterval(
            keepalive
        );

        send.disabled = true;

        talkButton.disabled = true;

        setState(
            "reconnecting",
            "fault"
        );

        setTimeout(
            connect,
            reconnectDelay
        );

        reconnectDelay =
            Math.min(
                reconnectDelay * 2,
                8000
            );
    };

    socket.onerror = () =>
        socket.close();
}


// ---- text submit --------------------------------------------------------

form.addEventListener(
    "submit",
    (event) => {

        event.preventDefault();

        const text =
            input.value.trim();

        if (
            !text ||
            !socket ||
            socket.readyState !==
                WebSocket.OPEN
        ) {
            return;
        }

        addTurn(
            "operator",
            text
        );

        socket.send(
            JSON.stringify({
                type: "say",
                text,
            })
        );

        input.value = "";
    }
);


// ---- start --------------------------------------------------------------

connect();