import type { ComponentPropsWithoutRef, ReactNode } from "react";

type ExpanderProps = Omit<
  ComponentPropsWithoutRef<"details">,
  "open" | "children" | "summary"
> & {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
};

export function Expander({
  summary,
  children,
  defaultOpen = false,
  className = "",
  ...rest
}: ExpanderProps) {
  return (
    <details
      open={defaultOpen}
      className={`border border-stroke rounded-m bg-surface overflow-hidden mb-3.5 ${className}`}
      {...rest}
    >
      <summary className="cursor-pointer text-[#cdd5f5] font-semibold px-4 py-3 list-none [&::-webkit-details-marker]:hidden flex items-center gap-2">
        <span className="transition-transform inline-block [details[open]_&]:rotate-90">
          ▶
        </span>
        {summary}
      </summary>
      <div className="px-4 pb-4 pt-1">{children}</div>
    </details>
  );
}
