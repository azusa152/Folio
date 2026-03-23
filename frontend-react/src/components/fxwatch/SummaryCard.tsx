interface SummaryCardProps {
  label: string
  value: string
  highlight?: boolean
  small?: boolean
}

export function SummaryCard({ label, value, highlight = false, small = false }: SummaryCardProps) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={`${small ? "text-sm font-semibold truncate" : "text-2xl font-bold"} ${
          highlight ? "text-destructive" : ""
        }`}
      >
        {value}
      </p>
    </div>
  )
}
