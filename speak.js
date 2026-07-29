// Stream A - TTS wrapper, now backed by Cartesia's cloud TTS API instead of
// window.speechSynthesis. Voice: "Clive - Measured Expert" (composed,
// articulate) - matches the PRD's "straight, serious broadcast voice" brief.
//
// Measured round-trip latency ~0.7s for a typical commentary line (network
// TTS is not instant like the old browser speechSynthesis path) - see
// physics.js's CONFIG.speakLeadSeconds, bumped up accordingly so audio
// doesn't land after the impulse it's describing.

const CARTESIA_VOICE_ID = "b24f41fd-00a3-4cd8-992a-a0c9f13f3ef1"; // Clive - Measured Expert
const CARTESIA_MODEL = "sonic-3.5";

const Speak = (() => {
  let currentAudio = null;

  function getApiKey() {
    let key = localStorage.getItem("oof_cartesia_api_key");
    if (!key) {
      key = prompt("Cartesia API key (stored in localStorage):");
      if (key) localStorage.setItem("oof_cartesia_api_key", key.trim());
    }
    return key;
  }

  async function speak(line) {
    const apiKey = getApiKey();
    if (!apiKey) return;

    // A new beat interrupts a still-talking old one (same semantics as the
    // old speechSynthesis.cancel() call).
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    try {
      const resp = await fetch("https://api.cartesia.ai/tts/bytes", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "Authorization": `Bearer ${apiKey}`,
          "Cartesia-Version": "2026-03-01",
        },
        body: JSON.stringify({
          model_id: CARTESIA_MODEL,
          transcript: line,
          voice: { mode: "id", id: CARTESIA_VOICE_ID },
          output_format: { container: "wav", encoding: "pcm_s16le", sample_rate: 44100 },
          language: "en",
        }),
      });
      if (!resp.ok) throw new Error(`Cartesia TTS ${resp.status}: ${await resp.text()}`);

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.addEventListener("ended", () => URL.revokeObjectURL(url));
      currentAudio = audio;
      await audio.play();
    } catch (e) {
      console.warn("Cartesia TTS failed:", e);
    }
  }

  return { speak };
})();

window.Speak = Speak;
