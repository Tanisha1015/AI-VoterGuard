import { num, pct, ratioToBaseline } from "./facts.js";
import { CHECKS, type Text } from "./mock-checks.js";
import type { ExplainContent, ExplainRequest } from "./types.js";

/**
 * Deterministic, neutral, bilingual text built only from the request payload. Used in mock mode
 * (tests, offline demos). No LLM is involved and no number is invented.
 */

const REASON_EN: Record<string, string> = {
  ABSENT: "absent", SHIFTED: "shifted", DEAD: "deceased", DUPLICATE: "duplicate entry",
};
const REASON_HI: Record<string, string> = {
  ABSENT: "अनुपस्थित", SHIFTED: "स्थानांतरित", DEAD: "मृत", DUPLICATE: "दोहरी प्रविष्टि",
};
const GENDER_EN: Record<string, string> = { f: "Female", m: "Male", o: "Other-gender" };
const GENDER_HI: Record<string, string> = { f: "महिला", m: "पुरुष", o: "अन्य लिंग के" };

const CLOSING: Text = {
  en: "This is unusual and worth verifying.",
  hi: "यह असामान्य है और सत्यापन के योग्य है।",
};

function topReason(mix: Record<string, number>): string {
  const entries = Object.entries(mix).sort(([, a], [, b]) => b - a);
  return entries[0]?.[0] ?? "ABSENT";
}

function ratioPhrase(value: number, baseline: number): Text {
  const ratio = ratioToBaseline(value, baseline);
  if (ratio === null || ratio < 1.5) {
    return { en: "", hi: "" };
  }
  return {
    en: `, about ${num(ratio)} times that baseline`,
    hi: `, यानी आधारभूत मान का लगभग ${num(ratio)} गुना`,
  };
}

function deletionRate(p: ExplainRequest): Text {
  const { part_no } = p.booth;
  const { value, baseline } = p.flag.metric;
  const r = ratioPhrase(value, baseline);
  return {
    en: `Booth ${part_no} shows a deletion rate of ${pct(value)}, compared with a constituency baseline of ${pct(baseline)}${r.en}.`,
    hi: `भाग संख्या ${part_no} में नाम हटाने की दर ${pct(value)} है, जबकि निर्वाचन क्षेत्र का आधारभूत औसत ${pct(baseline)} है${r.hi}।`,
  };
}

function reasonDominance(p: ExplainRequest): Text {
  const { part_no, reason_mix } = p.booth;
  const reason = topReason(reason_mix);
  const { value, baseline } = p.flag.metric;
  return {
    en: `In booth ${part_no}, removals recorded as "${REASON_EN[reason] ?? reason}" make up ${pct(value)} of all removals, compared with ${pct(baseline)} across the constituency.`,
    hi: `भाग संख्या ${part_no} में "${REASON_HI[reason] ?? reason}" कारण से दर्ज हटाई गई प्रविष्टियाँ कुल हटाए गए नामों का ${pct(value)} हैं, जबकि पूरे निर्वाचन क्षेत्र में यह ${pct(baseline)} है।`,
  };
}

function genderSkew(p: ExplainRequest): Text {
  const { part_no } = p.booth;
  const { name, value, baseline } = p.flag.metric;
  const key = name.charAt(0).toLowerCase();
  return {
    en: `${GENDER_EN[key] ?? "One gender group"} voters make up ${pct(value)} of removed entries in booth ${part_no}, compared with ${pct(baseline)} of the booth's draft roll.`,
    hi: `भाग संख्या ${part_no} में हटाई गई प्रविष्टियों में ${GENDER_HI[key] ?? "एक लिंग वर्ग के"} मतदाताओं की हिस्सेदारी ${pct(value)} है, जबकि मसौदा सूची में यह ${pct(baseline)} है।`,
  };
}

