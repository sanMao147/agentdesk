import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";

type CardProps<T extends ElementType = "div"> = {
  as?: T;
  className?: string;
  children?: ReactNode;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "className" | "children">;

export function Card<T extends ElementType = "div">({
  as,
  className = "",
  children,
  ...rest
}: CardProps<T>) {
  const Tag: ElementType = as ?? "div";
  return (
    <Tag
      className={`bg-surface border border-stroke rounded-m backdrop-blur-md p-4 mb-3.5 shadow-[0_18px_40px_-30px_rgba(0,0,0,0.8),_inset_0_1px_0_rgba(255,255,255,0.05)] transition duration-200 ease-out hover:-translate-y-0.5 hover:border-stroke-2 hover:shadow-[0_26px_60px_-34px_rgba(16,185,129,0.35),_inset_0_1px_0_rgba(255,255,255,0.07)] ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}

type CardHeaderProps = ComponentPropsWithoutRef<"div">;

export function CardHeader({ className, children, ...rest }: CardHeaderProps) {
  return (
    <div className={className} {...rest}>
      {children}
    </div>
  );
}

type CardBodyProps = ComponentPropsWithoutRef<"div">;

export function CardBody({ className = "", children, ...rest }: CardBodyProps) {
  return (
    <div className={`mt-2 ${className}`} {...rest}>
      {children}
    </div>
  );
}
