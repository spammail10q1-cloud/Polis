"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowUp,
  ChevronDown,
  ExternalLink,
  LoaderCircle,
  LockKeyhole,
  MessageSquareText,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { useQuery } from "@/lib/use-query";
import { useToast } from "@/components/toast";
import { apiPatch, apiPost, errorMessage } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import type { AnswerBlock, AssistantAnswer, AssistantStatus, Overview } from "@/lib/types";
import { cn } from "@/lib/format";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  answer?: AssistantAnswer;
};

const suggestedPrompts = [
  "Why is my ALT higher than last time?",
  "Which genetic variants affect medication metabolism?",
  "What information is missing from my health profile?",
  "Compare my latest blood results with the previous test.",
  "What should I ask my doctor about these results?",
  "Explain how my body processes metoprolol.",
  "Which biological pathways connect my measurements?",
  "What if I take clopidogrel?",
];

export default function AssistantPage() {
  const { consent, refresh: refreshAuth } = useAuth();
  const { push } = useToast();
  const status = useQuery<AssistantStatus>("/assistant/status");
  const overview = useQuery<Overview>("/overview");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enabling, setEnabling] = useState(false);
  const threadRef = useRef<HTMLDivElement | null>(null);

  const latestAnswer = [...messages].reverse().find((message) => message.role === "assistant")?.answer;
  const consentOn = status.data?.ai_processing_consent ?? consent?.ai_processing ?? false;

  useEffect(() => {
    const element = threadRef.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending) return;
    if (!consentOn) {
      setError("Enable AI processing consent before using POLIS AI.");
      return;
    }
    setError(null);
    setSending(true);
    const userMessage: ChatMessage = { id: `user-${Date.now()}`, role: "user", content: message };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    const history = messages.slice(-8).map((item) => ({ role: item.role, content: item.answer?.answer ?? item.content }));
    try {
      const answer = await apiPost<AssistantAnswer>("/assistant/chat", { message, history });
      setMessages((current) => [
        ...current,
        { id: `assistant-${Date.now()}`, role: "assistant", content: answer.answer, answer },
      ]);
    } catch (err) {
      const text = errorMessage(err);
      setError(text);
      push(text, "error");
    } finally {
      setSending(false);
    }
  };

  const enableConsent = async () => {
    setEnabling(true);
    try {
      await apiPatch("/privacy/consent", { ai_processing: true });
      await status.refresh();
      await refreshAuth();
      push("AI processing consent enabled.", "success");
    } catch (err) {
      push(errorMessage(err), "error");
    } finally {
      setEnabling(false);
    }
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(input);
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Research correspondence"
        title="POLIS AI"
        description="A research assistant that explains your recorded data and retrieved evidence. It shows its sources, limitations and missing information, and refuses when the evidence is insufficient."
        actions={
          <>
            <Badge tone={status.data?.external_llm_configured ? "violet" : "neutral"}>
              {status.data?.external_llm_configured ? "External model configured" : "Local deterministic engine"}
            </Badge>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                onClick={() => {
                  setMessages([]);
                  setError(null);
                }}
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> New thread
              </Button>
            )}
          </>
        }
      />

      {!consentOn ? (
        <ConsentRequired onEnable={enableConsent} loading={enabling} />
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.62fr)]">
          <Panel className="flex min-h-[620px] flex-col overflow-hidden" emphasis>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
              <div className="flex items-center gap-2.5">
                <span className="text-[12px] text-mist">Research thread</span>
                <span className="font-mono text-[11px] text-dim">
                  {messages.length} {messages.length === 1 ? "message" : "messages"}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-dim">
                <ShieldCheck className="h-3.5 w-3.5 text-mint" aria-hidden="true" />
                <span>{status.data?.retrieval ?? "Local evidence"}</span>
              </div>
            </div>

            <div ref={threadRef} className="scroll-area flex-1 overflow-y-auto px-4 py-5 sm:px-6">
              {!messages.length ? (
                <AssistantEmpty onPrompt={send} overview={overview.data} />
              ) : (
                <div className="space-y-7">
                  {messages.map((message) =>
                    message.role === "user" ? (
                      <UserEntry key={message.id} text={message.content} />
                    ) : (
                      <AssistantEntry key={message.id} answer={message.answer!} onFollowUp={send} />
                    ),
                  )}
                  {sending && <Thinking />}
                </div>
              )}
            </div>

            <div className="border-t border-line bg-ink p-3 sm:p-4">
              {error && (
                <div className="mb-2 flex items-start gap-2 border border-danger/30 bg-danger/[0.05] px-3 py-2 text-[12px] leading-relaxed text-danger">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {error}
                </div>
              )}
              <div className="relative">
                <label htmlFor="assistant-question" className="mb-1.5 block text-[12px] text-dim">
                  Your question
                </label>
                <textarea
                  id="assistant-question"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Ask about your labs, genetics, medications or missing information"
                  className="input min-h-[92px] resize-none pb-10 pr-16"
                  maxLength={4000}
                  disabled={sending}
                />
                <div className="absolute bottom-2.5 left-3 flex items-center gap-1.5 text-[11px] text-dim">
                  <LockKeyhole className="h-3 w-3" aria-hidden="true" /> Grounded in your records
                </div>
                <button
                  onClick={() => send(input)}
                  disabled={!input.trim() || sending}
                  aria-label="Send message"
                  className="btn btn-primary absolute bottom-2 right-2 h-11 w-11 p-0"
                >
                  {sending ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <ArrowUp className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              </div>
              <p className="mt-2.5 text-[12px] leading-relaxed text-dim">
                POLIS AI is not a clinician. It does not diagnose, prescribe or change medicines. For urgent symptoms,
                contact local emergency services. Demonstration data are synthetic.
              </p>
            </div>
          </Panel>

          <div className="space-y-4 xl:sticky xl:top-[74px] xl:self-start">
            <Panel>
              <PanelHeader eyebrow="Grounding" title="What the answer can use" />
              <div className="space-y-3 p-4">
                <GroundingRow label="Latest lab signals" value={String(overview.data?.latest_labs.length ?? 0)} />
                <GroundingRow label="Pharmacogenes" value="Curated synthetic panel" />
                <GroundingRow label="Active medications" value={String(overview.data?.active_medications.length ?? 0)} />
                <GroundingRow label="Evidence corpus" value="Versioned local sources" />
                <GroundingRow label="Raw record egress" value="None" tone="mint" />
                <div className="border-t border-line pt-3">
                  <p className="text-[12px] leading-relaxed text-dim">
                    Retrieval uses a local hybrid lexical and embedding index. Every citation is displayed and links to
                    the original source. POLIS never invents a citation.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => {
                    setMessages([]);
                    setError(null);
                  }}
                >
                  <MessageSquareText className="h-3.5 w-3.5" aria-hidden="true" /> Start a new question
                </Button>
              </div>
            </Panel>

            <Panel>
              <PanelHeader eyebrow="Suggested questions" title="Explore your context" />
              <div className="space-y-0.5 p-2">
                {suggestedPrompts.slice(0, 5).map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    className="flex min-h-11 w-full items-start px-2.5 py-2 text-left text-[13px] leading-relaxed text-muted transition-colors hover:bg-raised hover:text-mist"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </Panel>

            {latestAnswer && latestAnswer.citations.length > 0 && (
              <Panel>
                <PanelHeader eyebrow="Latest sources" title="Evidence trail" />
                <div className="divide-y divide-line">
                  {latestAnswer.citations.slice(0, 4).map((citation, index) => (
                    <a
                      key={citation.id}
                      href={citation.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-raised"
                    >
                      <span className="mt-0.5 shrink-0 font-mono text-[11px] text-signal/80">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[12px] leading-snug text-mist">{citation.title}</span>
                        <span className="mt-1 block font-mono text-[11px] text-dim">
                          {citation.organization} · {citation.published_at ?? "undated"}
                        </span>
                      </span>
                    </a>
                  ))}
                </div>
              </Panel>
            )}

            <Callout tone="warning" title="Safety boundaries">
              No diagnosis. No prescribing or dose changes. Emergency symptoms require emergency services. If the
              evidence or your data are insufficient, the assistant will say so rather than invent an answer.
            </Callout>
          </div>
        </div>
      )}
    </div>
  );
}

