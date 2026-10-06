const baseUrl = (process.env.BASIRA_API_URL || process.env.VITE_BASIRA_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const scenarios = [
  {
    id: "quran",
    label: "QURAN",
    payload: {
      question: "ما نص الآية 255 من سورة البقرة؟",
      quran_reference: "2:255",
    },
    expectedDomains: ["quran"],
  },
  {
    id: "tafsir",
    label: "TAFSIR",
    payload: {
      question: "ما معنى الآية 2:255؟",
      quran_reference: "2:255",
    },
    expectedDomains: ["quran", "tafsir"],
  },
  {
    id: "hadith",
    label: "HADITH",
    payload: {
      question: "ما صحة حديث رقم 65065؟",
    },
    expectedDomains: ["hadith"],
  },
];

let failed = false;

for (const scenario of scenarios) {
  console.log("\n" + "=".repeat(72));
  console.log(`${scenario.label} — ${scenario.payload.question}`);
  console.log("=".repeat(72));

  try {
    const response = await fetch(`${baseUrl}/api/v1/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(scenario.payload),
    });

    const raw = await response.text();
    if (!response.ok) {
      failed = true;
      console.error(`HTTP ${response.status}`);
      console.error(raw.slice(0, 1200));
      continue;
    }

    const result = JSON.parse(raw);
    const evidence = Array.isArray(result.evidence) ? result.evidence : [];
    const domains = [...new Set(evidence.map((item) => item.domain).filter(Boolean))];
    const missing = scenario.expectedDomains.filter((domain) => !domains.includes(domain));

    console.log("action        =", result.action);
    console.log("has_answer    =", result.has_answer);
    console.log("trust state   =", result.experience?.state ?? "<none>");
    console.log("can_publish   =", result.experience?.can_publish ?? "<none>");
    console.log("evidence      =", evidence.length);
    console.log("domains       =", domains.join(", ") || "<none>");
    console.log("limitations   =", Array.isArray(result.limitations) ? result.limitations.length : 0);
    console.log(
      "references    =",
      evidence.map((item) => item.reference).filter(Boolean).slice(0, 8).join(" | ") || "<none>",
    );

    if (missing.length > 0) {
      failed = true;
      console.error("DOMAIN CHECK  = FAIL — missing:", missing.join(", "));
    } else {
      console.log("DOMAIN CHECK  = PASS");
    }
  } catch (error) {
    failed = true;
    console.error("REQUEST ERROR =", error instanceof Error ? error.message : String(error));
  }
}

console.log("\n" + "=".repeat(72));
console.log(failed ? "❌ THREE-DOMAIN SMOKE FAILED" : "✅ THREE-DOMAIN SMOKE PASSED");
console.log("=".repeat(72));
process.exitCode = failed ? 1 : 0;
