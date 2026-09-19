import { Briefcase, FileCheck, FilePen, type LucideIcon, Phone, SearchCheck, Truck } from "lucide-react";

export type StepIcon = "request" | "call" | "match" | "documents" | "work" | "truck";

const ICONS: Record<StepIcon, LucideIcon> = {
  request: FilePen,
  call: Phone,
  match: SearchCheck,
  documents: FileCheck,
  work: Briefcase,
  truck: Truck,
};

export type Step = { icon: StepIcon; title: string; text: string };

/** "How it works" timeline: icons on a dashed line, the first step highlighted. */
export function Steps({ steps, dark = false }: { steps: Step[]; dark?: boolean }) {
  return (
    <ol className={dark ? "steps steps--dark" : "steps"}>
      {steps.map(({ icon, title, text }, i) => {
        const Icon = ICONS[icon];
        return (
          <li key={title} className={i === 0 ? "step step--active" : "step"}>
            <span className="step-icon" aria-hidden>
              <Icon size={18} />
            </span>
            <strong>{title}</strong>
            <span>{text}</span>
          </li>
        );
      })}
    </ol>
  );
}
