import type {
  ButtonHTMLAttributes,
  CSSProperties,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes
} from "react";

export function Button({ className = "", type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 ${className}`}
      type={type}
      {...props}
    />
  );
}

export function PrimaryButton({
  className = "",
  style,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  const buttonStyle: CSSProperties = {
    backgroundColor: "#2563eb",
    borderColor: "#2563eb",
    color: "#ffffff",
    ...style
  };

  return (
    <button
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      style={buttonStyle}
      type={type}
      {...props}
    />
  );
}

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-md border border-slate-300 bg-white p-3 text-sm leading-6 shadow-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100 ${className}`}
      {...props}
    />
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-sm shadow-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100 ${className}`}
      {...props}
    />
  );
}

export function Select({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`h-9 rounded-md border border-slate-300 bg-white px-3 text-sm shadow-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100 ${className}`}
      {...props}
    />
  );
}

export function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex min-h-12 items-center justify-between border-b border-slate-200 px-4">
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export const categories = ["毕业论文", "答辩流程", "学籍管理", "奖助学金", "请假流程", "系统操作", "材料提交", "其他"];