function AssistantEmpty({ onPrompt, overview }: { onPrompt: (prompt: string) => void; overview?: Overview | null }) {
  return (
    <div className="flex h-full min-h-[430px] flex-col justify-center px-2 py-8 sm:px-6">
      <p className="mono-label">No messages yet</p>
      <h2 className="mt-3 max-w-lg font-display text-[26px] leading-tight text-mist sm:text-[30px]">
        Ask a question about your record.
      </h2>
      <p className="mt-3 max-w-lg text-[13px] leading-relaxed text-muted">
        POLIS AI reads your recorded context and the curated evidence corpus. It will show what it used, what it could
        not conclude, and which sources support the explanation.
      </p>
      <div className="mt-6 grid w-full max-w-[540px] grid-cols-1 gap-2 sm:grid-cols-2">
        {suggestedPrompts.slice(0, 4).map((prompt) => (
          <button
            key={prompt}
            onClick={() => onPrompt(prompt)}
            className="min-h-11 rounded-[2px] border border-line bg-ink px-3 py-3 text-left text-[13px] leading-relaxed text-muted transition-colors hover:border-signal/30 hover:text-mist"
          >
            {prompt}
          </button>
        ))}
      </div>
      {overview && (
        <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-dim">
          <span>{overview.latest_labs.length} lab signals</span>
          <span aria-hidden="true">·</span>
          <span>{overview.active_medications.length} medications</span>
          <span aria-hidden="true">·</span>
          <span>curated pharmacogenomics</span>
          <span aria-hidden="true">·</span>
          <span>{overview.twin.overall_completeness}% complete</span>
        </div>
      )}
    </div>
  );
}

