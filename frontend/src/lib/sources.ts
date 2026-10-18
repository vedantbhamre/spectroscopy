// The AFS source documents behind every citation. The backend and the jury use the IDs (S01–S06);
// people reading a report see the document's name.
export const SOURCES: Record<string, { short: string; title: string }> = {
  S01: { short: "Multispectral Lab guide", title: "AFS Multispectral Laboratory of Optical Analysis Methods" },
  S02: { short: "Process Control slides", title: "AFS Process Control slides" },
  S03: { short: "Kidney tissue study", title: "LED-based kidney tissue study (2017)" },
  S04: { short: "MIR + fluorescence study", title: "Combined MIR and fluorescence study (2021)" },
  S05: { short: "AFS flyer", title: "Art Fiber Systems flyer" },
  S06: { short: "AFS lab website", title: "AFS laboratory web page" },
  EXT: { short: "External source", title: "External source" },
};

export const sourceShort = (id: string) => SOURCES[id]?.short ?? id;
export const sourceTitle = (id: string) => SOURCES[id]?.title ?? id;

// "S01 p.12, S02 p.10" in trace text → "Multispectral Lab guide p.12, Process Control slides p.10".
export const readableSources = (text: string) => text.replace(/\bS0([1-6])\b/g, (id) => sourceShort(id));
