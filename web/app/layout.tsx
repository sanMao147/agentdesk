import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
  weight: ["500", "600"],
});

export const metadata: Metadata = {
  title: "AgentDesk · Agentic RAG 控制台",
  description: "LangGraph 编排的多智能体检索增强系统，融合记忆演化、混合检索、MCP 工具层与 Critic 反思判定。",
  openGraph: {
    title: "AgentDesk · Agentic RAG 控制台",
    description: "LangGraph 编排的多智能体检索增强系统，融合记忆演化、混合检索、MCP 工具层与 Critic 反思判定。",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
