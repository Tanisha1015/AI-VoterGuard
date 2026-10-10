import type { ExplainRequest } from "./types.js";

/** Static, neutral, bilingual field-verification steps per detector (no numbers). */

export type Text = { en: string; hi: string };

export const CHECKS: Record<ExplainRequest["flag"]["detector"], Text[]> = {
  DELETION_RATE: [
    { en: "Recommend a field check of a sample of removed entries in this booth.", hi: "इस भाग में हटाई गई प्रविष्टियों के एक नमूने की क्षेत्रीय जाँच की सिफारिश की जाती है।" },
    { en: "Compare the removal list with the Booth Level Officer's visit records.", hi: "हटाई गई सूची का मिलान बूथ स्तर अधिकारी के भ्रमण अभिलेखों से करें।" },
  ],
  REASON_DOMINANCE: [
    { en: "Review a sample of the removal entries and the supporting-document references recorded for them.", hi: "हटाई गई प्रविष्टियों के एक नमूने और उनके लिए दर्ज समर्थक दस्तावेज़ संदर्भों की समीक्षा करें।" },
    { en: "Compare the recorded reasons with the Booth Level Officer's visit records.", hi: "दर्ज कारणों का मिलान बूथ स्तर अधिकारी के भ्रमण अभिलेखों से करें।" },
  ],
  GENDER_SKEW: [
    { en: "Recommend a household re-verification of a sample of the removed entries.", hi: "हटाई गई प्रविष्टियों के एक नमूने का परिवार स्तर पर पुनः सत्यापन करने की सिफारिश की जाती है।" },
    { en: "Compare the removals with the Booth Level Officer's visit records.", hi: "हटाई गई प्रविष्टियों का मिलान बूथ स्तर अधिकारी के भ्रमण अभिलेखों से करें।" },
  ],
  AGE_SKEW: [
    { en: "Re-verify a sample of these removed entries with the household or local records.", hi: "इन हटाई गई प्रविष्टियों के एक नमूने का परिवार या स्थानीय अभिलेखों से दोबारा सत्यापन करें।" },
    { en: "Recommend a field check to confirm the supporting records for these removals exist.", hi: "इन प्रविष्टियों को हटाने के समर्थन में अभिलेख उपलब्ध हैं, इसकी क्षेत्रीय जाँच की सिफारिश की जाती है।" },
  ],
  HOUSE_CLUSTER: [
    { en: "Recommend visiting the address to confirm how many households live there.", hi: "उस पते पर जाकर वहाँ कितने परिवार रहते हैं, इसकी पुष्टि करने की सिफारिश की जाती है।" },
    { en: "Compare the entries at this house number with the Booth Level Officer's household records.", hi: "इस मकान संख्या की प्रविष्टियों का मिलान बूथ स्तर अधिकारी के परिवार अभिलेखों से करें।" },
  ],
  DUPLICATE_ENTRY: [
    { en: "Compare a sample of these entries with the matching entries in the other booths.", hi: "इन प्रविष्टियों के एक नमूने का मिलान अन्य भागों की संबंधित प्रविष्टियों से करें।" },
    { en: "Recommend a field check to confirm where each person is registered to vote.", hi: "प्रत्येक व्यक्ति कहाँ मतदाता के रूप में दर्ज है, इसकी पुष्टि के लिए क्षेत्रीय जाँच की सिफारिश की जाती है।" },
  ],
  DATA_QUALITY: [
    { en: "Review the records listed under the data-quality issues for this booth.", hi: "इस भाग के डेटा गुणवत्ता संबंधी बिंदुओं के अंतर्गत सूचीबद्ध अभिलेखों की समीक्षा करें।" },
    { en: "Cross-check these records against the supporting-document references.", hi: "इन अभिलेखों का मिलान समर्थक दस्तावेज़ संदर्भों से करें।" },
  ],
};
