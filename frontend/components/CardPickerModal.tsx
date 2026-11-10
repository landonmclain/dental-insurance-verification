"use client";

import { useEffect, useState } from "react";

type CardInfo = {
  id: string;
  payer: string | null;
  image_url: string;
};

type Props = {
  onSelect: (card: CardInfo) => void;
  onClose: () => void;
};

export function CardPickerModal({ onSelect, onClose }: Props) {
  const [cards, setCards] = useState<CardInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/cards")
      .then((r) => r.json())
      .then((data) => setCards(data))
      .catch(() => setCards([]))
      .finally(() => setLoading(false));
  }, []);

  function pick(card: CardInfo) {
    onSelect(card);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl dark:bg-neutral-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">Choose a sample card</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:text-neutral-500 dark:hover:text-neutral-300"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-slate-500 dark:text-neutral-400">Loading cards…</p>
        ) : cards.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-neutral-400">No generated cards found.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {cards.map((card) => (
              <button
                type="button"
                key={card.id}
                onClick={() => pick(card)}
                className="group overflow-hidden rounded-lg border border-slate-200 text-left hover:border-blue-400 dark:border-neutral-700 dark:hover:border-blue-500"
              >
                <img
                  src={`/api${card.image_url}`}
                  alt={card.payer ?? card.id}
                  className="h-28 w-full object-cover"
                />
                <div className="px-2 py-1 text-xs text-slate-600 dark:text-neutral-300">
                  {card.payer ?? card.id}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