function ageSkew(p: ExplainRequest): Text {
  const { part_no } = p.booth;
  const { name, value, baseline } = p.flag.metric;
  if (name === "dead_under_40") {
    return {
      en: `Booth ${part_no} has ${num(value)} removals recorded as deceased for voters under 40, compared with a typical booth count of ${num(baseline)}.`,
      hi: `भाग संख्या ${part_no} में 40 वर्ष से कम आयु के ${num(value)} मतदाताओं को मृत दर्शाकर हटाया गया है, जबकि सामान्य भाग में यह संख्या ${num(baseline)} है।`,
    };
  }
  return {
    en: `In booth ${part_no}, voters aged 18-25 make up ${pct(value)} of removed entries, compared with ${pct(baseline)} of the booth's draft roll.`,
    hi: `भाग संख्या ${part_no} में हटाई गई प्रविष्टियों में 18-25 वर्ष आयु वर्ग की हिस्सेदारी ${pct(value)} है, जबकि मसौदा सूची में यह ${pct(baseline)} है।`,
  };
}

function houseCluster(p: ExplainRequest): Text {
  const { part_no } = p.booth;
  const { name, value, baseline } = p.flag.metric;
  if (name === "max_house_additions") {
    return {
      en: `Booth ${part_no} has ${num(value)} new entries at a single house number, compared with a typical booth maximum of ${num(baseline)}.`,
      hi: `भाग संख्या ${part_no} में एक ही मकान संख्या पर ${num(value)} नई प्रविष्टियाँ हैं, जबकि सामान्य भाग में अधिकतम ${num(baseline)} है।`,
    };
  }
  return {
    en: `Booth ${part_no} has up to ${num(value)} voters listed at a single house number, compared with a typical booth maximum of ${num(baseline)}.`,
    hi: `भाग संख्या ${part_no} में एक ही मकान संख्या पर ${num(value)} तक मतदाता दर्ज हैं, जबकि सामान्य भाग में अधिकतम ${num(baseline)} है।`,
  };
}

function duplicateEntry(p: ExplainRequest): Text {
  const { part_no } = p.booth;
  const { value, baseline } = p.flag.metric;
  return {
    en: `Booth ${part_no} has ${num(value)} entries that closely resemble entries in other booths, compared with a typical booth count of ${num(baseline)}.`,
    hi: `भाग संख्या ${part_no} में ${num(value)} प्रविष्टियाँ अन्य भागों की प्रविष्टियों से काफ़ी मिलती-जुलती हैं, जबकि सामान्य भाग में यह संख्या ${num(baseline)} है।`,
  };
}

function dataQuality(p: ExplainRequest): Text {
  const { part_no } = p.booth;
  const { value, baseline } = p.flag.metric;
  return {
    en: `Booth ${part_no} has ${num(value)} data-quality issues, for example missing or inconsistent records, compared with a typical booth count of ${num(baseline)}.`,
    hi: `भाग संख्या ${part_no} में ${num(value)} डेटा गुणवत्ता संबंधी बिंदु हैं, जैसे अभिलेख का न मिलना या असंगत अभिलेख, जबकि सामान्य भाग में यह संख्या ${num(baseline)} है।`,
  };
}

const BUILDERS: Record<ExplainRequest["flag"]["detector"], (p: ExplainRequest) => Text> = {
  DELETION_RATE: deletionRate,
  REASON_DOMINANCE: reasonDominance,
  GENDER_SKEW: genderSkew,
  AGE_SKEW: ageSkew,
  HOUSE_CLUSTER: houseCluster,
  DUPLICATE_ENTRY: duplicateEntry,
  DATA_QUALITY: dataQuality,
};

/** Neutral bilingual explanation and 2 recommended checks for one flag. */
export function mockExplain(payload: ExplainRequest): ExplainContent {
  const detail = BUILDERS[payload.flag.detector](payload);
  return {
    explanation: {
      en: `${detail.en} ${CLOSING.en}`,
      hi: `${detail.hi} ${CLOSING.hi}`,
    },
    recommended_checks: CHECKS[payload.flag.detector].map((c) => ({ ...c })),
  };
}

