import { cn } from "@/lib/utils"

interface ScoreBarProps {
  score: number
  className?: string
  showLabel?: boolean
}

export function ScoreBar({ score, className, showLabel = true }: ScoreBarProps) {
  const percentage = Math.round(score * 100)
  const color =
    score >= 0.7 ? "bg-success" : score >= 0.4 ? "bg-warning" : "bg-destructive"
  const glowColor =
    score >= 0.7
      ? "shadow-glow-success"
      : score >= 0.4
      ? "shadow-[0_0_12px_hsl(38_92%_50%/0.2)]"
      : "shadow-[0_0_12px_hsl(0_72%_51%/0.2)]"

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", color, glowColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono text-muted-foreground w-8 text-right">
          {percentage}
        </span>
      )}
    </div>
  )
}