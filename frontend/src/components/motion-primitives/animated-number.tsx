'use client';
// From motion-primitives (MIT, github.com/ibelick/motion-primitives @ 120f64f), adapted for React 19 and the SpectraSense tokens.
import { cn } from '@/lib/utils';
import { motion, SpringOptions, useSpring, useTransform } from 'motion/react';
import { useEffect } from 'react';

export type AnimatedNumberProps = {
  value: number;
  className?: string;
  springOptions?: SpringOptions;
  decimals?: number;
};

export function AnimatedNumber({
  value,
  className,
  springOptions,
  decimals = 0,
}: AnimatedNumberProps) {
  const spring = useSpring(value, springOptions);
  const display = useTransform(spring, (current) => current.toFixed(decimals));

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return (
    <motion.span className={cn('tabular-nums', className)}>
      {display}
    </motion.span>
  );
}
