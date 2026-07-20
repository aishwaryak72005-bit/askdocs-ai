import React from "react";

/**
 * FormattedMarkdown renders markdown-like text nicely formatted
 * (bold text, bullets, paragraphs) without needing extra heavy dependencies.
 */
export default function FormattedMarkdown({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const blocks = [];
  let currentList = [];

  const flushList = () => {
    if (currentList.length > 0) {
      blocks.push({ type: "list", items: [...currentList] });
      currentList = [];
    }
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }

    if (trimmed.startsWith("* ") || trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
      const itemText = trimmed.replace(/^[\*\-\•]\s*/, "");
      currentList.push(itemText);
    } else {
      flushList();
      if (trimmed.startsWith("### ")) {
        blocks.push({ type: "h3", text: trimmed.replace(/^###\s*/, "") });
      } else if (trimmed.startsWith("## ")) {
        blocks.push({ type: "h2", text: trimmed.replace(/^##\s*/, "") });
      } else if (trimmed.startsWith("# ")) {
        blocks.push({ type: "h1", text: trimmed.replace(/^#\s*/, "") });
      } else {
        blocks.push({ type: "p", text: trimmed });
      }
    }
  });
  flushList();

  const parseInline = (text) => {
    // Replace **bold** with <strong>
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="formatted-text">
      {blocks.map((block, idx) => {
        if (block.type === "list") {
          return (
            <ul key={idx} className="formatted-list">
              {block.items.map((item, itemIdx) => (
                <li key={itemIdx}>{parseInline(item)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "h1") return <h3 key={idx}>{parseInline(block.text)}</h3>;
        if (block.type === "h2") return <h4 key={idx}>{parseInline(block.text)}</h4>;
        if (block.type === "h3") return <h5 key={idx}>{parseInline(block.text)}</h5>;
        return <p key={idx}>{parseInline(block.text)}</p>;
      })}
    </div>
  );
}
