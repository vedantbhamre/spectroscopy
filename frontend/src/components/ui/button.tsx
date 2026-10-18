import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

// shadcn Button, styled as Carbon buttons (see DESIGN.md): square, 14px label, one accent colour.
// primary = default, secondary = charcoal, tertiary = outline, ghost and link for low emphasis.
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-3 rounded-none text-sm font-normal whitespace-nowrap transition-colors disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-accent text-white hover:bg-accent-dim disabled:bg-line disabled:text-ink-3",
        secondary: "bg-ink text-bg hover:bg-ink-2 disabled:bg-line disabled:text-ink-3",
        outline: "border border-accent bg-transparent text-accent hover:bg-panel disabled:border-line disabled:text-ink-3",
        ghost: "text-accent hover:bg-panel disabled:text-ink-3",
        destructive: "bg-bad text-white hover:opacity-90 disabled:bg-line disabled:text-ink-3",
        link: "px-0 text-accent underline-offset-4 hover:underline disabled:text-ink-3",
        inverse: "bg-white text-accent hover:bg-panel",
        "outline-inverse": "border border-hero-ink bg-transparent text-hero-ink hover:bg-hero-line",
      },
      size: {
        default: "h-10 px-4",
        xs: "h-6 gap-1 px-2 text-xs [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-2 px-3",
        lg: "h-12 gap-6 px-4",
        icon: "size-10",
        "icon-xs": "size-6 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
