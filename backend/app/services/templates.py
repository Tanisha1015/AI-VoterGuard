"""Neutral bilingual (English + Hindi) text built from numbers computed by the detectors.

This is the fallback used whenever the agent service cannot phrase a flag, and the source of the
fixed citizen-facing texts. Every number comes from deterministic code; the wording only says that a
pattern is unusual and worth verifying, and never states or implies wrongdoing or eligibility.
"""

from __future__ import annotations

from typing import Any, Optional

Text = dict[str, str]  # {"en": "...", "hi": "..."}

# If the project later wants to name a specific claim form, set this to {"en": "...", "hi": "..."}
# and it is added as one more step. Left unset on purpose: forms and deadlines change.
CLAIM_FORM_REFERENCE: Optional[Text] = None

REASON_HI: dict[str, str] = {
    "ABSENT": "अनुपस्थित",
    "SHIFTED": "स्थानांतरित",
    "DEAD": "मृत",
    "DUPLICATE": "दोहरी प्रविष्टि",
}

DISCLAIMER_FLAGS: Text = {
    "en": "Flags are prompts for field verification. They do not establish wrongdoing or eligibility.",
    "hi": "ये संकेत क्षेत्रीय सत्यापन के लिए सुझाव मात्र हैं। ये किसी अनियमितता या पात्रता को स्थापित नहीं करते।",
}

DISCLAIMER_CITIZEN: Text = {
    "en": "Confirm current forms and deadlines on the official ECI website.",
    "hi": "वर्तमान प्रपत्र और अंतिम तिथियाँ भारत निर्वाचन आयोग की आधिकारिक वेबसाइट पर जाँच लें।",
}

AMBIGUOUS_MESSAGE: Text = {
    "en": "More than one entry matches these details. To protect privacy we do not list them. "
          "Please search again using your EPIC number.",
    "hi": "इन विवरणों से एक से अधिक प्रविष्टियाँ मिलती हैं। गोपनीयता की रक्षा के लिए हम उन्हें सूचीबद्ध नहीं करते। "
          "कृपया अपने EPIC नंबर से दोबारा खोजें।",
}


# ------------------------------------------------------------------ number formatting


def pct(value: float) -> str:
    """0.224 -> "22.4%"."""
    return f"{value * 100:.1f}%"


def num(value: float) -> str:
    """4.0 -> "4", 4.5 -> "4.5" (counts and medians)."""
    return f"{value:g}"


def top_reason(booth: dict[str, Any]) -> str:
    """The largest-share reason in a booth's reason_mix (ties resolve in contract order)."""
    mix = booth.get("reason_mix") or {}
    return max(REASON_HI, key=lambda r: mix.get(r, 0.0))


# ------------------------------------------------------------------ flag explanations


def _deletion_rate(p: int, v: float, b: float) -> tuple[Text, list[Text]]:
    if b > 0:
        ratio_en = f", about {v / b:.1f} times the constituency median of {pct(b)}"
        ratio_hi = f", जो निर्वाचन क्षेत्र की माध्यिका {pct(b)} से लगभग {v / b:.1f} गुना है"
    else:
        ratio_en = f", compared with a constituency median of {pct(b)}"
        ratio_hi = f", जबकि निर्वाचन क्षेत्र की माध्यिका {pct(b)} है"
    explanation = {
        "en": f"Booth {p} shows a deletion rate of {pct(v)}{ratio_en}. "
              "This is an unusual pattern worth verifying.",
        "hi": f"भाग संख्या {p} में नाम हटाने की दर {pct(v)} है{ratio_hi}। "
              "यह असामान्य पैटर्न है और सत्यापन के योग्य है।",
    }
    checks = [
        {"en": "Re-verify a sample of 20 removed households.",
         "hi": "हटाए गए 20 परिवारों के एक नमूने का दोबारा सत्यापन करें।"},
        {"en": "Compare the removal list with the Booth Level Officer's visit records.",
         "hi": "हटाई गई सूची का मिलान बूथ स्तर अधिकारी के भ्रमण अभिलेखों से करें।"},
        {"en": "Recommend a field check of the entries removed under the most common reason.",
         "hi": "सबसे अधिक दर्ज कारण से हटाई गई प्रविष्टियों की क्षेत्रीय जाँच की सिफारिश की जाती है।"},
    ]
    return explanation, checks


