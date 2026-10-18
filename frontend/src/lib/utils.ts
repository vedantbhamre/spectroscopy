import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Merges class names; later Tailwind utilities win over earlier ones (shadcn / motion-primitives helper).
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
