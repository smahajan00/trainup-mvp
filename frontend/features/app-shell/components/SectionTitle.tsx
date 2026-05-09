type SectionTitleProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
};

export function SectionTitle({
  eyebrow,
  title,
  description,
  action
}: SectionTitleProps) {
  return (
    <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 overflow-hidden">
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="mt-2 break-words font-display text-3xl font-bold leading-tight tracking-tight text-white md:text-4xl">
          {title}
        </h2>
        {description ? (
          <p className="mt-2 line-clamp-2 max-w-xl break-words text-sm leading-relaxed text-neutral-300 md:text-base">
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