def _reason_dominance(p: int, v: float, b: float, booth: dict[str, Any]) -> tuple[Text, list[Text]]:
    reason = top_reason(booth)
    explanation = {
        "en": f"In booth {p}, {pct(v)} of removals are recorded with the reason {reason}, "
              f"compared with about {pct(b)} across the constituency. "
              "This pattern is unusual and worth verifying.",
        "hi": f"भाग संख्या {p} में {pct(v)} नाम '{REASON_HI[reason]}' कारण से हटाए गए हैं, "
              f"जबकि पूरे निर्वाचन क्षेत्र में यह लगभग {pct(b)} है। "
              "यह पैटर्न असामान्य है और सत्यापन के योग्य है।",
    }
    checks = [
        {"en": f"Recommend visiting a sample of 20 addresses recorded as {reason} to confirm the "
               "current situation.",
         "hi": f"'{REASON_HI[reason]}' दर्ज 20 पतों के एक नमूने पर जाकर वर्तमान स्थिति की पुष्टि करने की "
               "सिफारिश की जाती है।"},
        {"en": "Check that the remarks supporting these removals are complete and consistent.",
         "hi": "जाँचें कि इन प्रविष्टियों को हटाने के समर्थन में दर्ज टिप्पणियाँ पूर्ण और एकरूप हैं।"},
    ]
    return explanation, checks


def _gender_skew(p: int, v: float, b: float, name: str) -> tuple[Text, list[Text]]:
    group_en, group_hi = ("Women", "महिलाओं") if name.startswith("f") else ("Men", "पुरुषों")
    explanation = {
        "en": f"{group_en} account for {pct(v)} of removed entries in booth {p}, against a share of "
              f"{pct(b)} in the booth's draft roll. This may indicate a pattern that is worth a field check.",
        "hi": f"भाग संख्या {p} में हटाई गई प्रविष्टियों में {group_hi} की हिस्सेदारी {pct(v)} है, जबकि "
              f"मसौदा सूची में यह {pct(b)} है। यह ऐसा पैटर्न हो सकता है जिसकी क्षेत्रीय जाँच उचित होगी।",
    }
    checks = [
        {"en": "Re-verify a sample of 20 removed households, noting the gender mix of the entries.",
         "hi": "हटाए गए 20 परिवारों के एक नमूने का दोबारा सत्यापन करें और प्रविष्टियों में लिंग अनुपात दर्ज करें।"},
        {"en": "Compare the removal records with the Booth Level Officer's visit notes.",
         "hi": "हटाए जाने के अभिलेखों का मिलान बूथ स्तर अधिकारी के भ्रमण नोट्स से करें।"},
    ]
    return explanation, checks


def _age_skew(p: int, v: float, b: float, name: str) -> tuple[Text, list[Text]]:
    if name == "dead_under_40":
        explanation = {
            "en": f"Booth {p} has {num(v)} entries removed with the reason DEAD for voters under 40, "
                  f"compared with a typical booth count of {num(b)}. This is unusual and worth verifying.",
            "hi": f"भाग संख्या {p} में 40 वर्ष से कम आयु के {num(v)} नाम 'मृत' कारण से हटाए गए हैं, जबकि "
                  f"सामान्य भाग में यह संख्या {num(b)} है। यह असामान्य है और सत्यापन के योग्य है।",
        }
    else:
        explanation = {
            "en": f"In booth {p}, voters aged 18-25 make up {pct(v)} of removed entries, compared with "
                  f"{pct(b)} of the booth's draft roll. This is unusual and worth verifying.",
            "hi": f"भाग संख्या {p} में हटाई गई प्रविष्टियों में 18-25 वर्ष आयु वर्ग की हिस्सेदारी {pct(v)} है, "
                  f"जबकि मसौदा सूची में यह {pct(b)} है। यह असामान्य है और सत्यापन के योग्य है।",
        }
    checks = [
        {"en": "Re-verify a sample of 20 of these removed entries with the household or local records.",
         "hi": "इन हटाई गई प्रविष्टियों के 20 के नमूने का परिवार या स्थानीय अभिलेखों से दोबारा सत्यापन करें।"},
        {"en": "Recommend a field check to confirm the supporting records for these removals exist.",
         "hi": "इन प्रविष्टियों को हटाने के समर्थन में अभिलेख उपलब्ध हैं, इसकी क्षेत्रीय जाँच की सिफारिश की जाती है।"},
    ]
    return explanation, checks


