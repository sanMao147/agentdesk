"use client";

import { useEffect, useState } from "react";
import type { Config } from "@/lib/api";
import { CHAT_MODEL_PRESETS, DEMOS } from "@/lib/constants";
import { Eyebrow } from "@/components/ui/Eyebrow";

export interface AskBarProps {
  config: Config;
  initialQuery: string;
  onQueryChange: (v: string) => void;
  onRun: (q: string) => void;
  onModelChange: (model: string) => void;
}

const SELECT_CLASSES =
  "bg-surface-2 text-ink border border-stroke-2 rounded-xl py-2 px-4 text-[0.95rem] placeholder:text-faint focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/25 w-full";

const INPUT_CLASSES =
  "bg-surface-2 text-ink border border-stroke-2 rounded-xl h-[52px] px-4 text-[0.95rem] placeholder:text-faint focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/25 w-full";

export function AskBar({
  config,
  initialQuery,
  onQueryChange,
  onRun,
  onModelChange,
}: AskBarProps) {
  const live = config.use_llm;
  const [selectValue, setSelectValue] = useState(config.chat_model);
  const [customInput, setCustomInput] = useState(
    CHAT_MODEL_PRESETS.includes(config.chat_model) ? "" : config.chat_model,
  );

  useEffect(() => {
    setSelectValue(config.chat_model);
    setCustomInput(
      CHAT_MODEL_PRESETS.includes(config.chat_model) ? "" : config.chat_model,
    );
  }, [config.chat_model]);

  const handleSelectChange = (v: string) => {
    setSelectValue(v);
    if (v !== "自定义…") {
      onModelChange(v);
    }
  };

  const handleCustomSubmit = () => {
    const v = customInput.trim();
    if (v) {
      onModelChange(v);
    }
  };

  const isCustom = selectValue === "自定义…";
  const options = CHAT_MODEL_PRESETS.includes(config.chat_model)
    ? CHAT_MODEL_PRESETS
    : [config.chat_model, ...CHAT_MODEL_PRESETS];

  return (
    <div>
      <Eyebrow>Ask the knowledge base</Eyebrow>

      <div className="grid grid-cols-[1fr_2fr_2fr] gap-3 items-center">
        <div className="pt-2.5 text-muted font-semibold text-[0.9rem]">
          🧠 Chat 模型
        </div>
        <select
          value={selectValue}
          onChange={(e) => handleSelectChange(e.target.value)}
          disabled={!live}
          className={SELECT_CLASSES}
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        {isCustom ? (
          <input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            onBlur={handleCustomSubmit}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleCustomSubmit();
              }
            }}
            placeholder="如 Qwen/Qwen2.5-72B-Instruct"
            disabled={!live}
            className={SELECT_CLASSES}
          />
        ) : (
          <div className="pt-[11px] text-faint text-[0.74rem]">
            {live
              ? "影响 改写/生成/裁判三处 · 7B 易把数字写崩，建议 32B+"
              : "离线 fallback 不调用大模型，切换无效（需在 .env 配 key）"}
          </div>
        )}
      </div>

      <div className="text-faint text-[0.75rem] my-2">示例 · 点击即问</div>
      <div className="grid grid-cols-5 gap-2">
        {DEMOS.map(([label, query]) => (
          <button
            key={label}
            type="button"
            onClick={() => onRun(query)}
            className="rounded-xl border border-stroke-2 bg-surface-2 text-[#dfe4ff] font-medium py-2 px-3 text-xs hover:border-brand hover:text-white hover:bg-brand/16 transition text-center"
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-[4fr_1fr] gap-3 mt-3">
        <input
          type="text"
          value={initialQuery}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onRun(initialQuery);
            }
          }}
          placeholder="例如：公司A和公司B 2025年营收分别是多少？"
          className={INPUT_CLASSES}
        />
        <button
          type="button"
          onClick={() => onRun(initialQuery)}
          className="rounded-xl border-0 text-white h-[50px] font-bold tracking-wide shadow-[0_14px_34px_-14px_rgba(124,92,255,0.85)] bg-grad hover:brightness-110 hover:-translate-y-0.5 transition"
        >
          ⚡ 运行
        </button>
      </div>
    </div>
  );
}
