import type { ComponentPropsWithoutRef, ReactNode } from "react";

type PillVariant = "default" | "tool" | "bad";

type PillProps = Omit<ComponentPropsWithoutRef<"span">, "color" | "children"> & {
  children: ReactNode;
  variant?: PillVariant;
  color?: string;
};

const variantClasses: Record<PillVariant, string> = {
  default: "bg-brand/15 text-[#a7f3d0]",
  tool: "bg-ok/15 text-[#a7f3d0]",
  bad: "bg-bad/15 text-[#fecaca]",
};

export function Pill({
  children,
  variant = "default",
  color,
  className = "",
  style: styleProp,
  ...rest
}: PillProps) {
  const variantClass = color ? "" : variantClasses[variant];
  const colorStyle = color
    ? { backgroundColor: `${color}22`, color }
    : undefined;
  const style = styleProp ? { ...colorStyle, ...styleProp } : colorStyle;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-[11px] py-[5px] rounded-full text-[0.74rem] font-semibold mr-1.5 mb-1.5 border border-stroke-2 font-mono ${variantClass} ${className}`}
      style={style}
      {...rest}
    >
      {children}
    </span>
  );
}
