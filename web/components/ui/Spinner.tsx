import type { ComponentPropsWithoutRef } from "react";

type SpinnerProps = ComponentPropsWithoutRef<"div"> & {
  label?: string;
};

export function Spinner({
  label = "加载中…",
  className = "",
  ...rest
}: SpinnerProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`} {...rest}>
      <div className="w-5 h-5 rounded-full border-2 border-stroke-2 border-t-brand animate-spin" />
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}
