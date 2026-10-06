import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  AlertTriangle,
  BookOpen,
  Bookmark,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  ExternalLink,
  FileSearch,
  FileText,
  Globe2,
  History,
  Layers3,
  Library,
  Link2,
  Menu,
  Moon,
  RefreshCcw,
  Scale,
  Search,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Sun,
  ThumbsDown,
  ThumbsUp,
  UserRound,
  X,
} from "lucide-react";

import { BasiraLogo } from "./components/BasiraLogo";
import {
  getEvidenceDetail,
  queryBasira,
  type EvidenceDetail,
  type QueryEvidence,
  type QueryExperience,
  type QueryExperienceTraceStep,
  type QueryResponse,
} from "./api/basira";
import "./index.css";

type Language = "ar" | "en";
type Theme = "light" | "dark";

type Preset = {
  ar: string;
  en: string;
  quranReference?: string;
};

type ExperienceState = QueryExperience["state"];

type HadithSignal = {
  kind: "weak" | "conflict" | "graded";
  label: string;
  detail: string;
  grades: QueryEvidence[];
};

const copy = {
  ar: {
    about: "عن بصيرة",
    sources: "المصادر",
    method: "كيف تعمل بصيرة",
    faq: "الأسئلة الشائعة",
    start: "ابدأ الآن",
    kicker: "تحقق مبني على الأدلة",
    heroLine1: "لا تكتفِ بالإجابة،",
    heroLine2: "اعرف لماذا يمكن الوثوق بها.",
    heroSubtitle:
      "بصيرة تربط سؤالك بالأدلة الموثقة من المصادر المعتمدة، وتوضح لك ما الذي دعم النتيجة وما الذي منعها من النشر.",
    placeholder: "اكتب سؤالك هنا...",
    verify: "تحقق",
    verifying: "جارٍ التحقق",
    examples: "جرّب أمثلة مما تستطيع بصيرة التحقق منه",
    newConversation: "محادثة جديدة",
    today: "اليوم",
    answer: "الإجابة",
    evidence: "الأدلة والمصادر",
    evidenceIntro:
      "كل بطاقة هنا دليل مستقل. لا تدمج بصيرة الأقوال المختلفة ولا ترفع مصدرًا إلى مرتبة أعلى من حالته الفعلية.",
    trust: "حالة الثقة",
    reasoning: "كيف وصلت بصيرة لهذه النتيجة؟",
    technical: "التفاصيل التقنية",
    showTrace: "عرض مسار التحقق",
    hideTrace: "إخفاء مسار التحقق",
    evidenceCount: "الأدلة",
    sourceCount: "المصادر",
    resolution: "اكتمال الحسم",
    publication: "قرار النشر",
    publishAllowed: "مسموح",
    publishBlocked: "متوقف",
    semantic: "التحقق الدلالي",
    semanticPass: "اجتاز",
    semanticNotEnabled: "غير مفعّل",
    limitations: "حدود هذه الإجابة",
    conflictTitle: "يوجد خلاف أو تعارض في الأدلة",
    conflictDetail:
      "تم الحفاظ على الآراء أو الدرجات المختلفة كما وردت في مصادرها، دون اختيار نتيجة واحدة تلقائيًا.",
    hadithWeak: "حديث ضعيف",
    hadithWeakDetail:
      "هذه هي الدرجة المنقولة من المصدر. لا تتعامل بصيرة مع الحديث الضعيف كدليل حاسم بمفرده.",
    hadithConflict: "اختلفت المصادر في درجة الحديث",
    hadithConflictDetail:
      "تعرض بصيرة كل درجة مع مصدرها وتحافظ على الخلاف بدل دمجه في حكم واحد.",
    hadithGrade: "درجة الحديث",
    sourceOriginal: "المصدر الأصلي",
    sourceText: "عرض النص الكامل",
    linkedToAnswer: "مستخدم في الإجابة",
    supportingOnly: "دليل مسترجع",
    claimsLinked: "ادعاءات مرتبطة",
    noPublishableAnswer: "لم تُنشر إجابة",
    sourceUnavailable: "تعذر الوصول إلى بعض المصادر المطلوبة",
    expertReview: "مراجعة خبير مطلوبة",
    caseNumber: "رقم الحالة",
    share: "مشاركة",
    save: "حفظ",
    helpful: "هل كانت هذه النتيجة مفيدة؟",
    loadingSource: "جارٍ تحميل النص الأصلي...",
    sourceLoadError: "تعذر تحميل النص الكامل من المصدر.",
    close: "إغلاق",
    traceComplete: "مكتمل",
    traceWarning: "تنبيه",
    traceBlocked: "متوقف",
    footer: "بصيرة · من الدليل إلى المعرفة الموثوقة",
  },
  en: {
    about: "About Basira",
    sources: "Sources",
    method: "How Basira works",
    faq: "FAQ",
    start: "Start now",
    kicker: "Evidence-first verification",
    heroLine1: "Don’t stop at the answer.",
    heroLine2: "Know why it can be trusted.",
    heroSubtitle:
      "Basira connects each question to governed evidence and makes the reasons for publishing, limiting, or withholding an answer visible.",
    placeholder: "Ask about a verse, hadith, interpretation, or ruling...",
    verify: "Verify",
    verifying: "Verifying",
    examples: "Try examples Basira can verify",
    newConversation: "New conversation",
    today: "Today",
    answer: "Answer",
    evidence: "Evidence & sources",
    evidenceIntro:
      "Each card is an independent evidence item. Basira does not silently merge disagreement or upgrade a source beyond its actual status.",
    trust: "Trust state",
    reasoning: "How did Basira reach this result?",
    technical: "Technical details",
    showTrace: "Show verification trace",
    hideTrace: "Hide verification trace",
    evidenceCount: "Evidence",
    sourceCount: "Sources",
    resolution: "Resolution",
    publication: "Publication",
    publishAllowed: "Allowed",
    publishBlocked: "Stopped",
    semantic: "Semantic verification",
    semanticPass: "Passed",
    semanticNotEnabled: "Not enabled",
    limitations: "Answer limitations",
    conflictTitle: "The evidence contains disagreement",
    conflictDetail:
      "Different views or grades are preserved as attributed. Basira does not silently select a single outcome.",
    hadithWeak: "Weak hadith",
    hadithWeakDetail:
      "This grade is attributed to the source. Basira does not treat weak hadith evidence as independently decisive.",
    hadithConflict: "Hadith grading differs across sources",
    hadithConflictDetail:
      "Basira shows every attributed grade and preserves the disagreement instead of collapsing it.",
    hadithGrade: "Hadith grade",
    sourceOriginal: "Original source",
    sourceText: "View full text",
    linkedToAnswer: "Used in answer",
    supportingOnly: "Retrieved evidence",
    claimsLinked: "Linked claims",
    noPublishableAnswer: "No answer was published",
    sourceUnavailable: "Some required sources were unavailable",
    expertReview: "Expert review required",
    caseNumber: "Case ID",
    share: "Share",
    save: "Save",
    helpful: "Was this result helpful?",
    loadingSource: "Loading the original text...",
    sourceLoadError: "The full source text could not be loaded.",
    close: "Close",
    traceComplete: "Complete",
    traceWarning: "Warning",
    traceBlocked: "Stopped",
    footer: "Basira · From evidence to trustworthy knowledge",
  },
} as const;

const presets: Preset[] = [
  {
    ar: "هل هذا النص القرآني صحيح: يا أيها الذين آمنوا استعينوا بالصبر والصلاة إن الله يحب الصابرين؟",
    en: "Is this Quran quotation correct: “Seek help through patience and prayer; indeed Allah loves the patient”?",
  },
  {
    ar: "ما معنى الكرسي في قوله تعالى: وسع كرسيه السماوات والأرض؟",
    en: "What does al-Kursi mean in: “His Kursi extends over the heavens and the earth”?",
    quranReference: "2:255",
  },
  {
    ar: "هل حديث إنما الأعمال بالنيات صحيح؟",
    en: "Is the hadith “Actions are judged by intentions” authentic?",
  },
  {
    ar: "هل حديث إنما الأعمال بالنيات صحيح؟ وإذا ثبت، فماذا يدل على أهمية النية؟",
    en: "Is the hadith “Actions are judged by intentions” authentic, and if established, what does it indicate about the importance of intention?",
  },
  {
    ar: "ما حكم مس المرأة فرجها وهل ينقض الوضوء؟",
    en: "Does a woman touching her private part invalidate wudu, and what are the madhhab positions?",
  },
  {
    ar: "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟ وهل حديث إنما الأعمال بالنيات صحيح؟",
    en: "What does al-Kursi mean in Quran 2:255, and is the hadith “Actions are judged by intentions” authentic?",
    quranReference: "2:255",
  },
];



const faqScenarios = [
  {
    category: {
      ar: "تصحيح القرآن",
      en: "Quran verification",
    },
    question: {
      ar: "هل هذا النص القرآني صحيح: يا أيها الذين آمنوا استعينوا بالصبر والصلاة إن الله يحب الصابرين؟",
      en: "Is this Quran quotation correct: “Seek help through patience and prayer; indeed Allah loves the patient”?",
    },
  },
  {
    category: {
      ar: "تحقق القرآن",
      en: "Quran verification",
    },
    question: {
      ar: "يا أيها الذين آمنوا استعينوا بالصبر والصلاة إن الله مع الصابرين",
      en: "Verify the Quran quotation ending with: “Indeed Allah is with the patient.”",
    },
  },
  {
    category: {
      ar: "نص القرآن",
      en: "Quran",
    },
    question: {
      ar: "هات نص الآية 2:255",
      en: "Show the exact text of Quran 2:255.",
    },
    quranReference: "2:255",
  },
  {
    category: {
      ar: "القرآن والتفسير",
      en: "Quran & Tafsir",
    },
    question: {
      ar: "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟",
      en: "What does al-Kursi mean in Quran 2:255?",
    },
    quranReference: "2:255",
  },
  {
    category: {
      ar: "القرآن",
      en: "Quran",
    },
    question: {
      ar: "هل أمر القرآن بالمحافظة على الصلاة؟",
      en: "Does the Quran command believers to maintain the prayers?",
    },
  },
  {
    category: {
      ar: "الحديث",
      en: "Hadith",
    },
    question: {
      ar: "هل حديث إنما الأعمال بالنيات صحيح؟",
      en: "Is the hadith “Actions are judged by intentions” authentic?",
    },
  },
  {
    category: {
      ar: "الحديث والاستدلال",
      en: "Hadith reasoning",
    },
    question: {
      ar: "هل حديث إنما الأعمال بالنيات صحيح؟ وإذا ثبت، فماذا يدل على أهمية النية؟",
      en: "Is the hadith “Actions are judged by intentions” authentic, and if established, what does it indicate about intention?",
    },
  },
  {
    category: {
      ar: "اختبار حديث غير ثابت",
      en: "Unattested Hadith safety",
    },
    question: {
      ar: "هل حديث من قال يا بصيرة سبع مرات بعد الفجر دخل الجنة بلا حساب صحيح؟ وإذا ثبت، فماذا يدل على فضل هذا الذكر؟",
      en: "Is the alleged hadith about saying “Ya Basira” seven times after Fajr authentic, and if so what does it imply?",
    },
  },
  {
    category: {
      ar: "القرآن والسنة",
      en: "Quran & Sunnah",
    },
    question: {
      ar: "ما فضل الصلاة في السنة؟ وهل أمر القرآن بالمحافظة على الصلاة؟",
      en: "What is the virtue of prayer in the Sunnah, and does the Quran command maintaining the prayers?",
    },
  },
  {
    category: {
      ar: "متعدد المجالات",
      en: "Multi-domain",
    },
    question: {
      ar: "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟ وهل حديث إنما الأعمال بالنيات صحيح؟",
      en: "What does al-Kursi mean in Quran 2:255, and is the hadith “Actions are judged by intentions” authentic?",
    },
    quranReference: "2:255",
  },
  {
    category: {
      ar: "الفقه والخلاف",
      en: "Fiqh disagreement",
    },
    question: {
      ar: "ما حكم مس المرأة فرجها وهل ينقض الوضوء؟",
      en: "Does a woman touching her private part invalidate wudu, and what are the madhhab positions?",
    },
  },
] as const;