function ConsentRequired({ onEnable, loading }: { onEnable: () => void; loading: boolean }) {
  return (
    <Panel className="mx-auto max-w-2xl">
      <PanelBody className="flex flex-col items-center py-14 text-center">
        <div className="flex h-12 w-12 items-center justify-center border border-amber/25 bg-amber/[0.05]">
          <LockKeyhole className="h-5 w-5 text-amber" aria-hidden="true" />
        </div>
        <h2 className="mt-5 font-display text-[26px] leading-tight text-mist">AI processing consent is off.</h2>
        <p className="mt-2 max-w-md text-[13px] leading-relaxed text-muted">
          POLIS AI is independently controlled. Enable consent to let the assistant read your recorded context and
          generate grounded explanations. The rest of POLIS remains available without it.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Button variant="primary" onClick={onEnable} loading={loading}>
            Enable AI processing
          </Button>
          <Link href="/privacy" className="btn btn-secondary">
            Review privacy controls
          </Link>
        </div>
        <p className="mt-5 max-w-md text-[12px] leading-relaxed text-dim">
          No raw records are sent to an external model in the default deployment. The deterministic engine composes
          answers locally from retrieved sources and your data.
        </p>
      </PanelBody>
    </Panel>
  );
}

function UserEntry({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 hidden w-10 shrink-0 text-[12px] text-dim sm:block">You</span>
      <div className="min-w-0 flex-1 border-l border-line pl-3 sm:border-l-0 sm:pl-0">
        <span className="mb-1 block text-[12px] text-dim sm:hidden">You</span>
        <p className="text-[14px] leading-relaxed text-mist">{text}</p>
      </div>
    </div>
  );
}

