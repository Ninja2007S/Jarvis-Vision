// Runs on the audio rendering thread, not the main thread — capture stays
// glitch-free even while the UI is busy streaming a reply back in.
class MicCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.inRate = sampleRate; // the AudioContext's native rate, e.g. 48000
    this.outRate = 16000; // what Whisper wants
    this.ratio = this.inRate / this.outRate;
    this.carry = 0; // fractional position left over between blocks
  }

  process(inputs) {
    const input = inputs[0][0];
    if (!input || input.length === 0) return true;

    const samples = [];
    let position = this.carry;
    while (position < input.length) {
      const index = Math.floor(position);
      samples.push(input[index] ?? 0);
      position += this.ratio;
    }
    this.carry = position - input.length;

    const pcm16 = new Int16Array(samples.length);
    for (let i = 0; i < samples.length; i++) {
      const clamped = Math.max(-1, Math.min(1, samples[i]));
      pcm16[i] = clamped < 0 ? clamped * 32768 : clamped * 32767;
    }

    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor("mic-capture", MicCapture);