const verificationMoments: Record<Language, string[]> = {
  ar: [
    "نفحص صياغة السؤال ونحدد مرساة البحث المناسبة.",
    "نسترجع الأدلة من القرآن والسنة والمراجع المعتمدة.",
    "نربط الادعاءات بالأدلة ونكشف التعارض أو النقص عند وجوده.",
    "نراجع صلاحية النشر قبل إظهار النتيجة النهائية.",
  ],
  en: [
    "We parse the question and detect the right research anchor.",
    "We retrieve governed evidence from trusted Islamic sources.",
    "We connect claims to evidence and surface disagreement or gaps.",
    "We review publication safety before showing the final result.",
  ],
};

const experienceWords: Record<
  string,
  {
    ar: { label: string; headline: string; detail: string };
    en: { label: string; headline: string; detail: string };
  }
> = {
  verified: {
    ar: {
      label: "إجابة موثقة",
      headline: "الإجابة اجتازت بوابة التحقق",
      detail: "الادعاءات المنشورة مرتبطة بالأدلة المستشهد بها واجتازت التحقق الدلالي.",
    },
    en: {
      label: "Verified answer",
      headline: "The answer passed the publication gate",
      detail: "Published claims are linked to cited evidence and passed semantic verification.",
    },
  },
  grounded: {
    ar: {
      label: "إجابة مرتبطة بالمصادر",
      headline: "الإجابة مبنية على أدلة قابلة للتتبع",
      detail: "المصادر مرتبطة بالإجابة، لكن التحقق الدلالي الكامل غير مفعّل لهذا المسار.",
    },
    en: {
      label: "Source-grounded answer",
      headline: "The answer is traceable to its evidence",
      detail: "Sources are linked, but full semantic verification is not enabled for this path.",
    },
  },
  limited: {
    ar: {
      label: "إجابة مع قيود",
      headline: "يمكن عرض الإجابة مع توضيح حدودها",
      detail: "الأدلة تسمح بالإجابة، مع وجود قيود يجب أن تبقى ظاهرة للمستخدم.",
    },
    en: {
      label: "Answer with limitations",
      headline: "The answer can be shown with explicit limits",
      detail: "The evidence supports publication, but important limitations remain visible.",
    },
  },
  conflict: {
    ar: {
      label: "يوجد خلاف في الأدلة",
      headline: "تم الحفاظ على الخلاف بدل إخفائه",
      detail: "المصادر تحتوي على اختلاف معتبر، لذلك لا تختار بصيرة رأيًا واحدًا تلقائيًا.",
    },
    en: {
      label: "Evidence disagreement",
      headline: "The disagreement was preserved",
      detail: "The sources differ, so Basira does not silently select one view.",
    },
  },
  needs_more_evidence: {
    ar: {
      label: "الأدلة غير كافية",
      headline: "يلزم استرجاع أدلة إضافية",
      detail: "لم تتحقق متطلبات الأدلة اللازمة لإجابة قابلة للنشر.",
    },
    en: {
      label: "More evidence required",
      headline: "Additional evidence is needed",
      detail: "The evidence requirements for a publishable answer were not satisfied.",
    },
  },
  regenerate: {
    ar: {
      label: "تحتاج الصياغة إلى إعادة توليد",
      headline: "الأدلة موجودة لكن الصياغة لم تجتز التحقق",
      detail: "تم إيقاف نشر الصياغة الحالية حتى تُعاد صياغتها بما يطابق الأدلة.",
    },
    en: {
      label: "Regeneration required",
      headline: "Evidence exists, but the wording failed verification",
      detail: "Publication was stopped until the wording can be regenerated against the cited evidence.",
    },
  },
  blocked: {
    ar: {
      label: "تم حجب الإجابة",
      headline: "فشل تحقق حاسم قبل النشر",
      detail: "لا تسمح بوابة التحقق بنشر الإجابة الحالية.",
    },
    en: {
      label: "Answer blocked",
      headline: "A critical verification failed",
      detail: "The publication gate does not allow this answer to be shown.",
    },
  },
  expert_review: {
    ar: {
      label: "تحتاج مراجعة خبير",
      headline: "تم تحويل الحالة إلى مراجعة بشرية مؤهلة",
      detail: "لا تصدر بصيرة حكمًا مستقلًا في هذه الحالة عالية الحساسية.",
    },
    en: {
      label: "Expert review required",
      headline: "The case was escalated for qualified human review",
      detail: "Basira does not publish an autonomous ruling for this high-sensitivity case.",
    },
  },
  abstained: {
    ar: {
      label: "لم تُنشر إجابة",
      headline: "اختارت بصيرة الامتناع عن الإجابة",
      detail: "حالة الأدلة الحالية لا تسمح بإجابة موثوقة.",
    },
    en: {
      label: "No answer published",
      headline: "Basira abstained from answering",
      detail: "The current evidence state does not support a trustworthy answer.",
    },
  },
};

const domainWords: Record<string, { ar: string; en: string }> = {
  quran: { ar: "القرآن الكريم", en: "Quran" },
  hadith: { ar: "الحديث", en: "Hadith" },
  tafsir: { ar: "التفسير", en: "Tafsir" },
  revelation_context: { ar: "أسباب النزول", en: "Revelation context" },
  fiqh: { ar: "الفقه", en: "Fiqh" },
  fatwa: { ar: "الفتوى", en: "Fatwa" },
  aqidah: { ar: "العقيدة", en: "Aqidah" },
  sirah: { ar: "السيرة", en: "Sirah" },
  sira: { ar: "السيرة", en: "Sirah" },
  history: { ar: "التاريخ", en: "History" },
  language: { ar: "اللغة", en: "Language" },
  general: { ar: "مرجع", en: "Reference" },
};

function stateIcon(state: string, size = 20) {
  if (state === "verified" || state === "grounded") {
    return <ShieldCheck size={size} />;
  }

  if (state === "conflict") {
    return <Scale size={size} />;
  }

  if (state === "regenerate") {
    return <RefreshCcw size={size} />;
  }

  if (state === "blocked" || state === "abstained") {
    return <ShieldAlert size={size} />;
  }

  return <CircleAlert size={size} />;
}

function domainIcon(domain: string, size = 20) {
  if (domain === "quran") {
    return <BookOpen size={size} />;
  }

  if (domain === "hadith") {
    return <Link2 size={size} />;
  }

  if (domain === "tafsir") {
    return <Library size={size} />;
  }

  if (domain === "revelation_context") {
    return <FileSearch size={size} />;
  }

  return <FileText size={size} />;
}

function localizedDomain(domain: string, language: Language) {
  return domainWords[domain]?.[language] ?? domain.replaceAll("_", " ");
}

function semanticLabel(status: string, language: Language) {
  const labels: Record<string, { ar: string; en: string }> = {
    pass: { ar: "اجتاز", en: "Passed" },
    regenerate: { ar: "إعادة توليد", en: "Regenerate" },
    block: { ar: "فشل حاسم", en: "Blocked" },
    not_enabled: { ar: "غير مفعّل", en: "Not enabled" },
  };

  return labels[status]?.[language] ?? status.replaceAll("_", " ");
}

