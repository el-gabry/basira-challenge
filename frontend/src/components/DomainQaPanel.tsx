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
          <small>TRUST SHIELD · LIVE</small>
          <strong>{language === "ar" ? "أقسام التحقق" : "Verification sections"}</strong>
        </div>
      </div>

      <div className="domain-qa-grid">
        {domainQaScenarios
          .filter((scenario) => language === "ar" || scenario.id !== "fiqh")
          .map((scenario) => {
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
                {language === "ar" ? "تحقق" : "Verify"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
