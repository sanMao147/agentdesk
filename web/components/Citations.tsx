import { Eyebrow } from "@/components/ui/Eyebrow";
import { Pill } from "@/components/ui/Pill";

export interface CitationsProps {
  citations: string[];
}

export function Citations({ citations }: CitationsProps) {
  if (!citations.length) return null;
  return (
    <div>
      <Eyebrow>Citations</Eyebrow>
      <div className="flex flex-wrap">
        {citations.map((c, i) => (
          <Pill key={i}>🔖 {c}</Pill>
        ))}
      </div>
    </div>
  );
}
