import { cn } from "@/lib/utils"

interface StatusDotProps {
  status: "running" | "idle" | "error" | "paused" | string
  className?: string
  pulse?: boolean
}

const statusColors: Record<string, string> = {
  running: "bg-success",
  idle: "bg-muted-foreground",
  error: "bg-destructive",
  paused: "bg-warning",
}

export function StatusDot({ status, className, pulse }: StatusDotProps) {
  const color = statusColors[status] || "bg-muted-foreground"
  const shouldPulse = pulse ?? status === "running"

  return (
    <span className={cn("relative flex h-2.5 w-2.5", className)}>
      {shouldPulse && (
        <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", color)} />
      )}
      <span className={cn("relative inline-flex rounded-full h-2.5 w-2.5", color)} />
    </span>
  )
}