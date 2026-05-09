import { AlertCircle, Check, Clipboard, Eraser, RefreshCw, Save, Wand2 } from "lucide-react";
import { useState } from "react";
import { api, Reference, ReplyResponse } from "../api/client";
import { Button, Panel, PrimaryButton, Textarea } from "../components/ui";

export default function ReplyWorkbench() {
  const [question, setQuestion] = useState("老师，我论文系统上传后一直显示待审核怎么办？");
  const [answer, setAnswer] = useState("");
  const [meta, setMeta] = useState<Omit<ReplyResponse, "answer"> | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [faqSaved, setFaqSaved] = useState(false);
  const [error, setError] = useState("");

  async function generate(style = "normal") {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.generateReply(question, style);
      setAnswer(data.answer);
      setMeta({
        category: data.category,
        confidence: data.confidence,
        need_human_review: data.need_human_review,
        references: data.references,
        ai_used: data.ai_used,
        ai_provider: data.ai_provider,
        ai_model: data.ai_model,
        ai_error: data.ai_error
      });
      await api.createHistory({
        student_question: question,
        ai_answer: data.answer,
        final_answer: data.answer,
        category: data.category,
        confidence: data.confidence,
        need_human_review: data.need_human_review
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  async function rewrite(style: string) {
    if (!answer.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.rewriteReply(question, answer, style);
      setAnswer(data.answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "改写失败");
    } finally {
      setLoading(false);
    }
  }

  async function copyAnswer() {
    await navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function saveFAQ() {
    if (!question.trim() || !answer.trim()) return;
    setError("");
    try {
      await api.createFAQ({
        question,
        answer,
        category: meta?.category || "其他",
        allow_auto_reply: true
      });
      setFaqSaved(true);
      setTimeout(() => setFaqSaved(false), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存 FAQ 失败");
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="学生问题">
          <Textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={13} />
          <div className="mt-3 flex flex-wrap gap-2">
            <PrimaryButton onClick={() => generate("normal")} disabled={loading}>
              <Wand2 size={16} />
              生成回复
            </PrimaryButton>
            <Button onClick={() => generate("normal")} disabled={loading || !answer}>
              <RefreshCw size={16} />
              重新生成
            </Button>
            <Button onClick={() => setQuestion("")}>
              <Eraser size={16} />
              清空输入
            </Button>
          </div>
        </Panel>

        <Panel
          title="AI 建议回复"
          action={
            meta ? (
              <div className="flex items-center gap-2 text-xs">
                <span className="rounded bg-slate-100 px-2 py-1">{meta.category}</span>
                <span className={meta.ai_used ? "text-emerald-700" : "text-slate-500"}>
                  {meta.ai_used ? `已调用模型${meta.ai_model ? `：${meta.ai_model}` : ""}` : "未调用模型"}
                </span>
                <span className={meta.need_human_review ? "text-amber-700" : "text-emerald-700"}>
                  {meta.need_human_review ? "建议人工核实" : "可审核后发送"}
                </span>
                <span>{Math.round(meta.confidence * 100)}%</span>
              </div>
            ) : null
          }
        >
          {error && (
            <div className="mb-3 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm leading-6 text-red-700">
              <AlertCircle className="mt-0.5 shrink-0" size={16} />
              <span>{error}</span>
            </div>
          )}
          {meta?.ai_error && (
            <div className="mb-3 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-800">
              <AlertCircle className="mt-0.5 shrink-0" size={16} />
              <span>大模型调用失败：{meta.ai_error}</span>
            </div>
          )}
          <Textarea value={answer} onChange={(event) => setAnswer(event.target.value)} rows={13} placeholder="生成后的回复会显示在这里，老师可直接修改。" />
          <div className="mt-3 flex flex-wrap gap-2">
            <PrimaryButton onClick={copyAnswer} disabled={!answer}>
              {copied ? <Check size={16} /> : <Clipboard size={16} />}
              {copied ? "已复制" : "复制回复"}
            </PrimaryButton>
            <Button onClick={() => rewrite("formal")} disabled={loading || !answer}>更正式</Button>
            <Button onClick={() => rewrite("shorter")} disabled={loading || !answer}>更简短</Button>
            <Button onClick={() => rewrite("warmer")} disabled={loading || !answer}>更温和</Button>
            <Button onClick={saveFAQ} disabled={!answer || faqSaved}>
              {faqSaved ? <Check size={16} /> : <Save size={16} />}
              {faqSaved ? "已保存" : "保存 FAQ"}
            </Button>
            <Button
              onClick={() => setMeta((current) => current ? { ...current, need_human_review: true } : current)}
              disabled={!answer}
            >
              标记人工核实
            </Button>
          </div>
        </Panel>
      </div>

      <Panel title="检索依据">
        {meta?.references.length ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {meta.references.map((ref: Reference, index) => (
              <article key={`${ref.title}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <h3 className="mb-2 text-sm font-semibold text-slate-800">{ref.title}</h3>
                <p className="line-clamp-5 whitespace-pre-wrap text-sm leading-6 text-slate-600">{ref.content}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">生成回复后会显示 FAQ 或知识库片段。没有明确依据时会提示人工核实。</p>
        )}
      </Panel>
    </div>
  );
}
