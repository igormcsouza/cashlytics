import { formatMonthLabel, shiftMonth } from "@/lib/month";

interface Props {
  month: string; // YYYY-MM
  onPrev: () => void;
  onNext: () => void;
}

// Month navigation below the expense table (issue #10): arrows on either
// side of the current month's name. On desktop the faded previous/next month
// names are also shown so the user understands the arrows page through
// months; on mobile there isn't room for that, so they're hidden.
export default function MonthNav({ month, onPrev, onNext }: Props) {
  const prevLabel = formatMonthLabel(shiftMonth(month, -1));
  const label = formatMonthLabel(month);
  const nextLabel = formatMonthLabel(shiftMonth(month, 1));

  return (
    <div className="flex items-center justify-center gap-3 sm:gap-6 mt-4 select-none">
      <button
        type="button"
        onClick={onPrev}
        aria-label="Previous month"
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 text-lg"
      >
        ←
      </button>

      <span
        aria-hidden="true"
        className="hidden sm:inline text-sm text-slate-600 whitespace-nowrap"
      >
        {prevLabel}
      </span>

      <span className="text-lg font-semibold text-slate-100 whitespace-nowrap">
        {label}
      </span>

      <span
        aria-hidden="true"
        className="hidden sm:inline text-sm text-slate-600 whitespace-nowrap"
      >
        {nextLabel}
      </span>

      <button
        type="button"
        onClick={onNext}
        aria-label="Next month"
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 text-lg"
      >
        →
      </button>
    </div>
  );
}
