/**
 * Rejection data for the neutrality guard. These are the words the generated text must never
 * contain; this service never produces them itself.
 */

/** English terms, matched case-insensitively as whole words. Spaces match any whitespace. */
export const BLOCKED_ENGLISH: readonly string[] = [
  "fraud", "frauds", "fraudulent", "fraudulently", "illegal", "illegally", "illegality",
  "rigging", "rigged", "fake", "fakes", "faked", "bogus", "ineligible", "ineligibility",
  "foreigner", "foreigners", "infiltrator", "infiltrators", "infiltration", "scam", "scams",
  "conspiracy", "conspiracies", "wrongdoing", "wrongful", "wrongfully", "wrongly deleted",
  "wrongly removed", "unlawful", "criminal", "forged", "forgery", "cheating", "tampered",
  "tampering", "manipulated", "manipulation", "suspicious", "deliberate", "deliberately",
  "intentional", "intentionally", "illegitimate",
  // Never speculate about causes involving a group.
  "muslim", "muslims", "hindu", "hindus", "christian", "christians", "sikh", "sikhs",
  "caste", "religion", "religious", "communal", "community", "communities", "nationality",
  "citizenship", "immigrant", "immigrants",
];

/**
 * Hindi stems, matched as substrings (nukta marks removed first) because Hindi words take
 * suffixes such as plural and oblique forms.
 */
export const BLOCKED_HINDI: readonly string[] = [
  "धोखाधड़ी", "धोखाधडी", "फर्जी", "फ़र्ज़ी", "जाली", "अवैध", "गैरकानूनी", "घुसपैठिया",
  "घुसपैठिए", "घुसपैठ", "घोटाला", "घोटाले", "साजिश", "षड्यंत्र", "विदेशी", "अपात्र",
  "धांधली", "हेराफेरी", "आपराधिक", "अपराध", "जानबूझकर", "संदिग्ध",
  "मुस्लिम", "हिंदू", "हिन्दू", "ईसाई", "जाति", "धर्म", "समुदाय", "नागरिकता",
  "राष्ट्रीयता", "अप्रवासी",
];
