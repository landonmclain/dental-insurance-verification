"use client";

import { useState } from "react";
import { CardPickerModal } from "./CardPickerModal";

type CardInfo = {
  id: string;
  payer: string | null;
  image_url: string;
};

type Props = {
  onSubmit: (cardId: string) => void;
  disabled: boolean;
};

export function VerificationForm({ onSubmit, disabled }: Props) {
  const [card, setCard] = useState<CardInfo | null>(null);
  const [showPicker, setShowPicker] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (card) onSubmit(card.id);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-xl border bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h2 className="text-lg font-semibold">Insurance card</h2>

      <button
        type="button"
        onClick={() => setShowPicker(true)}
        className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 dark:border-neutral-600 dark:hover:bg-neutral-800"
      >
        {card ? "Change card" : "Choose a sample card"}
      </button>

      {showPicker && (
        <CardPickerModal
          onSelect={(picked) => {
            setCard(picked);
            setShowPicker(false);
          }}
          onClose={() => setShowPicker(false)}
        />
      )}

      {card && (
        <div className="space-y-2">
          <span className="text-sm font-medium text-slate-600 dark:text-neutral-300">
            Selected card
          </span>
          <img
            src={`/api${card.image_url}`}
            alt={card.payer ?? card.id}
            className="w-full rounded-lg border border-slate-200 object-cover dark:border-neutral-700"
          />
        </div>
      )}

      <button
        type="submit"
        disabled={disabled || !card}
        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {disabled ? "Verifying…" : "Send for verification"}
      </button>
    </form>
  );
}