def _house_cluster(p: int, v: float, b: float, name: str) -> tuple[Text, list[Text]]:
    if name == "max_house_additions":
        explanation = {
            "en": f"Booth {p} has {num(v)} new entries at a single house number, compared with a typical "
                  f"booth maximum of {num(b)}. This is unusual and worth verifying.",
            "hi": f"भाग संख्या {p} में एक ही मकान संख्या पर {num(v)} नई प्रविष्टियाँ हैं, जबकि सामान्य भाग में "
                  f"अधिकतम {num(b)} है। यह असामान्य है और सत्यापन के योग्य है।",
        }
    else:
        explanation = {
            "en": f"Booth {p} has up to {num(v)} voters listed at a single house number, compared with a "
                  f"typical booth maximum of {num(b)}. This is unusual and worth verifying.",
            "hi": f"भाग संख्या {p} में एक ही मकान संख्या पर {num(v)} तक मतदाता दर्ज हैं, जबकि सामान्य भाग में "
                  f"अधिकतम {num(b)} है। यह असामान्य है और सत्यापन के योग्य है।",
        }
    checks = [
        {"en": "Recommend visiting the address to confirm how many households live there.",
         "hi": "उस पते पर जाकर वहाँ कितने परिवार रहते हैं, इसकी पुष्टि करने की सिफारिश की जाती है।"},
        {"en": "Compare the entries at this house number with the Booth Level Officer's household records.",
         "hi": "इस मकान संख्या की प्रविष्टियों का मिलान बूथ स्तर अधिकारी के परिवार अभिलेखों से करें।"},
    ]
    return explanation, checks



def _duplicate_entry(p: int, v: float, b: float) -> tuple[Text, list[Text]]:
    explanation = {
        "en": f"Booth {p} has {num(v)} entries that closely resemble entries in other booths, compared "
              f"with a typical booth count of {num(b)}. This is unusual and worth verifying.",
        "hi": f"भाग संख्या {p} में {num(v)} प्रविष्टियाँ अन्य भागों की प्रविष्टियों से काफ़ी मिलती-जुलती हैं, जबकि "
              f"सामान्य भाग में यह संख्या {num(b)} है। यह असामान्य है और सत्यापन के योग्य है।",
    }
    checks = [
        {"en": "Compare a sample of these entries with the matching entries in the other booths.",
         "hi": "इन प्रविष्टियों के एक नमूने का मिलान अन्य भागों की संबंधित प्रविष्टियों से करें।"},
        {"en": "Recommend a field check to confirm where each person is registered to vote.",
         "hi": "प्रत्येक व्यक्ति कहाँ मतदाता के रूप में दर्ज है, इसकी पुष्टि के लिए क्षेत्रीय जाँच की सिफारिश की जाती है।"},
    ]
    return explanation, checks


