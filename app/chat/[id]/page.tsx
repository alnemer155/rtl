"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ChatView } from "@/components/chat/chat-view";
import { api, type ConversationMessage } from "@/lib/api";

export default function ChatPage() {
  const params = useParams<{ id: string }>();
  const [messages, setMessages] = useState<ConversationMessage[] | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    api
      .conversation(params.id)
      .then((detail) => {
        setMessages(detail.messages);
        setTitle(detail.title);
      })
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "تعذر تحميل المحادثة"),
      );
  }, [params?.id]);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-5 pt-16">
        <p className="text-[14px] text-[var(--muted)]">{error}</p>
      </main>
    );
  }
  if (messages === null) {
    return (
      <main className="mx-auto max-w-3xl px-5 pt-16">
        <p className="quiet-dot text-[13px] text-[var(--muted-foreground)]">…</p>
      </main>
    );
  }
  return (
    <ChatView
      initialMessages={messages}
      initialConversationId={params.id}
      initialTitle={title}
    />
  );
}
