// Presentation metadata per response_type — drives the label pill + accent
// color + accessible description for each kind of assistant reply.
export const RESPONSE_META = {
  FACTUAL: {
    label: "Factual",
    tone: "factual",
    aria: "Factual answer from official sources",
  },
  ADVISORY_REFUSAL: {
    label: "Facts only",
    tone: "refusal",
    aria: "Advisory request declined — facts only, no investment advice",
  },
  OUT_OF_SCOPE: {
    label: "Out of scope",
    tone: "scope",
    aria: "Out of scope — outside the covered schemes",
  },
  NO_SOURCE: {
    label: "No source",
    tone: "nosource",
    aria: "No supporting source found",
  },
  PII_REJECTED: {
    label: "Privacy",
    tone: "pii",
    aria: "Rejected to protect personal information",
  },
  ERROR: {
    label: "Service issue",
    tone: "error",
    aria: "Temporary service issue",
  },
};

export const DISCLAIMER = "Facts-only. No investment advice.";

export const FALLBACK_EXAMPLES = [
  "What is the expense ratio of HDFC Mid Cap Fund?",
  "What is the lock-in period of HDFC ELSS Tax Saver?",
  "What is a mutual fund?",
];
