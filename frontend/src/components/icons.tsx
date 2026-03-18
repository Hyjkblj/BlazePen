import type { ReactElement, SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

const createIcon = (path: ReactElement, viewBox = '0 0 24 24') =>
  function Icon(props: IconProps) {
    return (
      <svg
        viewBox={viewBox}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        {...props}
      >
        {path}
      </svg>
    );
  };

export const ChevronLeftIcon = createIcon(<path d="M15 18l-6-6 6-6" />);
export const ChevronRightIcon = createIcon(<path d="M9 6l6 6-6 6" />);
export const RefreshIcon = createIcon(
  <>
    <path d="M20 11a8 8 0 0 0-14.85-4" />
    <path d="M4 4v5h5" />
    <path d="M4 13a8 8 0 0 0 14.85 4" />
    <path d="M20 20v-5h-5" />
  </>
);
export const CloseIcon = createIcon(<path d="M18 6L6 18M6 6l12 12" />);
export const DocumentIcon = createIcon(
  <>
    <path d="M8 3.5h6l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 7 19V5A1.5 1.5 0 0 1 8.5 3.5Z" />
    <path d="M14 3.5V8h4" />
    <path d="M9.5 12h5" />
    <path d="M9.5 15.5h5" />
  </>
);
export const PlayIcon = createIcon(<path d="M9 7.5v9l7-4.5-7-4.5Z" />);
export const SettingsIcon = createIcon(
  <>
    <path d="M12 8.75a3.25 3.25 0 1 0 0 6.5 3.25 3.25 0 0 0 0-6.5Z" />
    <path d="M4.5 12a7.87 7.87 0 0 1 .14-1.46l-1.89-1.4 1.9-3.3 2.27.57a7.96 7.96 0 0 1 2.52-1.46L9.8 2.5h4.4l.36 2.45a7.96 7.96 0 0 1 2.52 1.46l2.27-.57 1.9 3.3-1.89 1.4c.09.48.14.97.14 1.46s-.05.98-.14 1.46l1.89 1.4-1.9 3.3-2.27-.57a7.96 7.96 0 0 1-2.52 1.46l-.36 2.45H9.8l-.36-2.45a7.96 7.96 0 0 1-2.52-1.46l-2.27.57-1.9-3.3 1.89-1.4A7.87 7.87 0 0 1 4.5 12Z" />
  </>
);
export const LogoutIcon = createIcon(
  <>
    <path d="M10 5.5H7.75A1.75 1.75 0 0 0 6 7.25v9.5c0 .97.78 1.75 1.75 1.75H10" />
    <path d="M14 8l4 4-4 4" />
    <path d="M9 12h9" />
  </>
);
export const MaleIcon = createIcon(
  <>
    <circle cx="10" cy="14" r="4" />
    <path d="M13 11l5-5" />
    <path d="M14.5 6H18v3.5" />
  </>
);
export const FemaleIcon = createIcon(
  <>
    <circle cx="12" cy="9.5" r="4" />
    <path d="M12 13.5V20" />
    <path d="M9 17h6" />
  </>
);
