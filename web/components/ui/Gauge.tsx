import type { ComponentPropsWithoutRef } from "react";

type GaugeProps = Omit<ComponentPropsWithoutRef<"div">, "color" | "style"> & {
  pct: number;
  color: string;
};

export function Gauge({ pct, color, className = "", ...rest }: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div
      className={`relative w-[92px] h-[92px] rounded-full grid place-items-center ${className}`}
      style={{
        background: `conic-gradient(${color} ${clamped}%, rgba(255,255,255,0.08) 0)`,
        boxShadow: "inset 0 0 0 1px var(--stroke)",
      }}
      {...rest}
    >
      <div
        className="absolute inset-[9px] rounded-full shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
        style={{ background: "#0c1122" }}
      />
      <b className="relative text-[1.25rem] font-extrabold tabular-nums">
        {clamped}%
      </b>
    </div>
  );
}
