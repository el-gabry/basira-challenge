import { BookOpen, FlaskConical, Library, ScrollText, Scale
} from "lucide-react";
import {
  domainQaScenarios,
  type DomainQaScenario,
  type QaLanguage,
} from "../qa/domainScenarios";

type Props = {
  language: QaLanguage;
  disabled?: boolean;
  onRun: (scenario: DomainQaScenario) => void;
};

const iconByDomain = {
  quran: BookOpen,
  fiqh: Scale,
  tafsir: Library,
  hadith: ScrollText,
} as const;

export function DomainQaPanel({ language, disabled = false, onRun }: Props) {
  return (
    <section className="domain-qa-panel" aria-label={language === "ar" ? "اختبار المجالات" : "Domain UI QA"}>
      <div className="domain-qa-heading">
        <span className="domain-qa-icon"><FlaskConical size={17} /></span>
        <div>
          <small>UI QA · REAL API</small>
          <strong>{language === "ar" ? "جرّب المجالات الثلاثة على الواجهة الجديدة" : "Try the three live domains on the new UI"}</strong>
          <p>
            {language === "ar"
              ? "كل زر يرسل السؤال الحقيقي إلى /api/v1/query ثم يعرض نفس استجابة الـ backend في واجهة النتيجة الجديدة. لا توجد mock data هنا."
              : "Each button sends a real request to /api/v1/query and renders the backend response in the new result UI. No mock data is used."}
          </p>
        </div>
      </div>

      <div className="domain-qa-grid">
        {domainQaScenarios.map((scenario) => {
          const Icon = iconByDomain[scenario.id];
          return (
            <article className={`domain-qa-card domain-qa-${scenario.id}`} key={scenario.id}>
              <div className="domain-qa-card-top">
                <span className="domain-qa-card-icon"><Icon size={19} /></span>
                <strong>{scenario.domainLabel[language]}</strong>
              </div>
              <p>{scenario.description[language]}</p>
              <code dir={language === "ar" ? "rtl" : "ltr"}>{scenario.question[language]}</code>
              <small>{scenario.expectation[language]}</small>
              <button type="button" disabled={disabled} onClick={() => onRun(scenario)}>
                {language === "ar" ? "جرّب على الواجهة" : "Run in new UI"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