function AssistantEntry({ answer, onFollowUp }: { answer: AssistantAnswer; onFollowUp: (question: string) => void }) {
  const [showContext, setShowContext] = useState(false);
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 hidden w-10 shrink-0 text-[12px] text-signal sm:block">POLIS</span>
      <div className="min-w-0 flex-1 sm:border-l sm:border-signal/25 sm:pl-4">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          <span className="text-[12px] text-signal sm:hidden">POLIS</span>
          <span className="font-mono text-[11px] text-dim">{answer.intent.replaceAll("_", " ")}</span>
          <span className="h-2.5 w-px bg-line" aria-hidden="true" />
          <span className="font-mono text-[11px] text-dim">{answer.engine}</span>
        </div>
        <div className="mt-2 space-y-3">
          {answer.blocks.map((block, index) => (
            <AnswerBlockView key={`${block.type}-${index}`} block={block} answer={answer} />
          ))}
        </div>

        {answer.citations.length > 0 && (
          <div className="mt-3 border-t border-line pt-2.5">
            <div className="mono-label mb-1.5">Sources</div>
            <div className="flex flex-wrap gap-1.5">
              {answer.citations.map((citation, index) => (
                <a
                  key={citation.id}
                  href={citation.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="group inline-flex max-w-full items-center gap-1.5 rounded-[2px] border border-line bg-ink px-2 py-1 transition-colors hover:border-signal/30"
                  title={`${citation.title}, ${citation.organization}`}
                >
                  <span className="font-mono text-[11px] text-signal/80">{String(index + 1).padStart(2, "0")}</span>
                  <span className="truncate text-[12px] text-muted group-hover:text-mist">{citation.organization}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 text-dim" aria-hidden="true" />
                </a>
              ))}
            </div>
          </div>
        )}

        {answer.follow_up_questions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {answer.follow_up_questions.slice(0, 3).map((question) => (
              <FollowUp key={question} question={question} onSelect={onFollowUp} />
            ))}
          </div>
        )}

        <div className="mt-3">
          <button
            onClick={() => setShowContext((value) => !value)}
            className="flex min-h-9 items-center gap-1.5 text-[12px] text-dim transition-colors hover:text-mist"
          >
            <ChevronDown
              className={cn("h-3.5 w-3.5 transition-transform", showContext && "rotate-180")}
              aria-hidden="true"
            />
            Context, missing data and disclaimer
          </button>
          {showContext && (
            <div className="mt-2 space-y-3 rounded-[2px] border border-line bg-ink p-3">
              <div>
                <div className="mono-label mb-1">Context used</div>
                <div className="flex flex-wrap gap-1">
                  {answer.context_used.map((item) => (
                    <span key={item} className="chip">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
              {answer.missing_information.length > 0 && (
                <div>
                  <div className="mono-label mb-1">Missing information</div>
                  {answer.missing_information.slice(0, 5).map((item) => (
                    <p key={item} className="text-[12px] leading-relaxed text-dim">
                      · {item}
                    </p>
                  ))}
                </div>
              )}
              <p className="border-t border-line pt-2 text-[11px] leading-relaxed text-dim">{answer.disclaimer}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AnswerBlockView({ block, answer }: { block: AnswerBlock; answer: AssistantAnswer }) {
  if (block.type === "callout") {
    return (
      <Callout
        tone={block.tone === "danger" ? "danger" : block.tone === "warning" ? "warning" : block.tone === "info" ? "info" : "neutral"}
        title={block.title ?? undefined}
      >
        {block.text}
      </Callout>
    );
  }
  if (block.type === "table" && block.rows?.length) {
    const headers = Object.keys(block.rows[0]);
    return (
      <div>
        {block.title && <div className="mb-1.5 text-[13px] font-medium text-mist">{block.title}</div>}
        <div className="overflow-x-auto rounded-[2px] border border-line">
          <table className="w-full min-w-[420px]">
            <thead>
              <tr className="border-b border-line bg-raised">
                {headers.map((header) => (
                  <th key={header} className="px-2.5 py-2 text-left font-mono text-[11px] font-normal text-dim">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, index) => (
                <tr key={index} className="border-b border-line last:border-0">
                  {headers.map((header) => (
                    <td key={header} className="px-2.5 py-2 text-[12px] text-muted">
                      {String(row[header] ?? "n/a")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
  if (block.type === "bullets" && block.items) {
    return (
      <div>
        {block.title && <div className="mb-1.5 text-[13px] font-medium text-mist">{block.title}</div>}
        <ul className="space-y-1.5">
          {block.items.map((item) => (
            <li key={item} className="flex items-start gap-2.5 text-[14px] leading-relaxed text-muted">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-signal/60" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </div>
    );
  }
  return (
    <div>
      {block.title && <div className="mb-1.5 text-[13px] font-medium text-mist">{block.title}</div>}
      <p className="text-[14px] leading-relaxed text-muted">{block.text}</p>
      {block.citations.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1">
          {block.citations.map((id) => {
            const index = answer.citations.findIndex((citation) => citation.id === id);
            if (index < 0) return null;
            return (
              <a
                key={id}
                href={answer.citations[index].url}
                target="_blank"
                rel="noreferrer noopener"
                className="font-mono text-[12px] text-signal hover:underline"
              >
                [{index + 1}] {answer.citations[index].organization}
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}

function FollowUp({ question, onSelect }: { question: string; onSelect: (question: string) => void }) {
  return (
    <button
      onClick={() => onSelect(question)}
      className="inline-flex items-center rounded-[2px] border border-line bg-ink px-2.5 py-1.5 text-left text-[12px] leading-relaxed text-muted transition-colors hover:border-signal/30 hover:text-mist"
    >
      {question}
    </button>
  );
}

function Thinking() {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 hidden w-10 shrink-0 text-[12px] text-signal sm:block">POLIS</span>
      <div className="min-w-0 flex-1 sm:border-l sm:border-signal/25 sm:pl-4">
        <div className="flex items-center gap-2 text-[13px] text-muted" role="status">
          <LoaderCircle className="h-3.5 w-3.5 animate-spin text-signal" aria-hidden="true" />
          Retrieving evidence and grounding the response
        </div>
      </div>
    </div>
  );
}

function GroundingRow({ label, value, tone }: { label: string; value: string; tone?: "mint" }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[12px] text-dim">{label}</span>
      <span className={cn("max-w-[180px] text-right text-[12px]", tone === "mint" ? "text-mint" : "text-muted")}>
        {value}
      </span>
    </div>
  );
}