function normalizeGrade(value: string) {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function isWeakGrade(value: string) {
  const normalized = normalizeGrade(value);

  return [
    "ضعيف",
    "ضعفه",
    "لا يصح",
    "لا يثبت",
    "موضوع",
    "منكر",
    "واه",
    "weak",
    "daif",
    "da'if",
    "fabricated",
    "mawdu",
  ].some((marker) => normalized.includes(marker));
}

function hadithSignal(response: QueryResponse, language: Language): HadithSignal | null {
  const grades = response.evidence.filter(
    (item) => item.domain === "hadith" && item.claim_type === "hadith_grade" && item.claim_value,
  );

  const hasGradeConflict = response.conflicts.some(
    (item) => item.type === "hadith_grade" || item.type.includes("hadith"),
  );

  if (hasGradeConflict) {
    return {
      kind: "conflict",
      label: copy[language].hadithConflict,
      detail: copy[language].hadithConflictDetail,
      grades,
    };
  }

  if (grades.some((item) => isWeakGrade(item.claim_value ?? ""))) {
    return {
      kind: "weak",
      label: copy[language].hadithWeak,
      detail: copy[language].hadithWeakDetail,
      grades,
    };
  }

  if (grades.length > 0) {
    return {
      kind: "graded",
      label: copy[language].hadithGrade,
      detail:
        language === "ar"
          ? "تُعرض الدرجة كما نُسبت إلى مصدرها دون إعادة تصنيفها من الواجهة."
          : "The grade is shown exactly as attributed to its source; the UI does not re-grade it.",
      grades,
    };
  }

  return null;
}

function fallbackExperience(response: QueryResponse): QueryExperience {
  let state: ExperienceState = "abstained";

  if (response.action === "answer" && response.has_answer) {
    state = "grounded";
  } else if (response.action === "answer_with_limitation") {
    state = "limited";
  } else if (response.action === "retrieve_more") {
    state = "needs_more_evidence";
  } else if (response.action === "escalate_to_expert") {
    state = "expert_review";
  }

  if (response.conflicts.length > 0 && response.has_answer) {
    state = "conflict";
  }

  const words = experienceWords[state]?.ar ?? experienceWords.abstained.ar;

  return {
    state,
    severity: state === "grounded" ? "info" : state === "abstained" ? "danger" : "warning",
    label: words.label,
    headline: words.headline,
    detail: words.detail,
    can_publish: response.has_answer,
    evidence_count: response.evidence.length,
    used_evidence_count: response.evidence.filter((item) => item.used_in_answer).length,
    source_count: new Set(response.evidence.map((item) => item.source_id)).size,
    trace: [],
  };
}

function traceLabel(step: QueryExperienceTraceStep, language: Language) {
  if (language === "ar") {
    return step.label;
  }

  const labels: Record<string, string> = {
    understanding: "Understand the question",
    evidence: "Retrieve evidence",
    requirements: "Check evidence sufficiency",
    conflicts: "Preserve disagreement",
    publication: "Publication decision",
  };

  return labels[step.key] ?? step.label;
}

function traceSummary(step: QueryExperienceTraceStep, language: Language) {
  if (language === "ar") {
    return step.summary;
  }

  const summaries: Record<string, string> = {
    understanding: "The question was classified and routed to the appropriate reasoning path.",
    evidence: "Governed evidence was retrieved from the available source set.",
    requirements: "Required evidence obligations were evaluated before answering.",
    conflicts: "Conflicting or differing evidence was preserved instead of silently collapsed.",
    publication: "The final publication gate decided whether the answer could be shown.",
  };

  return summaries[step.key] ?? step.summary;
}

function referenceTitle(item: QueryEvidence) {
  return item.work_title ?? item.author_name ?? item.institution ?? item.source_id;
}


type TrustShieldTone = "complete" | "warning" | "blocked";

type TrustShieldLayer = {
  key: "integrity" | "requirements" | "conflicts" | "publication";
  label: string;
  detail: string;
  value: string;
  tone: TrustShieldTone;
};

function trustShieldLayers(
  response: QueryResponse,
  experience: QueryExperience,
  language: Language,
): TrustShieldLayer[] {
  const report = response.integrity_report;
  const integrity = report?.literal_source_integrity ?? "not_applicable";
  const integrityPassed = integrity === "passed";
  const integrityNotApplicable = integrity === "not_applicable";

  const resolvedRequirementStates = new Set(["satisfied", "no_attested_entry"]);
  const resolvedRequirements = response.requirements.filter((item) =>
    resolvedRequirementStates.has(item.state),
  ).length;
  const requirementsComplete =
    response.requirements.length === 0 || resolvedRequirements === response.requirements.length;

  const hasConflict = response.conflicts.length > 0;
  const publicationTone: TrustShieldTone = experience.can_publish
    ? "complete"
    : ["needs_more_evidence", "regenerate", "expert_review"].includes(experience.state)
      ? "warning"
      : "blocked";

  if (language === "ar") {
    return [
      {
        key: "integrity",
        label: "سلامة الاستشهاد",
        detail: integrityPassed
          ? "النصوص المنشورة مرتبطة بمصادرها دون تغيير."
          : integrityNotApplicable
            ? "لا توجد ادعاءات منشورة تحتاج فحصًا حرفيًا في هذه الحالة."
            : "لم تجتز سلامة الاستشهاد الفحص المطلوب.",
        value: integrityPassed ? "اجتاز" : integrityNotApplicable ? "غير منطبق" : integrity,
        tone: integrityPassed ? "complete" : integrityNotApplicable ? "warning" : "blocked",
      },
      {
        key: "requirements",
        label: "متطلبات الدليل",
        detail: requirementsComplete
          ? "تم حسم متطلبات الدليل المعلنة لهذا السؤال."
          : "ما زالت بعض متطلبات الدليل دون حسم.",
        value:
          response.requirements.length === 0
            ? "لا متطلبات إضافية"
            : `${resolvedRequirements}/${response.requirements.length}`,
        tone: requirementsComplete ? "complete" : "warning",
      },
      {
        key: "conflicts",
        label: "الخلاف والتعارض",
        detail: hasConflict
          ? "تم الحفاظ على الخلاف وإظهاره بدل دمجه أو إخفائه."
          : "لم يُكتشف تعارض بين الأدلة المنشورة.",
        value: hasConflict ? `${response.conflicts.length} محفوظ` : "لا تعارض",
        tone: hasConflict ? "warning" : "complete",
      },
      {
        key: "publication",
        label: "بوابة النشر",
        detail: experience.can_publish
          ? "سمحت البوابة بعرض النتيجة الحالية للمستخدم."
          : "أوقفت البوابة نشر إجابة موضوعية في الحالة الحالية.",
        value: experience.can_publish ? "مسموح" : "متوقف",
        tone: publicationTone,
      },
    ];
  }

  return [
    {
      key: "integrity",
      label: "Citation integrity",
      detail: integrityPassed
        ? "Published text remains linked to its source without alteration."
        : integrityNotApplicable
          ? "No published claims require literal integrity checking in this state."
          : "Citation integrity did not pass the required check.",
      value: integrityPassed ? "Passed" : integrityNotApplicable ? "N/A" : integrity,
      tone: integrityPassed ? "complete" : integrityNotApplicable ? "warning" : "blocked",
    },
    {
      key: "requirements",
      label: "Evidence obligations",
      detail: requirementsComplete
        ? "Declared evidence requirements were resolved for this question."
        : "Some evidence requirements remain unresolved.",
      value:
        response.requirements.length === 0
          ? "No extra obligations"
          : `${resolvedRequirements}/${response.requirements.length}`,
      tone: requirementsComplete ? "complete" : "warning",
    },
    {
      key: "conflicts",
      label: "Disagreement",
      detail: hasConflict
        ? "The disagreement is preserved and shown instead of being collapsed."
        : "No conflict was detected among the published evidence.",
      value: hasConflict ? `${response.conflicts.length} preserved` : "No conflict",
      tone: hasConflict ? "warning" : "complete",
    },
    {
      key: "publication",
      label: "Publication gate",
      detail: experience.can_publish
        ? "The publication gate allows the current result to be shown."
        : "The publication gate stopped a substantive answer in the current state.",
      value: experience.can_publish ? "Allowed" : "Stopped",
      tone: publicationTone,
    },
  ];
}

function trustShieldIcon(tone: TrustShieldTone) {
  if (tone === "complete") {
    return <Check size={15} />;
  }

  if (tone === "warning") {
    return <CircleAlert size={15} />;
  }

  return <ShieldAlert size={15} />;
}

function TrustShield({
  response,
  experience,
  semanticStatus,
  language,
}: {
  response: QueryResponse;
  experience: QueryExperience;
  semanticStatus: string;
  language: Language;
}) {
  const layers = trustShieldLayers(response, experience, language);
  const semantic = semanticLabel(semanticStatus, language);
  const title = language === "ar" ? "درع الثقة" : "Trust Shield";
  const caption =
    language === "ar"
      ? "ملخص بصري لحالة التحقق الحالية — لا يرفع درجة أي دليل ولا يخفي الخلاف."
      : "A visual summary of the current verification state — it never upgrades evidence or hides disagreement.";
  const evidenceLabel = language === "ar" ? "دليل" : "evidence";
  const sourcesLabel = language === "ar" ? "مصدر" : "sources";
  const semanticLabelText = language === "ar" ? "دلالي" : "semantic";

  return (
    <section className={`trust-shield trust-shield-${experience.severity}`} aria-label={title}>
      <div className="trust-shield-core">
        <div className="trust-shield-orbit orbit-one" />
        <div className="trust-shield-orbit orbit-two" />
        <div className="trust-shield-emblem">
          {stateIcon(experience.state, 34)}
        </div>
        <div className="trust-shield-core-copy">
          <small>{title}</small>
          <strong>{experience.label}</strong>
          <span>{experience.can_publish ? (language === "ar" ? "قابل للنشر" : "Publishable") : (language === "ar" ? "النشر متوقف" : "Publication stopped")}</span>
        </div>
        <div className="trust-shield-stats" aria-label="Trust shield statistics">
          <span><b>{experience.evidence_count}</b> {evidenceLabel}</span>
          <i />
          <span><b>{experience.source_count}</b> {sourcesLabel}</span>
          <i />
          <span><b>{semantic}</b> {semanticLabelText}</span>
        </div>
      </div>

      <div className="trust-shield-layers">
        {layers.map((layer, index) => (
          <article className={`trust-shield-layer tone-${layer.tone}`} key={layer.key}>
            <div className="trust-shield-layer-index">0{index + 1}</div>
            <span className="trust-shield-layer-icon">{trustShieldIcon(layer.tone)}</span>
            <div className="trust-shield-layer-copy">
              <small>{layer.label}</small>
              <strong>{layer.value}</strong>
              <p>{layer.detail}</p>
            </div>
          </article>
        ))}
      </div>

      <p className="trust-shield-caption">{caption}</p>
    </section>
  );
}

function SourceDrawer({
  detail,
  loading,
  error,
  language,
  onClose,
}: {
  detail: EvidenceDetail | null;
  loading: boolean;
  error: string | null;
  language: Language;
  onClose: () => void;
}) {
  const ui = copy[language];

  return (
    <div className="source-drawer-layer" role="presentation">
      <button className="source-drawer-backdrop" onClick={onClose} aria-label={ui.close} />
      <aside className="source-drawer" role="dialog" aria-modal="true" aria-label={ui.sourceText}>
        <div className="source-drawer-header">
          <div className="source-drawer-heading">
            <span className="source-drawer-icon">
              <Library size={20} />
            </span>
            <div>
              <small>{ui.sourceOriginal}</small>
              <h2>{detail?.work_title ?? detail?.source_id ?? ui.sourceText}</h2>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label={ui.close}>
            <X size={19} />
          </button>
        </div>

        {detail && (
          <div className="source-drawer-meta">
            {[detail.author_name, detail.publisher, detail.reference]
              .filter(Boolean)
              .map((value) => (
                <span key={value}>{value}</span>
              ))}
          </div>
        )}

        <div className="source-drawer-body">
          {loading && (
            <div className="drawer-state">
              <span className="spinner" />
              <span>{ui.loadingSource}</span>
            </div>
          )}
          {error && (
            <div className="drawer-state is-error">
              <CircleAlert size={18} />
              <span>{error}</span>
            </div>
          )}
          {detail && !loading && <article className="source-full-text">{detail.text}</article>}
        </div>
      </aside>
    </div>
  );
}

type TafsirPassageView = {
  key: string;
  evidence: QueryEvidence;
  provenanceIds: string[];
};

type TafsirSourceGroup = {
  sourceId: string;
  title: string;
  passages: TafsirPassageView[];
};

function normalizeEvidencePassage(
  value: string | null | undefined,
) {
  return (value ?? "")
    .replace(/\s+/g, " ")
    .trim();
}

function groupTafsirEvidence(
  items: QueryEvidence[],
): TafsirSourceGroup[] {
  const groups = new Map<
    string,
    TafsirSourceGroup
  >();

  for (const item of items) {
    if (item.domain !== "tafsir") {
      continue;
    }

    const text =
      item.display_excerpt ??
      item.text;

    // A visible passage must contain actual text.
    // Text-less retrieved records remain in the backend
    // response / trace but do not become empty UI passages.
    if (!text?.trim()) {
      continue;
    }

    const sourceId = item.source_id;

    let group = groups.get(sourceId);

    if (!group) {
      group = {
        sourceId,
        title:
          item.work_title?.trim() ||
          item.source_id,
        passages: [],
      };

      groups.set(
        sourceId,
        group,
      );
    } else if (
      group.title === group.sourceId &&
      item.work_title?.trim()
    ) {
      group.title =
        item.work_title.trim();
    }

    const normalizedText =
      normalizeEvidencePassage(text);

    const passageKey = [
      item.reference ?? "",
      normalizedText,
    ].join("::");

    const existing =
      group.passages.find(
        (passage) =>
          passage.key === passageKey,
      );

    if (existing) {
      if (
        !existing.provenanceIds.includes(
          item.evidence_id,
        )
      ) {
        existing.provenanceIds.push(
          item.evidence_id,
        );
      }

      // Prefer the record actually used in the answer
      // while preserving every provenance id.
      if (
        item.used_in_answer &&
        !existing.evidence.used_in_answer
      ) {
        existing.evidence = item;
      }

      continue;
    }

    group.passages.push({
      key: passageKey,
      evidence: item,
      provenanceIds: [
        item.evidence_id,
      ],
    });
  }

  return Array.from(
    groups.values(),
  ).filter(
    (group) =>
      group.passages.length > 0,
  );
}


function TafsirSourceCard({
  group,
  response,
  language,
}: {
  group: TafsirSourceGroup;
  response: QueryResponse;
  language: Language;
}) {
  const ui = copy[language];

  const sourceUsed =
    group.passages.some(
      (passage) =>
        passage.evidence.used_in_answer,
    );

  return (
    <article
      className={`evidence-card tafsir-source-card ${
        sourceUsed ? "is-used" : ""
      }`}
    >
      <div className="evidence-card-top tafsir-source-card__header">
        <div className="evidence-card-identity">
          <span className="evidence-domain-icon">
            {domainIcon("tafsir", 19)}
          </span>

          <div>
            <small>
              {localizedDomain(
                "tafsir",
                language,
              )}
            </small>

            <h3>{group.title}</h3>
          </div>
        </div>

        <span className="mini-badge used">
          <ShieldCheck size={12} />

          {language === "ar"
            ? "مصدر معتمد"
            : "Governed source"}
        </span>
      </div>

      <div className="governed-source-strip governed-source-strip--tafsir">
        <span className="governed-source-strip__icon">
          <ShieldCheck size={15} />
        </span>

        <div className="governed-source-strip__copy">
          <small>
            {language === "ar"
              ? "مصدر التفسير"
              : "Tafsir source"}
          </small>

          <strong>
            {group.title}
          </strong>

          <div className="governed-source-strip__meta">
            <code>
              {group.sourceId}
            </code>

            <span>
              {language === "ar"
                ? `${group.passages.length} مقاطع موثقة`
                : `${group.passages.length} governed passages`}
            </span>
          </div>
        </div>
      </div>

      <div className="tafsir-passages">
        {group.passages.map(
          ({
            evidence,
            provenanceIds,
            key,
          }) => {
            const excerpt =
              evidence.display_excerpt ??
              evidence.text;

            const linkedClaims =
              response.claims?.filter(
                (claim) =>
                  claim.evidence_ids.includes(
                    evidence.evidence_id,
                  ),
              ) ?? [];

            const usefulWorkTitle =
              evidence.work_title &&
              evidence.work_title !==
                group.title
                ? evidence.work_title
                : null;

            return (
              <section
                className="tafsir-passage"
                key={key}
              >
                <div className="tafsir-passage__heading">
                  <div>
                    {evidence.author_name && (
                      <strong className="tafsir-author">
                        {language === "ar"
                          ? `المفسر: ${evidence.author_name}`
                          : `Scholar: ${evidence.author_name}`}
                      </strong>
                    )}

                    {usefulWorkTitle && (
                      <span className="tafsir-work-title">
                        {usefulWorkTitle}
                      </span>
                    )}
                  </div>

                  {evidence.used_in_answer && (
                    <span className="mini-badge used">
                      <Check size={12} />
                      {ui.linkedToAnswer}
                    </span>
                  )}
                </div>

                {excerpt && (
                  <blockquote className="evidence-excerpt tafsir-passage__text">
                    {excerpt}
                  </blockquote>
                )}

                <div className="tafsir-passage__footer">
                  <div className="tafsir-passage__meta">
                    {evidence.reference && (
                      <span>
                        <b>
                          {language === "ar"
                            ? "المرجع"
                            : "Reference"}
                        </b>
                        {evidence.reference}
                      </span>
                    )}

                    {linkedClaims.length > 0 && (
                      <span>
                        {ui.claimsLinked}:{" "}
                        {linkedClaims.length}
                      </span>
                    )}

                    {provenanceIds.length > 1 && (
                      <span>
                        {language === "ar"
                          ? `${provenanceIds.length} سجلات provenance`
                          : `${provenanceIds.length} provenance records`}
                      </span>
                    )}
                  </div>

                  {evidence.source_url && (
                    <a
                      className="tafsir-original-source"
                      href={evidence.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ExternalLink size={14} />
                      {ui.sourceOriginal}
                    </a>
                  )}
                </div>
              </section>
            );
          },
        )}
      </div>
    </article>
  );
}


function EvidenceCard({
  item,
  response,
  language,
  onOpenDetail: _onOpenDetail,
}: {
  item: QueryEvidence;
  response: QueryResponse;
  language: Language;
  onOpenDetail: (id: string) => void;
}) {
  const ui = copy[language];
  const linkedClaims = response.claims?.filter((claim) => claim.evidence_ids.includes(item.evidence_id)) ?? [];
  const excerpt = item.display_excerpt ?? item.text;

  return (
    <article className={`evidence-card domain-${item.domain} ${item.used_in_answer ? "is-used" : ""}`}>
      <div className="evidence-card-top">
        <div className="evidence-card-identity">
          <span className="evidence-domain-icon">{domainIcon(item.domain, 19)}</span>
          <div>
            <small>{localizedDomain(item.domain, language)}</small>
            <h3>{referenceTitle(item)}</h3>
          </div>
        </div>
        <div className="evidence-card-badges">
          {item.used_in_answer && (
            <span className="mini-badge used">
              <Check size={12} />
              {ui.linkedToAnswer}
            </span>
          )}
          {!item.used_in_answer && <span className="mini-badge neutral">{ui.supportingOnly}</span>}
        </div>
      </div>

      <div className="governed-source-strip">
        <span className="governed-source-strip__icon">
          <ShieldCheck size={15} />
        </span>

        <div className="governed-source-strip__copy">
          <small>
            {language === "ar"
              ? "المصدر"
              : "Source"}
          </small>

          <strong>
            {referenceTitle(item)}
          </strong>

          <div className="governed-source-strip__meta">
            {item.reference && (
              <span>
                {language === "ar"
                  ? "المرجع"
                  : "Reference"}
                {" · "}
                {item.reference}
              </span>
            )}

            {item.author_name &&
              item.author_name !==
                referenceTitle(item) && (
                <span>
                  {language === "ar"
                    ? "النسبة"
                    : "Attribution"}
                  {" · "}
                  {item.author_name}
                </span>
              )}

            {item.institution && (
              <span>
                {item.institution}
              </span>
            )}

            {item.publisher && (
              <span>
                {item.publisher}
              </span>
            )}

            {item.source_id &&
              item.source_id !==
                referenceTitle(item) && (
                <code>
                  {item.source_id}
                </code>
              )}
          </div>
        </div>

        {item.source_url && (
          <a
            className="governed-source-link"
            href={item.source_url}
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={14} />
            {ui.sourceOriginal}
          </a>
        )}
      </div>

      {item.claim_type === "hadith_grade" && item.claim_value && (
        <div className={`hadith-grade-inline ${isWeakGrade(item.claim_value) ? "is-weak" : ""}`}>
          <span>{ui.hadithGrade}</span>
          <strong>{item.claim_value}</strong>
        </div>
      )}

      {excerpt && (
        <blockquote className={item.domain === "quran" ? "quran-excerpt" : "evidence-excerpt"}>
          {item.domain === "quran" ? "﴿ " : ""}
          {excerpt}
          {item.domain === "quran" ? " ﴾" : ""}
        </blockquote>
      )}

      <div className="evidence-card-meta">
        {item.reference && <span>{item.reference}</span>}
        {item.author_name && item.author_name !== referenceTitle(item) && <span>{item.author_name}</span>}
        {linkedClaims.length > 0 && (
          <span>
            {ui.claimsLinked}: {linkedClaims.length}
          </span>
        )}
      </div>

    </article>
  );
}


function VerificationOverlay({ language }: { language: Language }) {
  const [activeStep, setActiveStep] = useState(0);
  const steps = verificationMoments[language];

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveStep((current) => (current + 1) % steps.length);
    }, 2200);

    return () => {
      window.clearInterval(interval);
    };
  }, [steps]);

  return (
    <div className="verification-overlay" role="status" aria-live="polite" aria-label={language === "ar" ? "بصيرة تفكر" : "Basira is thinking"}>
      <div className="verification-overlay__backdrop" />
      <section className="verification-overlay__panel">
        <div className="verification-overlay__visuals" aria-hidden="true">
          <div className="verification-visual verification-visual--primary">
            <img src="/scenes/verification-visual-1.png" alt="" />
          </div>
          <div className="verification-visual verification-visual--secondary">
            <img src="/scenes/verification-visual-2.png" alt="" />
          </div>
          <div className="verification-overlay__pulse verification-overlay__pulse--one" />
          <div className="verification-overlay__pulse verification-overlay__pulse--two" />
          <div className="verification-overlay__signal" />
        </div>

        <div className="verification-overlay__copy">
          <div className="verification-badge">
            <Clock3 size={16} />
            <span>{language === "ar" ? "وضع التفكير" : "Thinking mode"}</span>
          </div>
          <h2>{language === "ar" ? "بصيرة تفكر قبل إظهار النتيجة" : "Basira is thinking before showing the result"}</h2>
          <p>
            {language === "ar"
              ? "تتحقق بصيرة من الأدلة والمرجع والصلة والكفاية قبل أن تقرر ما الذي يمكن نشره."
              : "Basira checks the evidence, anchor, relevance, and sufficiency before deciding what can be published."}
          </p>

          <div className="verification-steps">
            {steps.map((step, index) => (
              <div className={`verification-step ${index === activeStep ? "is-active" : ""}`} key={`${language}-${index}`}>
                <span className="verification-step__index">0{index + 1}</span>
                <span className="verification-step__text">{step}</span>
              </div>
            ))}
          </div>

          <div className="verification-progress" aria-hidden="true">
            <span />
          </div>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [language, setLanguage] = useState<Language>("ar");
  const [theme, setTheme] = useState<Theme>("light");
  const [query, setQuery] = useState("");
  const [queryReference, setQueryReference] = useState<string | undefined>();
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [traceOpen, setTraceOpen] = useState(true);
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState(false);
  const [sourceDetail, setSourceDetail] = useState<EvidenceDetail | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);

  const ui = copy[language];
  const direction = language === "ar" ? "rtl" : "ltr";

  const experience = useMemo(
    () => (response ? response.experience ?? fallbackExperience(response) : null),
    [response],
  );

  const experienceText = useMemo(() => {
    if (!experience) {
      return null;
    }

    return experienceWords[experience.state]?.[language] ?? {
      label: experience.label,
      headline: experience.headline,
      detail: experience.detail,
    };
  }, [experience, language]);

  const hadith = useMemo(
    () => (response ? hadithSignal(response, language) : null),
    [response, language],
  );

  useEffect(() => {
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  useEffect(() => {
    if (!sourceDrawerOpen) {
      return;
    }

    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSourceDrawerOpen(false);
      }
    };

    window.addEventListener("keydown", onKey);

    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [sourceDrawerOpen]);

  const choosePreset = (preset: Preset) => {
    setQuery(preset[language]);
    setQueryReference(preset.quranReference);
    setQueryError(null);
  };

  const toggleLanguage = () => {
    setLanguage((current) => (current === "ar" ? "en" : "ar"));
  };

  const startNewConversation = () => {
    setQuery("");
    setQueryReference(undefined);
    setResponse(null);
    setQueryError(null);
    setTraceOpen(true);
    setMobileHistoryOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const submitQuestion = async (questionOverride?: string, referenceOverride?: string) => {
    const question = (questionOverride ?? query).trim();
    const quranReference = referenceOverride ?? queryReference;

    if (!question || isVerifying) {
      return;
    }

    if (questionOverride) {
      setQuery(question);
      setQueryReference(referenceOverride);
    }

    setIsVerifying(true);
    setQueryError(null);


    try {
      const result = await queryBasira({
        question,
        quran_reference: quranReference,
        language,
      });


      setResponse(result);
      setTraceOpen(true);

      window.requestAnimationFrame(() => {
        document.getElementById("result-workspace")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    } catch {

      setQueryError(
        language === "ar"
          ? "تعذر إكمال التحقق الآن. تأكد من تشغيل خدمة بصيرة ثم حاول مرة أخرى."
          : "Basira could not complete verification. Make sure the API is running and try again.",
      );
    } finally {
      setIsVerifying(false);
    }
  };

  const openEvidenceDetail = async (evidenceId: string) => {
    setSourceDrawerOpen(true);
    setSourceDetail(null);
    setSourceError(null);
    setSourceLoading(true);

    try {
      const detail = await getEvidenceDetail(evidenceId);
      setSourceDetail(detail);
    } catch {
      setSourceError(ui.sourceLoadError);
    } finally {
      setSourceLoading(false);
    }
  };

  const semanticStatus = response?.integrity_report?.semantic_claim_verification ?? "not_enabled";
  const resolution = Math.round((response?.resolution_coverage ?? 0) * 100);
  const quranEvidence = response?.evidence.find((item) => item.domain === "quran" && item.text);

  const quranLocalized =
    language === "en"
      ? quranEvidence?.localized ?? null
      : null;

  const quranVerification =
    response?.quran_verification ?? null;

  const quranVerificationCandidate =
    quranVerification?.candidates?.[0] ?? null;

  const quranVerificationAltered =
    quranVerification?.status === "altered_text";

  const quranVerificationMatched =
    quranVerification?.status === "normalized_match" ||
    quranVerification?.status === "exact_match";

  const quranDisplayText =
    quranVerificationCandidate?.canonical_text ??
    quranEvidence?.text ??
    null;

  const quranDisplayReference =
    quranVerificationCandidate?.reference ??
    quranEvidence?.reference ??
    "";

  const quranVerificationSourceId =
    quranVerificationCandidate?.source_id ??
    quranEvidence?.source_id ??
    null;

  const quranVerificationSourceLabel =
    quranVerificationSourceId === "quranpedia:mushaf:1"
      ? language === "ar"
        ? "Quranpedia · المصحف المعتمد"
        : "Quranpedia · Canonical Mushaf"
      : quranVerificationSourceId;

  const hasQuranEvidence = Boolean(quranDisplayText);

  const quranPrimaryDifference =
    quranVerification?.differences?.[0] ?? null;

  const quranVerificationTrace =
    quranVerification
      ? [
          {
            key: "quran-understanding",
            label:
              language === "ar"
                ? "فهم السؤال"
                : "Understand the request",
            summary:
              language === "ar"
                ? "تم تحديد الطلب كتحقق حرفي من نص قرآني، وليس كسؤال بحث عام."
                : "The request was identified as literal Quran verification rather than a general retrieval question.",
            value:
              language === "ar"
                ? "تحقق نص قرآني"
                : "Quran text verification",
          },
          {
            key: "quran-source",
            label:
              language === "ar"
                ? "التحقق من المصدر القرآني"
                : "Verify against the Quran source",
            summary:
              language === "ar"
                ? `تمت مقارنة النص مباشرة بالمصدر القرآني المعتمد${
                    quranVerificationSourceLabel
                      ? ` — ${quranVerificationSourceLabel}`
                      : ""
                  }.`
                : `The submitted wording was compared directly with the governed canonical Quran source${
                    quranVerificationSourceLabel
                      ? ` — ${quranVerificationSourceLabel}`
                      : ""
                  }.`,
            value:
              quranVerificationSourceLabel ??
              (
                language === "ar"
                  ? "مصدر قرآني معتمد"
                  : "Governed Quran source"
              ),
          },
          {
            key: "quran-text-check",
            label:
              language === "ar"
                ? "فحص النص"
                : "Check the wording",
            summary:
              quranVerificationAltered &&
              quranPrimaryDifference
                ? language === "ar"
                  ? `تم اكتشاف اختلاف جوهري: ${
                      quranPrimaryDifference.received.join(" ")
                    } ← ${
                      quranPrimaryDifference.expected.join(" ")
                    }.`
                  : `A substantive wording difference was detected: ${
                      quranPrimaryDifference.received.join(" ")
                    } → ${
                      quranPrimaryDifference.expected.join(" ")
                    }.`
                : language === "ar"
                  ? "لم يُكتشف اختلاف جوهري بين النص المُرسل والنص القرآني المعتمد."
                  : "No substantive difference was detected between the submitted wording and the canonical Quran text.",
            value:
              quranVerificationAltered
                ? language === "ar"
                  ? "تم اكتشاف اختلاف"
                  : "Difference detected"
                : language === "ar"
                  ? "مطابق"
                  : "Matched",
          },
          {
            key: "quran-reference",
            label:
              language === "ar"
                ? "تثبيت المرجع"
                : "Resolve the reference",
            summary:
              language === "ar"
                ? `تم ربط النص بمرجعه القرآني المعتمد${
                    quranDisplayReference
                      ? `: ${quranDisplayReference}`
                      : "."
                  }`
                : `The text was resolved to its canonical Quran reference${
                    quranDisplayReference
                      ? `: ${quranDisplayReference}`
                      : "."
                  }`,
            value:
              quranDisplayReference ||
              (
                language === "ar"
                  ? "مرجع قرآني موثق"
                  : "Verified Quran reference"
              ),
          },
          {
            key: "quran-result",
            label:
              language === "ar"
                ? "نتيجة التحقق"
                : "Verification result",
            summary:
              quranVerificationAltered
                ? language === "ar"
                  ? "تم عرض موضع الاختلاف والنص الصحيح مباشرة من المصدر القرآني المعتمد؛ الذاكرة لم تحدد النص الصحيح."
                  : "The wording difference and canonical correction were shown directly from the governed Quran source; memory did not determine the correct text."
                : language === "ar"
                  ? "تم تأكيد مطابقة النص من المصدر القرآني المعتمد."
                  : "The wording match was confirmed from the governed canonical Quran source.",
            value:
              quranVerificationAltered
                ? language === "ar"
                  ? "تم التصحيح"
                  : "Correction shown"
                : language === "ar"
                  ? "تم التحقق"
                  : "Verified",
          },
        ]
      : null;

  const nonQuranClaims =
    response?.claims.filter(
      (claim) => claim.axis_id !== "quran",
    ) ?? [];

  const answerDisplayText =
    response?.has_answer && response.answer
      ? hasQuranEvidence
        ? nonQuranClaims
            .map((claim) => claim.text?.trim())
            .filter(Boolean)
            .join("\n\n") || null
        : response.answer
      : null;

  const nonQuranEvidence =
    response?.evidence.filter(
      (item) => item.domain !== "quran",
    ) ?? [];

  const tafsirSourceGroups =
    groupTafsirEvidence(
      nonQuranEvidence,
    );

  const nonTafsirEvidence =
    nonQuranEvidence.filter(
      (item) =>
        item.domain !== "tafsir",
    );

  const visibleEvidenceCardCount =
    nonTafsirEvidence.length +
    tafsirSourceGroups.length;

  const quranLocation =
    quranDisplayReference === "2:255"
      ? language === "ar"
        ? "سورة البقرة · الآية 255"
        : "Al-Baqarah · 2:255"
      : quranDisplayReference === "2:153"
        ? language === "ar"
          ? "سورة البقرة · الآية 153"
          : "Al-Baqarah · 2:153"
        : quranDisplayReference;


  return (
    <div className={`basira-app theme-${theme}`} dir={direction} lang={language}>
      {isVerifying && <VerificationOverlay language={language} />}
      {sourceDrawerOpen && (
        <SourceDrawer
          detail={sourceDetail}
          loading={sourceLoading}
          error={sourceError}
          language={language}
          onClose={() => setSourceDrawerOpen(false)}
        />
      )}

      <header className="main-header">
        <div className="header-inner">
          <button
            className="mobile-menu-button"
            type="button"
            onClick={() => setMobileHistoryOpen((value) => !value)}
            aria-label="Menu"
          >
            <Menu size={20} />
          </button>

          <a
            className="header-brand"
            href="#home"
            aria-label="Basira home"
            onClick={(event) => {
              event.preventDefault();

              startNewConversation();

              window.history.replaceState(
                null,
                "",
                window.location.pathname +
                  window.location.search,
              );

              window.scrollTo({
                top: 0,
                behavior: "smooth",
              });
            }}
          >
            <BasiraLogo dark={theme === "dark"} />
          </a>

          <nav className="main-navigation" aria-label="Main navigation">
            <a href="#about">{ui.about}</a>
            <a href="#memory" className="memory-nav-link">
              {language === "ar"
                ? "الحماية والتعلّم"
                : "Trust & Learning"}
              <span className="memory-nav-dot" />
            </a>
            <a href="#sources">{ui.sources}</a>
            <a href="#method">{ui.method}</a>
            <a href="#faq">{ui.faq}</a>
          </nav>

          <div className="header-actions">
            <button className="language-button" onClick={toggleLanguage} type="button">
              <Globe2 size={16} />
              {language === "ar" ? "EN" : "العربية"}
            </button>
            <button
              className="theme-button"
              onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
              type="button"
              aria-label={theme === "light" ? "Dark mode" : "Light mode"}
            >
              {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
            </button>
            <button
              className="start-button"
              type="button"
              onClick={() => {
                startNewConversation();

                window.history.replaceState(
                  null,
                  "",
                  window.location.pathname +
                    window.location.search,
                );

                window.requestAnimationFrame(() => {
                  const input =
                    document.getElementById(
                      "basira-query-input",
                    ) as HTMLInputElement | null;

                  input?.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                  });

                  window.setTimeout(
                    () => input?.focus(),
                    300,
                  );
                });
              }}
            >
              <UserRound size={16} />
              {ui.start}
            </button>
          </div>
        </div>
      </header>

      <main>
        <section id="home" className={`hero-scene ${response ? "has-result" : ""}`}>
          <div className="hero-arch hero-arch-left" />
          <div className="hero-arch hero-arch-right" />
          <div className="hero-light" />

          <div className="hero-content">
            {!response && (
              <>
                <div className="trust-kicker">
                  <ShieldCheck size={16} />
                  {ui.kicker}
                </div>
                <h1>
                  {ui.heroLine1}
                  <br />
                  <span>{ui.heroLine2}</span>
                </h1>
                <p className="hero-subtitle">{ui.heroSubtitle}</p>
              </>
            )}

            <div className="hero-search-shell">
              <Search size={21} className="search-icon" />
              <input
                id="basira-query-input"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setQueryReference(undefined);
                  setQueryError(null);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    void submitQuestion();
                  }
                }}
                placeholder={ui.placeholder}
                aria-label={ui.placeholder}
              />
              <button type="button" onClick={() => void submitQuestion()} disabled={isVerifying}>
                {isVerifying ? <span className="spinner" /> : <Sparkles size={16} />}
                {isVerifying ? ui.verifying : ui.verify}
              </button>
            </div>

            {queryError && (
              <div className="query-error" role="alert">
                <CircleAlert size={18} />
                <span>{queryError}</span>
              </div>
            )}

            {!response && (
              <div className="suggested-questions">
                <span>{ui.examples}</span>
                <div>
                  {presets.slice(0, 4).map((preset) => (
                    <button key={preset.ar} type="button" onClick={() => choosePreset(preset)}>
                      <Search size={13} />
                      {preset[language]}
                    </button>
                  ))}
                </div>
              </div>
            )}

          </div>
        </section>

        {!response && (
          <section id="method" className="method-section">
            <div className="section-heading centered">
              <small>{language === "ar" ? "لماذا تختلف بصيرة؟" : "WHY BASIRA IS DIFFERENT"}</small>
              <h2>{language === "ar" ? "طريقة عمل بصيرة" : "How Basira works"}</h2>
              <p>
                {language === "ar"
                  ? "من سؤالك إلى قرار نشر واضح، مع بقاء الدليل والخلاف والقيود مرئية."
                  : "From your question to an explicit publication decision, with evidence, disagreement, and limitations kept visible."}
              </p>
            </div>

            <div className="method-grid">
              {[
                {
                  icon: <CircleAlert size={25} />,
                  title: language === "ar" ? "تطرح سؤالك" : "Ask naturally",
                  text: language === "ar" ? "بالعربية الطبيعية دون صياغة تقنية." : "Use natural language, not a technical query syntax.",
                },
                {
                  icon: <Search size={25} />,
                  title: language === "ar" ? "نبحث في المصادر" : "Retrieve governed sources",
                  text: language === "ar" ? "وفق نوع السؤال والمرجع المثبت." : "According to the question type and verified anchors.",
                },
                {
                  icon: <Layers3 size={25} />,
                  title: language === "ar" ? "نفحص الصلة والكفاية" : "Check relevance & sufficiency",
                  text: language === "ar" ? "المصدر الموثوق لا يكفي إذا كان عن سياق آخر." : "A trusted source is not enough when it addresses the wrong context.",
                },
                {
                  icon: <ShieldCheck size={25} />,
                  title: language === "ar" ? "نقرر ما يمكن نشره" : "Gate publication",
                  text: language === "ar" ? "نجيب، نقيّد، نطلب مزيدًا من الدليل، أو نمتنع." : "Answer, limit, retrieve more, escalate, or abstain.",
                },
              ].map((item, index) => (
                <article className="method-card" key={item.title}>
                  <span className="method-index">0{index + 1}</span>
                  <span className="method-icon">{item.icon}</span>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </article>
              ))}
            </div>
          </section>
        )}

        {response && experience && experienceText && (
          <section id="result-workspace" className="result-workspace">
            <aside className={`history-panel ${mobileHistoryOpen ? "is-open" : ""}`}>
              <button type="button" className="new-chat-button" onClick={startNewConversation}>
                <FileText size={17} />
                {ui.newConversation}
                <span>+</span>
              </button>

              <div className="history-heading">
                <Clock3 size={14} />
                {ui.today}
              </div>

              <button type="button" className="history-item active">
                <span>{response.question}</span>
              </button>

              {presets.slice(0, 4).map((preset) => (
                <button
                  className="history-item"
                  type="button"
                  key={preset.ar}
                  onClick={() => choosePreset(preset)}
                >
                  <span>{preset[language]}</span>
                </button>
              ))}
            </aside>

            {mobileHistoryOpen && (
              <button
                className="mobile-history-backdrop"
                aria-label="Close"
                type="button"
                onClick={() => setMobileHistoryOpen(false)}
              />
            )}

            <div className="conversation-panel">
              <div className="question-row">
                <div className="question-avatar">
                  <UserRound size={21} />
                </div>
                <div className="question-bubble">{response.question}</div>
              </div>

              <article className={`answer-card state-${experience.state}`}>
                <header className={`answer-card-header ${quranVerification ? "is-quran-verification" : ""}`}>
                  <div className="answer-brand-mark">
                    {quranVerification
                      ? quranVerificationAltered
                        ? <ShieldAlert size={22} />
                        : <ShieldCheck size={22} />
                      : stateIcon(experience.state, 22)}
                  </div>

                  <div className="answer-header-copy">
                    {quranVerification ? (
                      <>
                        <div
                          className={`trust-state-pill ${
                            quranVerificationAltered
                              ? "quran-verification-pill--danger"
                              : "quran-verification-pill--success"
                          }`}
                        >
                          {quranVerificationAltered
                            ? <ShieldAlert size={14} />
                            : <ShieldCheck size={14} />}

                          <span>
                            {language === "ar"
                              ? "تحقق نصي من القرآن"
                              : "Canonical Quran verification"}
                          </span>
                        </div>

                        <h2>
                          {quranVerificationAltered
                            ? language === "ar"
                              ? "تم اكتشاف اختلاف في النص القرآني"
                              : "A Quran wording difference was detected"
                            : quranVerificationMatched
                              ? language === "ar"
                                ? "النص يطابق المصدر القرآني المعتمد"
                                : "The quotation matches the canonical Quran text"
                              : language === "ar"
                                ? "تم تنفيذ التحقق النصي"
                                : "Quran text verification completed"}
                        </h2>

                        <p>
                          {language === "ar"
                            ? "قورِن النص مباشرة بالمصدر القرآني المعتمد؛ النتيجة لا تعتمد على إجابة مولّدة."
                            : "The quotation was compared directly with the governed canonical Quran source; the result does not depend on generated wording."}
                        </p>
                      </>
                    ) : (
                      <>
                        <div className={`trust-state-pill state-${experience.state}`}>
                          {stateIcon(experience.state, 14)}
                          <span>{experienceText.label}</span>
                        </div>

                        <h2>{experienceText.headline}</h2>
                        <p>{experienceText.detail}</p>
                      </>
                    )}
                  </div>
                </header>

                {quranVerification ? (
                  <section
                    className={`quran-verification-card ${
                      quranVerificationAltered
                        ? "is-altered"
                        : "is-matched"
                    }`}
                  >
                    <div className="quran-verification-card__top">
                      <div>
                        <small>
                          {language === "ar"
                            ? "CANONICAL TEXT CHECK"
                            : "CANONICAL TEXT CHECK"}
                        </small>

                        <strong>
                          {quranVerificationAltered
                            ? language === "ar"
                              ? "النص المرسل لا يطابق النص القرآني"
                              : "The submitted wording does not match"
                            : language === "ar"
                              ? "النص المرسل مطابق"
                              : "The submitted wording matches"}
                        </strong>
                      </div>

                      <span className="quran-verification-status">
                        {quranVerification.status.replaceAll("_", " ")}
                      </span>
                    </div>

                    {quranVerification.differences.length > 0 ? (
                      <div className="quran-verification-differences">
                        {quranVerification.differences.map(
                          (difference, index) => (
                            <div
                              className="quran-verification-difference"
                              key={`${difference.kind}-${index}`}
                            >
                              <div>
                                <small>
                                  {language === "ar"
                                    ? "الكلمة الواردة — غير مطابقة"
                                    : "Received — incorrect"}
                                </small>

                                <strong className="quran-word quran-word--wrong">
                                  {difference.received.join(" ")}
                                </strong>
                              </div>

                              <span className="quran-word-arrow">
                                {direction === "rtl" ? "←" : "→"}
                              </span>

                              <div>
                                <small>
                                  {language === "ar"
                                    ? "النص الصحيح المعتمد"
                                    : "Canonical correction"}
                                </small>

                                <strong className="quran-word quran-word--correct">
                                  {difference.expected.join(" ")}
                                </strong>
                              </div>
                            </div>
                          ),
                        )}
                      </div>
                    ) : (
                      <div className="quran-verification-match">
                        <ShieldCheck size={18} />
                        <span>
                          {language === "ar"
                            ? "لم يُكتشف اختلاف جوهري في النص."
                            : "No substantive wording difference was detected."}
                        </span>
                      </div>
                    )}

                    {quranVerificationSourceLabel && (
                      <div className="quran-verification-source">
                        <ShieldCheck size={16} />

                        <div>
                          <small>
                            {language === "ar"
                              ? "مصدر التحقق"
                              : "Verification source"}
                          </small>

                          <strong>
                            {quranVerificationSourceLabel}
                          </strong>

                          {quranDisplayReference && (
                            <span>
                              {language === "ar"
                                ? `المرجع القرآني · ${quranDisplayReference}`
                                : `Quran reference · ${quranDisplayReference}`}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    <p className="quran-verification-card__principle">
                      {language === "ar"
                        ? "الذاكرة تحدد متى يصبح التحقق إلزاميًا؛ المصدر القرآني المعتمد وحده يحدد النص الصحيح."
                        : "Memory decides when verification is mandatory. The canonical Quran source alone decides what is correct."}
                    </p>
                  </section>
                ) : (
                  <TrustShield
                    response={response}
                    experience={experience}
                    semanticStatus={semanticStatus}
                    language={language}
                  />
                )}

                {quranDisplayText && (
                  <section
                    className="quran-mushaf"
                    aria-label={
                      language === "ar"
                        ? "النص القرآني الموثق"
                        : "Verified Quran text"
                    }
                  >
                    <div className="quran-mushaf__header">
                      <span className="quran-mushaf__ornament">۞</span>

                      <div>
                        <small>
                          {language === "ar"
                            ? "القرآن الكريم"
                            : "THE HOLY QURAN"}
                        </small>

                        <strong>{quranLocation}</strong>
                      </div>

                      <span className="quran-mushaf__ornament">۞</span>
                    </div>

                    <div className="quran-mushaf__frame">
                      <p dir="rtl" lang="ar">
                        ﴿ {quranDisplayText} ﴾
                      </p>
                    </div>

                    {language === "en" &&
                      quranLocalized?.text && (
                        <div
                          className="quran-mushaf__translation"
                          dir="ltr"
                          lang="en"
                        >
                          <small>
                            TRUSTED ENGLISH MEANING
                          </small>

                          <p>{quranLocalized.text}</p>

                          <div className="quran-mushaf__translation-source">
                            <ShieldCheck size={13} />

                            <span>
                              {quranLocalized.work_title ??
                                "Source-native English translation"}
                            </span>

                            {quranLocalized.source_id && (
                              <code>
                                {quranLocalized.source_id}
                              </code>
                            )}
                          </div>
                        </div>
                      )}

                    <div className="quran-mushaf__footer">
                      <ShieldCheck size={14} />

                      <div className="quran-mushaf__source">
                        <span>
                          {language === "ar"
                            ? quranVerification
                              ? "النص الصحيح من المصدر القرآني المعتمد — لا يأتي من الذاكرة"
                              : "نص قرآني موثق من المصدر المعتمد"
                            : quranVerification
                              ? "Canonical Quran text — supplied by the governed source, not memory"
                              : "Verified Quran text from the governed source"}
                        </span>

                        {quranVerificationSourceLabel && (
                          <strong>
                            {quranVerificationSourceLabel}
                            {quranDisplayReference
                              ? ` · ${quranDisplayReference}`
                              : ""}
                          </strong>
                        )}
                      </div>
                    </div>
                  </section>
                )}

                {answerDisplayText ? (
                  <section className="answer-main">
                    <div className="answer-section-title">
                      <span>
                        {language === "ar"
                          ? "الشرح والنتيجة"
                          : "Explanation & result"}
                      </span>

                      <span className="resolution-chip">
                        {resolution}% {ui.resolution}
                      </span>
                    </div>

                    <p className="answer-copy" dir="auto">
                      {answerDisplayText}
                    </p>
                  </section>
                ) : !response.has_answer && !quranVerification ? (
                  <section className="withheld-answer">
                    <span className="withheld-icon">
                      {stateIcon(experience.state, 26)}
                    </span>

                    <div>
                      <h3>{ui.noPublishableAnswer}</h3>
                      <p>{experienceText.detail}</p>
                    </div>
                  </section>
                ) : null}

                {!quranVerification &&
                  response.limitations.length > 0 && (
                  <section className="limitations-panel">
                    <div className="limitations-title">
                      <CircleAlert size={18} />
                      <strong>{ui.limitations}</strong>
                    </div>
                    {response.limitations.map((item) => (
                      <p key={item}>{item}</p>
                    ))}
                  </section>
                )}

                {hadith && (
                  <section className={`hadith-signal hadith-${hadith.kind}`}>
                    <div className="hadith-signal-heading">
                      <span className="hadith-signal-icon">
                        {hadith.kind === "conflict" ? <Scale size={20} /> : <AlertTriangle size={20} />}
                      </span>
                      <div>
                        <h3>{hadith.label}</h3>
                        <p>{hadith.detail}</p>
                      </div>
                    </div>

                    {hadith.grades.length > 0 && (
                      <div className="hadith-grades-grid">
                        {hadith.grades.map((grade) => (
                          <div className="hadith-grade-card" key={grade.evidence_id}>
                            <span>{referenceTitle(grade)}</span>
                            <strong>{grade.claim_value}</strong>
                            {grade.reference && <small>{grade.reference}</small>}
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                )}

                {response.conflicts.length > 0 && (
                  <section className="conflict-panel">
                    <div className="conflict-heading">
                      <Scale size={20} />
                      <div>
                        <h3>{ui.conflictTitle}</h3>
                        <p>{ui.conflictDetail}</p>
                      </div>
                    </div>

                    <div className="conflict-groups">
                      {response.conflicts.map((conflict) => {
                        const conflictEvidence = response.evidence.filter((item) =>
                          conflict.evidence_ids.includes(item.evidence_id),
                        );

                        return (
                          <div className="conflict-group" key={conflict.group_id}>
                            <div className="conflict-group-title">
                              <span>{conflict.type.replaceAll("_", " ")}</span>
                              <small>{conflict.group_id}</small>
                            </div>
                            <div className="conflict-values">
                              {conflictEvidence.map((item) => (
                                <div key={item.evidence_id}>
                                  <span>{referenceTitle(item)}</span>
                                  <strong>{item.claim_value ?? item.display_excerpt ?? item.reference ?? item.evidence_id}</strong>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}

                {response.unavailable_domains.length > 0 && (
                  <section className="source-unavailable-panel">
                    <CircleAlert size={18} />
                    <div>
                      <strong>{ui.sourceUnavailable}</strong>
                      <p>{response.unavailable_domains.map((domain) => localizedDomain(domain, language)).join(" · ")}</p>
                    </div>
                  </section>
                )}

                {response.expert_review && (
                  <section className="expert-review-panel">
                    <ShieldAlert size={20} />
                    <div>
                      <h3>{ui.expertReview}</h3>
                      <p>{response.expert_review.escalation_reasons.join(" · ")}</p>
                      <small>{ui.caseNumber}: {response.expert_review.case_id}</small>
                    </div>
                  </section>
                )}

                {nonQuranEvidence.length > 0 && (
                <section id="sources" className="evidence-section">
                  <div className="section-heading-row">
                    <div>
                      <small>{language === "ar" ? "EVIDENCE" : "EVIDENCE"}</small>
                      <h2>{ui.evidence}</h2>
                      <p>{ui.evidenceIntro}</p>
                    </div>
                    <span className="evidence-total">{visibleEvidenceCardCount}</span>
                  </div>

                  <div className="evidence-grid">
                    {tafsirSourceGroups.map((group) => (
                      <TafsirSourceCard
                        key={group.sourceId}
                        group={group}
                        response={response}
                        language={language}
                      />
                    ))}

                    {nonTafsirEvidence.map((item) => (
                      <EvidenceCard
                        key={item.evidence_id}
                        item={item}
                        response={response}
                        language={language}
                        onOpenDetail={(id) => void openEvidenceDetail(id)}
                      />
                    ))}
                  </div>
                </section>

                )}

                <section className="reasoning-section">
                  <button
                    type="button"
                    className="reasoning-toggle"
                    onClick={() => setTraceOpen((value) => !value)}
                    aria-expanded={traceOpen}
                  >
                    <span className="reasoning-toggle-icon"><ShieldCheck size={20} /></span>
                    <span>
                      <small>{language === "ar" ? "VERIFICATION TRACE" : "VERIFICATION TRACE"}</small>
                      <strong>{ui.reasoning}</strong>
                    </span>
                    <span className={`reasoning-chevron ${traceOpen ? "is-open" : ""}`}>
                      <ChevronDown size={19} />
                    </span>
                  </button>

                  {traceOpen && (
                    <div className="reasoning-body">
                      {quranVerificationTrace ? (
                        quranVerificationTrace.map(
                          (step, index) => (
                            <div
                              className="trace-step trace-complete"
                              key={`${step.key}-${index}`}
                            >
                              <span className="trace-marker">
                                <Check size={14} />
                              </span>

                              <div className="trace-step-copy">
                                <div>
                                  <strong>
                                    {step.label}
                                  </strong>

                                  <span className="trace-status">
                                    {ui.traceComplete}
                                  </span>
                                </div>

                                <p>
                                  {step.summary}
                                </p>

                                <code>
                                  {step.value}
                                </code>
                              </div>
                            </div>
                          ),
                        )
                      ) : (
                        <>
                          {experience.trace.map(
                            (step, index) => (
                              <div
                                className={`trace-step trace-${step.status}`}
                                key={`${step.key}-${index}`}
                              >
                                <span className="trace-marker">
                                  {step.status === "complete"
                                    ? <Check size={14} />
                                    : step.status === "blocked"
                                      ? <X size={14} />
                                      : <CircleAlert size={14} />}
                                </span>

                                <div className="trace-step-copy">
                                  <div>
                                    <strong>
                                      {traceLabel(
                                        step,
                                        language,
                                      )}
                                    </strong>

                                    <span className="trace-status">
                                      {step.status === "complete"
                                        ? ui.traceComplete
                                        : step.status === "blocked"
                                          ? ui.traceBlocked
                                          : ui.traceWarning}
                                    </span>
                                  </div>

                                  <p>
                                    {traceSummary(
                                      step,
                                      language,
                                    )}
                                  </p>

                                  {(step.evidence_ids.length > 0 ||
                                    step.source_ids.length > 0) && (
                                    <details className="technical-details">
                                      <summary>
                                        {ui.technical}
                                      </summary>

                                      {step.evidence_ids.length > 0 && (
                                        <code>
                                          {step.evidence_ids.join(" · ")}
                                        </code>
                                      )}

                                      {step.source_ids.length > 0 && (
                                        <code>
                                          {step.source_ids.join(" · ")}
                                        </code>
                                      )}
                                    </details>
                                  )}
                                </div>
                              </div>
                            ),
                          )}

                          {experience.trace.length === 0 && (
                            <div className="trace-empty">
                              <History size={18} />

                              <span>
                                {language === "ar"
                                  ? "مسار التحقق التفصيلي غير متاح في هذه الاستجابة القديمة."
                                  : "A detailed trace is not available in this legacy response."}
                              </span>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </section>

                <footer className="answer-actions">
                  <div>
                    <button type="button"><Bookmark size={15} />{ui.save}</button>
                    <button type="button"><Share2 size={15} />{ui.share}</button>
                  </div>
                  <div className="feedback-actions">
                    <span>{ui.helpful}</span>
                    <button type="button" aria-label="Helpful"><ThumbsUp size={15} /></button>
                    <button type="button" aria-label="Not helpful"><ThumbsDown size={15} /></button>
                  </div>
                </footer>
              </article>
            </div>
          </section>
        )}

        {!response && (
          <section id="memory" className="memory-section">
            <div className="learning-hero">
              <div>
                <small>
                  {language === "ar"
                    ? "TRUST & LEARNING"
                    : "TRUST & LEARNING"}
                </small>

                <h2>
                  {language === "ar"
                    ? "بصيرة لا تحفظ الأخطاء؛ تتعلم كيف تمنع تكرارها."
                    : "Basira does not memorize mistakes. It learns how to prevent them from happening again."}
                </h2>

                <p>
                  {language === "ar"
                    ? "إذا فشل مسار داخلي بطريقة مؤكدة، لا يتحول الخطأ إلى معلومة دينية جديدة. يتحول إلى قيد أمان، يُختبر أولًا، ثم يُسمح له بتغيير سلوك النظام."
                    : "When an internal path fails in a verified way, the failure does not become new religious knowledge. It becomes a safety constraint, is replay-tested, and only then may change system behavior."}
                </p>
              </div>

              <div className="learning-authority">
                <ShieldCheck size={23} />
                <strong>0</strong>
                <span>
                  {language === "ar"
                    ? "سلطة دينية للذاكرة"
                    : "religious authority"}
                </span>
              </div>
            </div>

            <div className="learning-story">
              <article className="learning-stage learning-stage--before">
                <small>
                  {language === "ar"
                    ? "قبل التعلّم"
                    : "BEFORE"}
                </small>

                <div className="learning-stage__icon">
                  <ShieldAlert size={22} />
                </div>

                <h3>
                  {language === "ar"
                    ? "بصيرة لم تكن واثقة من المسار"
                    : "Basira could not safely verify the request"}
                </h3>

                <p>
                  {language === "ar"
                    ? "المستخدم سأل عن صحة نص قرآني، لكن السؤال دخل مسار بحث عام. ولأن شروط الدليل لم تكتمل، أوقفت الحماية النشر بدل التخمين."
                    : "The user asked whether a Quran quotation was correct, but the request entered a general retrieval path. Because the evidence contract was incomplete, the Trust Shield blocked publication instead of guessing."}
                </p>

                <span className="learning-result is-blocked">
                  {language === "ar"
                    ? "تم إيقاف النشر بأمان"
                    : "Publication safely blocked"}
                </span>
              </article>

              <div className="learning-arrow">
                <span>→</span>
              </div>

              <article className="learning-stage learning-stage--learn">
                <small>
                  {language === "ar"
                    ? "التعلّم المحكوم"
                    : "GOVERNED LEARNING"}
                </small>

                <div className="learning-stage__icon">
                  <RefreshCcw size={22} />
                </div>

                <h3>
                  {language === "ar"
                    ? "الفشل تحوّل إلى قيد أمان"
                    : "The failure became a safety constraint"}
                </h3>

                <div className="learning-checks">
                  <span><Check size={14} /> Failure certificate</span>
                  <span><Check size={14} /> Counterfactual replay</span>
                  <span><Check size={14} /> Regression preserved</span>
                  <span><Check size={14} /> Safe to promote</span>
                </div>

                <p>
                  {language === "ar"
                    ? "لم تتعلم الذاكرة نص الآية. تعلّمت فقط أن هذا النوع من الأسئلة يجب أن يمر بالتحقق النصي."
                    : "Memory did not learn the verse. It learned only that this class of question must enter canonical text verification."}
                </p>
              </article>

              <div className="learning-arrow">
                <span>→</span>
              </div>

              <article className="learning-stage learning-stage--after">
                <small>
                  {language === "ar"
                    ? "بعد التعلّم"
                    : "AFTER"}
                </small>

                <div className="learning-stage__icon">
                  <ShieldCheck size={22} />
                </div>

                <h3>
                  {language === "ar"
                    ? "السؤال يذهب الآن مباشرة للتحقق"
                    : "The request now enters verification"}
                </h3>

                <p>
                  {language === "ar"
                    ? "حتى بصياغة جديدة لم تكن موجودة في الاختبار، تغيّر المسار من بحث عام إلى تحقق قرآني مباشر."
                    : "Even with unseen wording, the route changed from general lookup to canonical Quran verification."}
                </p>

                <span className="learning-result is-verified">
                  quote_verification
                </span>
              </article>
            </div>

            <div className="learning-proof">
              <div className="learning-proof__copy">
                <small>
                  {language === "ar"
                    ? "مثال حقيقي من التشغيل"
                    : "REAL RUNTIME EXAMPLE"}
                </small>

                <h3>
                  {language === "ar"
                    ? "الذاكرة تحدد متى نتحقق. المصدر هو الذي يحدد الحقيقة."
                    : "Memory decides when to verify. The source decides what is true."}
                </h3>

                <p>
                  {language === "ar"
                    ? "بعد تطبيق القيد الجديد، المقارن canonical اكتشف الفرق بنفسه:"
                    : "After the new constraint was promoted, the canonical matcher detected the wording difference itself:"}
                </p>
              </div>

              <div className="learning-proof__words">
                <div className="learning-word is-wrong">
                  <small>
                    {language === "ar"
                      ? "النص الوارد"
                      : "Received"}
                  </small>
                  <strong>يحب</strong>
                </div>

                <span className="learning-proof__arrow">→</span>

                <div className="learning-word is-correct">
                  <small>
                    {language === "ar"
                      ? "النص المعتمد"
                      : "Canonical"}
                  </small>
                  <strong>مع</strong>
                </div>
              </div>
            </div>

            <div className="learning-source">
              <div>
                <BookOpen size={19} />
                <span>
                  {language === "ar"
                    ? "سورة البقرة · الآية 153"
                    : "Al-Baqarah · 2:153"}
                </span>
              </div>

              <p dir="rtl" lang="ar">
                ﴿ يَا أَيُّهَا الَّذِينَ آمَنُوا
                اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ ۚ
                إِنَّ اللَّهَ مَعَ الصَّابِرِينَ ﴾
              </p>

              <small>
                <ShieldCheck size={13} />
                {language === "ar"
                  ? "النص من المصدر القرآني المعتمد، وليس من ذاكرة النظام"
                  : "The Quran text comes from the governed canonical source — not system memory"}
              </small>
            </div>

            <details className="learning-technical">
              <summary>
                {language === "ar"
                  ? "عرض الدليل التقني للتعلّم"
                  : "View technical learning proof"}
              </summary>

              <div className="learning-technical__stats">
                <span><b>5</b> verified failures</span>
                <span><b>5</b> executable replays</span>
                <span><b>5</b> promoted constraints</span>
                <span><b>0</b> religious authority</span>
              </div>

              <p>
                <code>BEFORE: quran_lookup</code>
                <span> → </span>
                <code>AFTER: quote_verification</code>
              </p>
            </details>
          </section>
        )}

        {!response && (
          <section id="about" className="proof-section about-basira">
            <div className="about-basira__copy">
              <small>
                {language === "ar"
                  ? "عن بصيرة"
                  : "ABOUT BASIRA"}
              </small>

              <h2>
                {language === "ar"
                  ? "لسنا نبني محركًا يعطي إجابة فقط؛ نبني نظامًا يعرف متى يحق له أن يجيب."
                  : "We are not building a system that merely answers. We are building one that knows when it is allowed to answer."}
              </h2>

              <p>
                {language === "ar"
                  ? "وُلدت بصيرة من مشكلة بسيطة وخطيرة: وجود مصدر صحيح لا يعني أن الإجابة صحيحة. قد يكون المصدر موثوقًا لكنه عن آية أخرى، أو قد يُستخدم نص القرآن كتفسير، أو قد تتجاوز صياغة الإجابة ما يثبته الدليل. لذلك تتحقق بصيرة من هوية المصدر، والمرجع، والصلة بالادعاء، وكفاية الأدلة، والخلاف، ثم تمر الإجابة عبر بوابة نشر قبل أن تظهر للمستخدم."
                  : "Basira started from a simple but dangerous problem: finding a correct source does not automatically make an answer correct. A trusted source may address the wrong verse, Quran text may be misused as Tafsir, or generated wording may go beyond the evidence. Basira verifies source identity, anchors, claim relevance, evidence sufficiency, disagreement, and publication eligibility before showing an answer."}
              </p>

              <p className="about-basira__principle">
                <ShieldCheck size={17} />

                <span>
                  {language === "ar"
                    ? "بصيرة لا تتعلم المعتقدات؛ بل تتعلم القيود. الأخطاء المؤكدة تتحول إلى اختبارات وقيود أمان قابلة لإعادة التشغيل، ولا تتحول ذاكرة النظام أبدًا إلى دليل ديني."
                    : "Basira does not learn beliefs; it learns constraints. Confirmed system failures become replayable safety constraints, while learned memory never becomes religious evidence."}
                </span>
              </p>
            </div>

            <div className="about-domains">
              <article>
                <span className="about-domain-icon">
                  <BookOpen size={20} />
                </span>

                <div>
                  <small>
                    {language === "ar" ? "مسار فعّال" : "ACTIVE"}
                  </small>

                  <strong>
                    {language === "ar" ? "القرآن" : "Quran"}
                  </strong>

                  <p>
                    {language === "ar"
                      ? "نص قرآني موثق بمرجع canonical وعرض مستقل بشكل المصحف."
                      : "Canonical Quran text with verified anchors and a dedicated Mushaf presentation."}
                  </p>
                </div>
              </article>

              <article>
                <span className="about-domain-icon">
                  <Link2 size={20} />
                </span>

                <div>
                  <small>
                    {language === "ar" ? "مسار فعّال" : "ACTIVE"}
                  </small>

                  <strong>
                    {language === "ar"
                      ? "السنة والحديث"
                      : "Sunnah & Hadith"}
                  </strong>

                  <p>
                    {language === "ar"
                      ? "النص والدرجة والخلاف تظل منسوبة إلى مصادرها."
                      : "Hadith text, grading, and disagreement remain attributed to their sources."}
                  </p>
                </div>
              </article>

              <article>
                <span className="about-domain-icon">
                  <Library size={20} />
                </span>

                <div>
                  <small>
                    {language === "ar" ? "مسار فعّال" : "ACTIVE"}
                  </small>

                  <strong>
                    {language === "ar" ? "التفسير" : "Tafsir"}
                  </strong>

                  <p>
                    {language === "ar"
                      ? "التفسير دليل مستقل، ولا يمكن لنص القرآن أن ينتحل دور التفسير."
                      : "Tafsir remains independent evidence; Quran text cannot impersonate Tafsir support."}
                  </p>
                </div>
              </article>

              <article className="about-domain-beta">
                <span className="about-domain-icon">
                  <Scale size={20} />
                </span>

                <div>
                  <small>
                    {language === "ar"
                      ? "BETA · قيد الضبط"
                      : "BETA · HARDENING"}
                  </small>

                  <strong>
                    {language === "ar" ? "الفقه" : "Fiqh"}
                  </strong>

                  <p>
                    {language === "ar"
                      ? "المسار يعمل حاليًا، مع استمرار ضبط التحقق وإدارة الخلاف قبل اعتباره مسارًا مستقرًا."
                      : "The path is operational while verification and disagreement handling continue to be hardened."}
                  </p>
                </div>
              </article>
            </div>
          </section>
        )}

        {!response && (
          <section id="faq" className="faq-section">
            <div className="faq-heading">
              <small>
                {language === "ar"
                  ? "أسئلة جُرّبت بالفعل"
                  : "PROVEN DEMOS"}
              </small>

              <h2>
                {language === "ar"
                  ? "ما الذي يمكنك أن تسأل عنه؟"
                  : "What can you ask Basira?"}
              </h2>

              <p>
                {language === "ar"
                  ? "هذه ليست أمثلة افتراضية؛ هي أسئلة وسيناريوهات استخدمناها فعليًا أثناء بناء واختبار بصيرة."
                  : "These are not hypothetical prompts. They are questions and scenarios used during Basira’s real verification and regression testing."}
              </p>
            </div>

            <div className="faq-grid">
              {faqScenarios.map((item, index) => (
                <button
                  key={`${item.category.en}-${index}`}
                  type="button"
                  className="faq-question"
                  disabled={isVerifying}
                  onClick={() =>
                    void submitQuestion(
                      item.question[language],
                      "quranReference" in item
                        ? item.quranReference
                        : undefined,
                    )
                  }
                >
                  <span className="faq-domain">
                    {item.category[language]}
                  </span>

                  <strong>
                    {item.question[language]}
                  </strong>

                  <span className="faq-try">
                    {language === "ar"
                      ? "جرّب السؤال"
                      : "Try this question"}
                    <ArrowUpRight size={14} />
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="site-footer">
        <BasiraLogo compact dark={theme === "dark"} />
        <span>{ui.footer}</span>
      </footer>
    </div>
  );
}

export default App;
