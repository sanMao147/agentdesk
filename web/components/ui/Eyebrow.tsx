import type { ComponentPropsWithoutRef, ReactNode } from "react";

type EyebrowProps = Omit<ComponentPropsWithoutRef<"div">, "children"> & {
  children: ReactNode;
};

export function Eyebrow({ children, className = "", ...rest }: EyebrowProps) {
  return (
    <div
      className={`flex items-center gap-2 my-1.5 mb-3 text-[0.74rem] font-bold tracking-[0.16em] uppercase text-faint ${className}`}
      {...rest}
    >
      <span className="inline-block w-[18px] h-0.5 rounded-sm bg-grad" />
      {children}
    </div>
  );
}
