type IconName = "experiments" | "new" | "connection" | "template" | "provider";

type AppIconProps = {
  name: IconName;
};

export function AppIcon({ name }: AppIconProps) {
  return (
    <svg
      aria-hidden="true"
      className="app-icon"
      fill="none"
      viewBox="0 0 24 24"
    >
      {name === "experiments" && (
        <>
          <rect height="7" rx="2" width="7" x="3" y="3" />
          <rect height="7" rx="2" width="7" x="14" y="3" />
          <rect height="7" rx="2" width="7" x="3" y="14" />
          <rect height="7" rx="2" width="7" x="14" y="14" />
        </>
      )}
      {name === "new" && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v8M8 12h8" />
        </>
      )}
      {name === "connection" && (
        <>
          <path d="M8.5 15.5 6 18a3.5 3.5 0 0 1-5-5l3-3a3.5 3.5 0 0 1 5 0" />
          <path d="m15.5 8.5 2.5-2.5a3.5 3.5 0 0 1 5 5l-3 3a3.5 3.5 0 0 1-5 0" />
          <path d="m8 16 8-8" />
        </>
      )}
      {name === "template" && (
        <>
          <path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
          <circle cx="16" cy="7" r="2" />
          <circle cx="8" cy="17" r="2" />
        </>
      )}
      {name === "provider" && (
        <>
          <path d="M12 2.8c.6 4.1 2.7 6.2 6.8 6.8-4.1.6-6.2 2.7-6.8 6.8-.6-4.1-2.7-6.2-6.8-6.8 4.1-.6 6.2-2.7 6.8-6.8Z" />
          <path d="M18.4 15.7c.25 1.8 1.2 2.75 3 3-1.8.25-2.75 1.2-3 3-.25-1.8-1.2-2.75-3-3 1.8-.25 2.75-1.2 3-3Z" />
        </>
      )}
    </svg>
  );
}
