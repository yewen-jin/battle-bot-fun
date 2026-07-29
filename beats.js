// Stream A - beat generation: fight history -> one OpenAI API call -> validated beat array.
// Depends on data/data.js (window.OOF_DATA, window.OOF_SYSTEM_PROMPT) loaded first.
// Fallback chain: generate -> retry once -> sample_beats.json (window.OOF_SAMPLE_BEATS).

const Beats = (() => {
  const DATA = window.OOF_DATA;

  // --- history summariser -------------------------------------------------

  function botSummary(name) {
    const bot = DATA.bots.find((b) => b.name === name);
    if (!bot) throw new Error(`Unknown bot: ${name}`);
    const fights = DATA.fights.filter(
      (f) => f.bot_a === name || f.bot_b === name
    );
    const lines = [
      `${bot.name} - ${bot.weapon_type || "unknown weapon"} - team ${bot.team || "unknown"}`,
      `Record: ${bot.record.wins}W-${bot.record.losses}L. Win methods: ${
        JSON.stringify(bot.win_methods)
      }`,
    ];
    if (!fights.length) {
      lines.push("ROOKIE: no prior recorded fights. Do not invent history.");
    } else {
      // Most recent ~12 fights with known outcomes carry the factual weight
      const known = fights.filter((f) => f.winner).slice(-12);
      for (const f of known) {
        const opp = f.bot_a === name ? f.bot_b : f.bot_a;
        const res = f.winner === name ? "beat" : "lost to";
        lines.push(
          `${f.event || "?"}: ${res} ${opp}${f.method ? ` (${f.method})` : ""}`
        );
      }
    }
    const flavor = (DATA.fan_flavor || {})[name] || [];
    if (flavor.length) {
      lines.push(`Fan chatter (tone only, never quote): ${flavor.join(" | ")}`);
    }
    return lines.join("\n");
  }

  // --- validator (PRD merge protocol step 1) ------------------------------

  function validate(doc) {
    const errs = [];
    const names = DATA.bots.map((b) => b.name);
    if (!doc || typeof doc !== "object") return ["not an object"];
    const { fight, beats } = doc;
    if (!fight || !names.includes(fight.a)) errs.push("fight.a invalid");
    if (!fight || !names.includes(fight.b)) errs.push("fight.b invalid");
    if (!fight || !["a", "b"].includes(fight.winner)) errs.push("fight.winner invalid");
    if (!Array.isArray(beats) || beats.length < 18 || beats.length > 30)
      errs.push(`beat count ${beats?.length} outside 18-30`);
    let prev = -Infinity;
    (beats || []).forEach((b, i) => {
      if (typeof b.t !== "number" || b.t <= prev) errs.push(`beat ${i}: t not ascending`);
      if (i === 0 && b.t < 0.5) errs.push("first beat t < 0.5");
      if (prev !== -Infinity && b.t - prev < 0.8) errs.push(`beat ${i}: gap < 0.8s`);
      prev = b.t;
      if (!["a", "b", "both"].includes(b.target)) errs.push(`beat ${i}: bad target`);
      const mag = Math.hypot(b.impulse?.x ?? NaN, b.impulse?.y ?? NaN);
      if (!(mag >= 40 && mag <= 220)) errs.push(`beat ${i}: |impulse| ${mag.toFixed(0)} out of range`);
      if (typeof b.line !== "string" || b.line.length >= 90) errs.push(`beat ${i}: bad line`);
      if (typeof b.shake !== "number" || b.shake < 0 || b.shake > 1) errs.push(`beat ${i}: bad shake`);
    });
    const last = (beats || [])[beats?.length - 1];
    if (last && last.shake !== 1.0) errs.push("final beat shake != 1.0");
    if (last && fight && last.target !== (fight.winner === "a" ? "b" : "a"))
      errs.push("final beat target is not the loser");
    if (prev > 140 + 0.001) errs.push(`duration ${prev.toFixed(1)}s > 140s`);
    return errs;
  }

  // --- API call -----------------------------------------------------------

  function getApiKey() {
    let key = localStorage.getItem("oof_openai_api_key");
    if (!key) {
      key = prompt("OpenAI API key (stored in localStorage):");
      if (key) localStorage.setItem("oof_openai_api_key", key.trim());
    }
    return key;
  }

  async function callModel(botA, botB) {
    const userMsg = [
      `Fight card: ${botA} vs ${botB}.`,
      "",
      `=== ${botA} ===`,
      botSummary(botA),
      "",
      `=== ${botB} ===`,
      botSummary(botB),
    ].join("\n");

    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "authorization": `Bearer ${getApiKey()}`,
      },
      body: JSON.stringify({
        model: "gpt-5.5",
        messages: [
          { role: "system", content: window.OOF_SYSTEM_PROMPT },
          { role: "user", content: userMsg },
        ],
      }),
    });
    if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    const choice = data.choices && data.choices[0];
    if (!choice) throw new Error("no choices in response");
    if (choice.finish_reason === "content_filter") throw new Error("model refused (content filter)");
    let text = (choice.message && choice.message.content) || "";
    // Strip fences defensively even though the prompt forbids them
    text = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/, "");
    return JSON.parse(text);
  }

  // --- public: generate with retry + fallback -----------------------------

  async function generate(botA, botB) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const doc = await callModel(botA, botB);
        const errs = validate(doc);
        if (!errs.length) return { doc, source: "live" };
        console.warn(`beats attempt ${attempt} invalid:`, errs);
      } catch (e) {
        console.warn(`beats attempt ${attempt} failed:`, e);
      }
    }
    console.warn("falling back to sample_beats");
    return { doc: window.OOF_SAMPLE_BEATS, source: "fallback" };
  }

  return { generate, validate, botSummary };
})();

window.Beats = Beats;
