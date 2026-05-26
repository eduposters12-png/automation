"use client";

import type { InputHTMLAttributes } from "react";
import { forwardRef } from "react";

import { cn } from "@/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const inputId = id || props.name;
    return (
      <label className="block" htmlFor={inputId}>
        <span className="mb-2 block text-sm font-medium text-gray-800">{label}</span>
        <input
          id={inputId}
          ref={ref}
          className={cn(
            "h-11 w-full rounded-md border border-gray-200 bg-white px-3 text-sm text-gray-950 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-indigo-500",
            error && "border-red-300 focus:border-red-500 focus:ring-red-100",
            className
          )}
          {...props}
        />
        {error ? <span className="mt-1 block text-xs font-medium text-red-600">{error}</span> : null}
      </label>
    );
  }
);

Input.displayName = "Input";