def _data_quality(p: int, v: float, b: float) -> tuple[Text, list[Text]]:
    explanation = {
        "en": f"Booth {p} has {num(v)} data-quality issues (for example missing records or unusual ages), "
              f"compared with a typical booth count of {num(b)}. This is worth verifying.",
        "hi": f"भाग संख्या {p} में {num(v)} डेटा गुणवत्ता संबंधी बिंदु हैं (जैसे अभिलेख का न मिलना या असामान्य आयु), "
              f"जबकि सामान्य भाग में यह संख्या {num(b)} है। यह सत्यापन के योग्य है।",
    }
    checks = [
        {"en": "Review the records listed under the data-quality issues for this booth.",
         "hi": "इस भाग के डेटा गुणवत्ता संबंधी बिंदुओं में सूचीबद्ध अभिलेखों की समीक्षा करें।"},
        {"en": "Ask the booth team to re-check the source documents for these entries.",
         "hi": "भाग की टीम से इन प्रविष्टियों के मूल दस्तावेज़ दोबारा जाँचने का अनुरोध करें।"},
    ]
    return explanation, checks


def _generic(p: int, v: float, b: float) -> tuple[Text, list[Text]]:
    explanation = {
        "en": f"Booth {p} shows a value of {num(v)}, compared with a baseline of {num(b)}. "
              "This is unusual and worth verifying.",
        "hi": f"भाग संख्या {p} में मान {num(v)} है, जबकि आधारभूत मान {num(b)} है। "
              "यह असामान्य है और सत्यापन के योग्य है।",
    }
    checks = [
        {"en": "Recommend a field check of a sample of entries in this booth.",
         "hi": "इस भाग की प्रविष्टियों के एक नमूने की क्षेत्रीय जाँच की सिफारिश की जाती है।"},
        {"en": "Compare the entries with the Booth Level Officer's visit records.",
         "hi": "प्रविष्टियों का मिलान बूथ स्तर अधिकारी के भ्रमण अभिलेखों से करें।"},
    ]
    return explanation, checks


def explain_flag(
    detector: str, metric_name: str, value: float, baseline: float, part_no: int, booth: dict[str, Any]
) -> tuple[Text, list[Text]]:
    """Return (explanation, recommended_checks) for one flag, in English and Hindi.

    ``booth`` is the BoothSummary dict of the flag's booth (only reason_mix is used, to name the
    dominant reason). The text states the metric values and 2-3 checks, and nothing more.
    """
    if detector == "DELETION_RATE":
        return _deletion_rate(part_no, value, baseline)
    if detector == "REASON_DOMINANCE":
        return _reason_dominance(part_no, value, baseline, booth)
    if detector == "GENDER_SKEW":
        return _gender_skew(part_no, value, baseline, metric_name)
    if detector == "AGE_SKEW":
        return _age_skew(part_no, value, baseline, metric_name)
    if detector == "HOUSE_CLUSTER":
        return _house_cluster(part_no, value, baseline, metric_name)
    if detector == "DUPLICATE_ENTRY":
        return _duplicate_entry(part_no, value, baseline)
    if detector == "DATA_QUALITY":
        return _data_quality(part_no, value, baseline)
    return _generic(part_no, value, baseline)


# ------------------------------------------------------------------ citizen texts


def next_step(deadline: Optional[str]) -> dict[str, Any]:
    """The 'what you can do next' block shown for a REMOVED result (bilingual)."""
    steps: list[Text] = [
        {"en": "Contact your Booth Level Officer or visit the official ECI portal",
         "hi": "अपने बूथ स्तर अधिकारी से संपर्क करें या भारत निर्वाचन आयोग के आधिकारिक पोर्टल पर जाएँ"},
        {"en": "Keep a proof of your current address ready",
         "hi": "अपने वर्तमान पते का प्रमाण तैयार रखें"},
    ]
    if CLAIM_FORM_REFERENCE is not None:
        steps.append(dict(CLAIM_FORM_REFERENCE))
    return {
        "title": {
            "en": "If this is incorrect, you can ask for your name to be restored",
            "hi": "यदि यह जानकारी सही नहीं है, तो आप अपना नाम पुनः जुड़वाने का अनुरोध कर सकते हैं",
        },
        "steps": steps,
        "deadline": deadline,
        "disclaimer": dict(DISCLAIMER_CITIZEN),
    }

