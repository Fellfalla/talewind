// TTS Worker — runs Kokoro ONNX inference off the main thread.
// Each worker holds its own model instance (~80-150MB depending on preset).
// Messages: init → ready | error, generate → chunk | error

let tts = null;

function buildWavBlob(audioData, sampleRate) {
  const numSamples = audioData.length;
  const bitsPerSample = 16;
  const byteRate = sampleRate * (bitsPerSample / 8);
  const dataSize = numSamples * (bitsPerSample / 8);
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  const writeStr = (offset, str) => { for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i)); };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, bitsPerSample / 8, true);
  view.setUint16(34, bitsPerSample, true);
  writeStr(36, "data");
  view.setUint32(40, dataSize, true);
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, audioData[i]));
    view.setInt16(44 + i * 2, Math.round(s * 32767), true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

self.onmessage = async (e) => {
  const { type, reqId, ...data } = e.data;

  if (type === "init") {
    try {
      const { KokoroTTS } = await import("https://cdn.jsdelivr.net/npm/kokoro-js@1.2.1/+esm");
      tts = await KokoroTTS.from_pretrained(data.modelId, {
        dtype: data.dtype,
        device: data.device,
      });
      self.postMessage({ type: "ready" });
    } catch (err) {
      self.postMessage({ type: "error", error: err.message });
    }
    return;
  }

  if (type === "generate") {
    try {
      if (!tts) throw new Error("Model not loaded");
      const result = await tts.generate(data.text, {
        voice: data.voice,
        speed: data.speed,
      });
      const blob = buildWavBlob(result.audio, result.sampling_rate);
      self.postMessage({ type: "chunk", reqId, blob });
    } catch (err) {
      self.postMessage({ type: "error", reqId, error: err.message });
    }
    return;
  }
};
