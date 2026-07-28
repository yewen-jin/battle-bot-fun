// Stream A - TTS wrapper around window.speechSynthesis.
// Gotcha handled: getVoices() returns [] on first call; wait for `voiceschanged`.

const Speak = (() => {
  let voice = null;
  let ready = false;

  function pickVoice() {
    const voices = window.speechSynthesis.getVoices();
    if (!voices.length) return;
    // Prefer a deep-ish English voice for broadcast feel; fall back to any English, then first.
    voice =
      voices.find((v) => /en[-_]US/i.test(v.lang) && /male|daniel|alex|fred/i.test(v.name)) ||
      voices.find((v) => /^en/i.test(v.lang)) ||
      voices[0];
    ready = true;
  }

  pickVoice();
  window.speechSynthesis.addEventListener("voiceschanged", pickVoice);

  // Fire ~150ms before the impulse (PRD merge protocol step 3): ears forgive early, not late.
  function speak(line) {
    if (!("speechSynthesis" in window)) return;
    const u = new SpeechSynthesisUtterance(line);
    if (ready && voice) u.voice = voice;
    u.rate = 1.15; // sports-commentary urgency
    u.pitch = 1.0;
    window.speechSynthesis.cancel(); // a new beat interrupts a still-talking old one
    window.speechSynthesis.speak(u);
  }

  return { speak };
})();

window.Speak = Speak;
