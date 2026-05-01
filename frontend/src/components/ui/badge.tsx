import { cn } from "@/lib/utils"

interface BadgeProps {
  children: React.ReactNode
  variant?: "default" | "success" | "warning" | "destructive" | "outline"
  className?: string
}

const variantClasses = {
  default: "bg-primary/15 text-primary border-primary/20",
  success: "bg-success/15 text-success border-success/20",
  warning: "bg-warning/15 text-warning border-warning/20",
  destructive: "bg-destructive/15 text-destructive border-destructive/20",
  outline: "bg-transparent text-muted-foreground border-border",
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  )
}