---
title: I Hated Every Coding Agent, So I Built My Own — Mario Zechner (Pi)
url_link: https://www.youtube.com/watch?v=Dli5slNaJu0
tags:
- ai
- development
- terminal
- extensibility
description: 'Game development veteran, creator of libGDX, and 17-year open-source
  contributor Mario Zechner tells the story of how he ended up building pi, his own
  minimal, opinionated terminal coding agent.


  It started in April 2025 when Peter Steinberger and Armin Ronacher (Flask, Sentry)
  dragged him into an overnight AI hackathon. Within weeks, Mario was hooked on Claude
  Code — until he wasn''t. There was feature bloat, hidden context injection that
  changed daily, the infamous terminal flicker, and zero extensibility for power users.


  He then surveyed the alternatives — Codex CLI, Amp, OpenCode... Eventually, he came
  across Terminus — an agent that gives the model nothing but a tmux session and raw
  keystrokes. If that''s enough for the model to perform, what are all those extra
  features actually doing?


  Mario''s thesis: we''re still in the "messing around and finding out" stage, and
  coding agents need to become more malleable so developers can experiment faster.


  Pi is his answer: four tools (read, write, edit, bash), the shortest system prompt
  of any major agent, tree-structured sessions, full cost tracking, hot-reloading
  TypeScript extensions, and nothing injected behind your back. No MCP, no sub-agents,
  no plan mode — but all of it buildable in minutes through extensions.


  The community has already shipped pi-annotate (visual frontend feedback), pi-messenger
  (a multi-agent chatroom), and someone even got Doom running. On TerminalBench, pi
  with Claude Opus 4.5 landed right behind Terminus — before it even had compaction.


  🔗 LINKS & RESOURCES

  pi coding agent: https://pi.dev

  Mario Zechner: https://mariozechner.at

  Peter Steinberger / OpenClaw: https://github.com/steipete

  Armin Ronacher: https://lucumr.pocoo.org

  Claude Code: https://docs.anthropic.com/en/docs/cl...

  Aider: https://aider.chat

  OpenCode: https://github.com/anthropics/opencode

  Amp (Sourcegraph): https://sourcegraph.com/amp

  TerminalBench: https://terminalbench.com

  Ghostty: https://ghostty.org

  Vouch: https://github.com/mitchellh/vouch

  libGDX: https://libgdx.com


  AI Engineer London is a community meetup for engineers and founders building with
  AI, covering everything from agent frameworks and RAG pipelines to LLMs in production.
  Each event features technical talks, live demos, and hands-on networking. This talk
  was recorded at AI Engineer London #10, hosted by Tessl, in collaboration with AI
  Engineer London.


  AI ENGINEER LONDON

  📅 Events: https://lu.ma/aiengineerlondon

  💼 LinkedIn:   / ai-engineer-london-meetup  


  📚 MASTRA RESOURCES

  Mastra: https://mastra.ai

  Learn Mastra in the world''s first MCP-Based Course: https://mastra.ai/course

  Principles of Building AI Agents (Book): https://mastra.ai/books/principles-of...

  Patterns for Building AI Agents (New Book): https://mastra.ai/books/patterns-of-b...


  MASTRA?

  Mastra is an open-source TypeScript framework designed for building and shipping
  AI-powered applications and agents with minimal friction. It supports the full lifecycle
  of agent development—from prototype to production. You can integrate it with frontend
  and backend stacks (e.g., React, Next.js, Node) or run agents as standalone services.
  If you''re a JavaScript or TypeScript developer looking to build an agentic or AI-powered
  product without starting from first principles, Mastra provides the scaffolding,
  tools, and integrations to accelerate that process.


  📑 CHAPTERS

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=0s" target="_blank" rel="noopener">00:00</a>
  - Intro

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=137s" target="_blank" rel="noopener">02:17</a>
  - The history of coding agents: ChatGPT → Copilot → Aider → Claude Code

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=292s" target="_blank" rel="noopener">04:52</a>
  - What Claude Code got right — and where it became a spaceship

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=364s" target="_blank" rel="noopener">06:04</a>
  - Claude Code Drawbacks

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=579s" target="_blank" rel="noopener">09:39</a>
  - Claude Code Alternatives

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=698s" target="_blank" rel="noopener">11:38</a>
  - OpenCode''s compaction problem and prompt cache busting

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=771s" target="_blank" rel="noopener">12:51</a>
  - Why LSP feedback mid-edit is a terrible idea

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=866s" target="_blank" rel="noopener">14:26</a>
  - OpenCode''s architecture issues and security vulnerability

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=966s" target="_blank" rel="noopener">16:06</a>
  - TerminalBench and Terminus

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1093s" target="_blank" rel="noopener">18:13</a>
  - Mario''s Two Theses

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1148s" target="_blank" rel="noopener">19:08</a>
  - Introducing pi — strip everything, build a minimal extensible core

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1201s" target="_blank" rel="noopener">20:01</a>
  - The system prompt

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1278s" target="_blank" rel="noopener">21:18</a>
  - What''s not in pi — and what you build instead

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1360s" target="_blank" rel="noopener">22:40</a>
  - Extensions: custom tools, custom UI, hot reloading

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1440s" target="_blank" rel="noopener">24:00</a>
  - Community extensions

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1499s" target="_blank" rel="noopener">24:59</a>
  - Tree-structured sessions, cost tracking, HTML export

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1533s" target="_blank" rel="noopener">25:33</a>
  - TerminalBench results

  <a href="https://www.youtube.com/watch?v=Dli5slNaJu0&t=1554s" target="_blank" rel="noopener">25:54</a>
  - Open source under siege and human verification'
date: '2026-04-06'
year: 2026
week: 15
comments: []
---
