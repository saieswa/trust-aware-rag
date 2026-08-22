"use client";

import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface ChatInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSubmit, disabled, placeholder }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-hairline bg-panel p-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            handleSubmit(e);
          }
        }}
        placeholder={placeholder || "Ask a question backed by your indexed documents…"}
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none rounded-md border border-hairline bg-raised px-3 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor disabled:opacity-60"
      />
      <Button type="submit" disabled={disabled || !value.trim()} aria-label="Send question">
        <Send className="h-4 w-4" />
      </Button>
    </form>
  );
}
