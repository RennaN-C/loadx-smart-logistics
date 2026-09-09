import type { ReactNode } from "react";

interface AlertBannerProps {
  readonly children: ReactNode;
}

export function AlertBanner({ children }: AlertBannerProps) {
  return (
    <div className="alert-banner" role="alert">
      {children}
    </div>
  );
}
