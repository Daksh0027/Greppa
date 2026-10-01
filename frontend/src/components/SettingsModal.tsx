"use client";

import React, { useState, useEffect } from "react";
import { Key, CheckCircle, ShieldAlert, X } from "lucide-react";
import { getStoredApiKey, setStoredApiKey, fetchHealth } from "@/lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState(false);
  const [healthStatus, setHealthStatus] = useState<any>(null);

  useEffect(() => {
    if (isOpen) {
      setApiKey(getStoredApiKey());
      fetchHealth().then(setHealthStatus).catch(() => setHealthStatus(null));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    setStoredApiKey(apiKey.trim());
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-zinc-700 w-full max-w-md rounded-xl p-6 shadow-2xl relative text-zinc-100">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-200"
        >
          <X size={18} />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg">
            <Key size={22} />
          </div>
          <div>
            <h2 className="text-lg font-bold">LLM Provider Settings</h2>
            <p className="text-xs text-zinc-400">Agent-driven dynamic API key configuration</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
              Google Gemini API Key
            </label>
            <input
              type="password"
              placeholder="AIzaSy..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
            <p className="text-xs text-zinc-400 mt-1">
              Keys are passed per-request. If left blank, local heuristic summarization and pseudo-embeddings will be used for offline testing.
            </p>
          </div>

          <div className="p-3 bg-zinc-800/80 rounded-lg border border-zinc-700/60 text-xs space-y-1.5">
            <div className="flex justify-between items-center text-zinc-300">
              <span>Backend Status:</span>
              <span className={healthStatus?.status === "healthy" ? "text-emerald-400 font-semibold" : "text-amber-400"}>
                {healthStatus?.status === "healthy" ? "Connected (Healthy)" : "Offline / Connecting..."}
              </span>
            </div>
            <div className="flex justify-between items-center text-zinc-300">
              <span>Default Summarizer:</span>
              <span className="font-mono text-blue-400">gemini-2.0-flash</span>
            </div>
            <div className="flex justify-between items-center text-zinc-300">
              <span>Agent Synthesis:</span>
              <span className="font-mono text-purple-400">gemini-2.0-pro</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-300 hover:bg-zinc-800 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1.5 transition"
            >
              {saved ? <CheckCircle size={14} /> : null}
              {saved ? "Saved" : "Save API Key"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
