export type QaLanguage = "ar" | "en";

export type DomainQaScenario = {
  id: "quran" | "tafsir" | "hadith" | "fiqh";
  domainLabel: Record<QaLanguage, string>;
  description: Record<QaLanguage, string>;
  question: Record<QaLanguage, string>;
  quranReference?: string;
  expectation: Record<QaLanguage, string>;
};

export const domainQaScenarios: DomainQaScenario[] = [
  {
    id: "quran",
    domainLabel: {
      ar: "القرآن",
      en: "Quran",
    },
    description: {
      ar: "استرجاع النص القرآني الموثق من المصدر المعتمد.",
      en: "Canonical Quran evidence with governed source-native English meaning.",
    },
    question: {
      ar: "ما نص الآية 255 من سورة البقرة؟",
      en: "What does Ayat al-Kursi say?",
    },
    quranReference: "2:255",
    expectation: {
      ar: "المتوقع: النص العربي الموثق والمرجع.",
      en: "Expected: canonical Arabic Quran plus trusted English meaning.",
    },
  },
  {
    id: "tafsir",
    domainLabel: {
      ar: "التفسير",
      en: "Tafsir",
    },
    description: {
      ar: "القرآن مرساة والتفسير دليل مستقل.",
      en: "Quran remains the anchor while Tafsir stays independent evidence.",
    },
    question: {
      ar: "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟",
      en: "Explain the tafsir of verse 2:255",
    },
    quranReference: "2:255",
    expectation: {
      ar: "المتوقع: القرآن مع أدلة التفسير الموثقة.",
      en: "Expected: governed Quran and Tafsir evidence.",
    },
  },
  {
    id: "hadith",
    domainLabel: {
      ar: "الحديث",
      en: "Hadith",
    },
    description: {
      ar: "التحقق من الحديث ودرجته ومصدره.",
      en: "Hadith authenticity and attributed grading.",
    },
    question: {
      ar: "هل حديث إنما الأعمال بالنيات صحيح؟",
      en: "Is the hadith Actions are judged by intentions authentic?",
    },
    expectation: {
      ar: "المتوقع: أدلة الحديث والدرجة والمصدر.",
      en: "English remains fail-closed until trusted public translation wiring is complete.",
    },
  },
  {
    id: "fiqh",
    domainLabel: {
      ar: "الفقه",
      en: "Fiqh",
    },
    description: {
      ar: "عرض الاتجاهات الفقهية الموثقة مع حفظ الخلاف.",
      en: "Governed Fiqh positions with disagreement preserved.",
    },
    question: {
      ar: "ما حكم مس المرأة فرجها وهل ينقض الوضوء؟",
      en: "Does touching the private part invalidate wudu?",
    },
    expectation: {
      ar: "المتوقع: الاتجاهات الموثقة دون اختراع ترجيح.",
      en: "Expected: source-native English Fiqh positions.",
    },
  },
];
