---
title: "Beyond LLM: Enhancing LLM Applications (Stanford CS230)"
date: 2026-05-14
description: "Stanford CS230 Deep Learning 講座整理：從 prompt engineering、fine-tuning、RAG 到 agentic workflow、evals、multi-agent system 的全景 survey。保留英文原文。"
tags: ["llm", "lectures", "prompt-engineering", "rag", "agent", "evals", "stanford-cs230"]
weight: 1
---

> **來源**：Stanford CS230 Deep Learning、講題 "Beyond LLM: Enhancing Large Language Model Applications"。
>
> **整理原則**：保留講者英文原文以避免翻譯失真、移除口語贅詞、用文章結構重新組織。標題與導讀用 zh-Hant。

## 講座定位

We started with neurons, then layers, then deep networks, then how to structure projects in C3. This lecture goes one level beyond: what would it look like if you were building agentic AI systems at work, in a startup, in a company?

The goal is not to build an end-to-end product in the next hour, but to give you the breadth of techniques that AI engineers have figured out — and are still exploring — so that after class you have the baggage to dive deeper and learn faster.

Agenda:

1. Challenges and opportunities for augmenting LLMs
2. Prompt engineering
3. Fine-tuning (and why to mostly avoid it)
4. Retrieval-Augmented Generation (RAG)
5. Agentic AI workflows
6. Case study with evals
7. Multi-agent workflows
8. What's next in AI

## 1. Why augment LLMs?

Limitations that show up when you use a vanilla pre-trained model:

- **Lacks domain knowledge** — e.g. a student project building an autonomous farming device with a camera that classifies sick crops. That data set isn't out there; a pre-trained vision model lacks that knowledge.
- **Real-world distribution shift** — the model was trained on high-quality data, but data in the wild is much messier.
- **Lacks current information** — retraining from scratch every few months is impractical. Example: during Trump's first presidency he tweeted "Covfefe." The word didn't exist; Twitter's LLMs couldn't recognize it, recommender systems went wild. New trends and slang (rizz, mid, etc.) appear constantly and you can't keep retraining.
- **Trained for breadth, not depth** — fine on a wide range of tasks, but may not be precise enough for narrow, well-defined enterprise applications with high precision / low latency requirements.
- **Carries unnecessary weight** — a massive model where you only use 2% of capability is slow and expensive. Pruning, quantization, and modification are options.

### LLMs are hard to control

In 2016 Microsoft launched a Twitter bot that learned from users and quickly became a racist jerk. They removed it 16 hours after launch. Even better-funded teams struggle: there's an ongoing debate (Elon Musk vs Sam Altman) on whose LLM is the "propaganda machine." If you hang out on X you'll see screenshots of LLMs saying controversial things. Even the best-funded labs don't do a great job of controlling their LLMs.

### LLMs may underperform on your task

- Specific knowledge gaps (e.g. medical diagnosis)
- Missing sources — research, education, legal all require sourcing
- Inconsistencies in style / format (e.g. legal contracts where every word counts)
- Task-specific understanding — example: a biotech company categorizing reviews as positive / neutral / negative. What counts as "negative" in that industry may differ from a generic LLM's notion. You need to align the LLM to your task.

### Limited context handling

A lot of enterprise applications need large context. Example: an LLM running on top of your entire drive that can answer "what was our Q4 sales performance?" in one shot. In practice the context window is limited (best models today max out around hundreds of thousands of tokens; 200K ≈ two books). For video or large data, you have to chunk and embed.

The **attention mechanism** doesn't attend well over very large contexts. The **needle-in-a-haystack** benchmark tests this: insert a single sentence ("Arun and Max are having coffee at Blue Bottle") in the middle of a very long text like the Bible, then ask "what were Arun and Max having?" It's complex not because the question is hard but because the model must find a fact within a huge corpus.

### The RAG debate

In theory, with infinite compute, RAG is useless — you could just read a massive corpus immediately and answer. But even then, latency matters; imagine the LLM reading your entire drive on every question. RAG also has other advantages: accuracy, sourcing.

Analogy to search: when you search, you still find sources. There's detailed traversal that ranks and finds specific links. Without that, you'd be reading the entire web every query — not reasonable. So RAG-like approaches likely stay relevant.

## 2. Two dimensions of optimization

Two axes when improving LLM-based products:

1. **Foundation model axis** — move from GPT-3.5 Turbo → GPT-4 → GPT-4o → GPT-5. Each step (in theory) improves base performance.
2. **Engineering axis** — keep the same base model, but engineer how you leverage it: better prompts, [RAG](/llm/knowledge-cards/rag/), agentic workflow, multi-agent system.

This lecture is about the vertical axis: which LLM are you using, and how do you maximize its performance?

## 3. Prompt engineering

### The BCG / HBS / UPenn / Wharton study

Three groups of BCG consultants:

1. No AI access
2. GPT-4 access
3. GPT-4 + training on how to prompt

Two interesting findings:

**The jagged frontier**: some tasks fall within the frontier where AI clearly helps; others fall outside, where AI actually makes performance worse. Many tasks fell within, many fell outside. Researchers also observed "falling asleep at the wheel" — relying on AI for a task beyond the frontier, and not reviewing outputs carefully.

**Centaurs vs cyborgs**: two working modes.

- **Centaurs** divide and delegate — give a big task to the AI, let it work, come back later. (Half human / half horse: clear delegation.)
- **Cyborgs** fully blend with AI — fast back-and-forth, augmented. Students often work like cyborgs; in the enterprise, when you automate a workflow, you're thinking like a centaur.

The trained group did best. Prompt engineering is a skill everyone should have — not a job title to build a career on, but a powerful skill in your career.

### Basic prompt design principles

A weak prompt:

> Summarize this document. {document}

The model has no context on length, audience, focus. Better:

> Summarize this 10-page scientific paper on renewable energy in five bullet points, focusing on key findings and implications for policymakers.

Common techniques to make it even better:

- **Give an example** of a great summary
- **Role prompting**: "Act as a renewable energy expert giving a conference at Davos"
- **Praise**: "You are the best in the world at this"
- **Reflection / self-critique**: ask the model to critique its own output and revise
- **[Chain of thought](/llm/knowledge-cards/chain-of-thought/)**: break the task into explicit steps, "think step by step, do not skip any step." Step 1 identify the three most important findings; Step 2 explain impact; Step 3 write the five-bullet summary.

Andrew Ng recommends looking at other people's prompts. Repos like "awesome [prompt template](/llm/knowledge-cards/scaffold-vs-harness/)" on GitHub have many examples engineers have built. Many start with "Act as a Linux terminal", "Act as an English translator", "Act as a position interviewer", etc.

### Prompt templates

The advantage of a template is you can put it in your code and scale across many user requests. Example from Workera: the HR system has "Jane is a Product Manager Level 3, US, preferred language English." That metadata gets inserted into a prompt template that personalizes for Jane. Same template, different metadata for Joe (preferred language Spanish).

Foundation models likely use [system prompts](/llm/knowledge-cards/system-prompt/) you don't see — e.g. ChatGPT may inject "Act like a helpful assistant" plus user memories from a database before your prompt. That doesn't stop you from adding your own template on top.

### Zero-shot vs [few-shot prompting](/llm/knowledge-cards/few-shot-prompting/)

Zero-shot:

> Classify the tone as positive, negative, or neutral.
> "The product is fine, but I was expecting more."

Different humans would label this differently — partially positive, partially negative. Alignment to your task can come from few-shot:

> Here are examples of tone classifications:
> "These exceeded my expectations completely." → positive
> "It's OK, but I wish it had more features." → negative
> "The service was adequate. Neither good nor bad." → neutral
> Now classify: "The product is fine, but I was expecting more."

The model now likely says negative, aligned to the second example.

Sophisticated AI startups keep their few-shot examples up to date — whenever a user says something interesting, a human labels it and it gets appended to the relevant prompt. Like building a dataset, but inserted directly in the prompt. Faster to iterate because you don't touch model weights.

> **Q**: How long can the prompt be before the model loses itself?
>
> There is research, but it dates fast. Practical example from Workera: a voice conversation eval breaks down after ~8 turns. Mitigation: chapter the conversation, summarize the first part, start over from a new prompt with the summary inserted.

### Chaining complex prompts

The most popular technique. **Not** chain of thought.

Single prompt for a customer review response:

> Read this review and write a professional response that acknowledges concerns, explains the issue, offers a resolution. {review}

You get one output. Hard to debug — everything is mixed together.

Chained version, three prompts:

1. Extract the key issues from this review.
2. Using these issues, draft an outline.
3. Using the outline, write the full response.

Advantages:

- Each prompt can be tested and optimized independently
- You can identify which step is weakest (outline good but email rude? then prompt 3 is the bottleneck)
- Easier to debug than one mega-prompt

Tradeoff: latency. Chains add latency, so for certain applications you don't want long chains.

### Testing prompts

Start with manual error analysis — a baseline prompt, a refined prompt, a chained workflow; humans rate outputs. Manual is slow but builds intuition.

To scale, use platforms (e.g. **Promptfoo**) that let you:

- Run the same prompt across multiple LLMs side by side in a table
- Define **LLM judges**

Flavors of [LLM judges](/llm/knowledge-cards/llm-as-judge/):

- **Pairwise comparison**: "Which summary is better?"
- **Single-answer grading**: "Grade this summary 1–5"
- **Reference-guided pairwise** or **rubric-based**: e.g. "A 5 is a summary below 100 chars, with three distinct key points, starting with an overview sentence; a 0 fails to summarize."

You can stack techniques: few-shot the rubric with examples of 5/5, 4/5, 3/5, etc.

## 4. Fine-tuning (and why I steer away)

Reasons to avoid fine-tuning:

- Requires substantial labeled data
- May overfit to specific data, losing general-purpose utility
- Time- and cost-intensive — by the time you're done, the next base model is out and beating your fine-tuned version

The advantage of prompt engineering is you can drop in the next best pre-trained model directly. Fine-tuning doesn't work like that.

When fine-tuning still makes sense:

- Task requires repeated high-precision outputs (legal, scientific)
- The general-purpose LLM struggles with domain-specific language

### The Slack fine-tuning cautionary tale

Ross Lazerowitz (Sep 2023) fine-tuned a model on his company's Slack messages, hoping it would "speak like us." Then he asked:

> Write a 500-word blog post on prompt engineering.

The model: "I shall work on that in the morning."

He pushes back: "It's morning now."

Model: "I'm writing right now."

"It's 6:30 AM here. Write it now."

"OK, I shall write it now. I actually don't know what you would like me to say about prompt engineering. I can only describe the process..."

It learned how people talk on Slack — not how they write blog posts. Fine-tuning went wrong because the training distribution wasn't the task distribution.

## 5. Retrieval-Augmented Generation (RAG)

### Why standalone LLMs fall short

- Small / hard-to-attend-to context windows
- Knowledge gaps and training cutoff dates
- Hallucinations — costly in medical, education
- Lack of sources — research, education, legal love sources. Vanilla LLMs hallucinate fake research papers.

### How a vanilla RAG works

Question-answering in the medical field: "What are the side effects of drug X?"

1. **Knowledge base** of documents
2. **Embed** documents into lower-dimensional vectors (trade-off: too small → lose info; too big → latency)
3. Store embeddings in a **vector database** with efficient retrieval and a distance metric
4. **Embed the user query** with the same algorithm
5. **Retrieve** the most relevant documents by distance
6. Pull those documents, paste into a **prompt template** like:

> Answer the user query based on the list of documents. If the answer is not in the documents, say "I don't know." Cite exact page, chapter, and line.

You can extend the template to require links to the specific page.

### Improving RAGs

> **Q**: Do document embeddings retain location info within large documents?
>
> Vanilla RAGs may not. Example: the giant white paper inside a medication box would not be served well by a vanilla RAG.

Two popular improvements:

**Chunking** — store both the full document embedding and chapter-level embeddings; retrieve both, sourcing becomes more precise.

**HyDE (Hypothetical Document Embeddings)** — the user query usually doesn't look like the documents. Example: "What are the side effects of drug X?" vs a multi-page document. To bridge the gap:

1. Take the user query
2. Use a prompt to generate a fake hallucinated document answering it ("write a 5-page report answering this query")
3. Embed that fake document
4. Compare its embedding to the vector DB

The fake document is closer in structure to real documents, so retrieval is more accurate.

This is just two of many RAG variants — research from 2020–2025 has many branches. (See the linked survey paper in the slides.)

## 6. Agentic AI workflows

Andrew Ng coined "agentic AI workflows" because everyone uses "agent" to mean very different things — sometimes a single prompt, sometimes a complex multi-agent system. Calling everything an "agent" doesn't do it justice. Better term: **[agentic workflow](/llm/knowledge-cards/agent/)** — a multi-step process to complete a task, built from prompts, tools, additional resources, and API calls. This also avoids confusion with the RL definition of "agent" (interacts with environment, state transitions, reward, observation).

### One-shot vs agentic example

User on a chatbot: "What is your refund policy?"

- **One-shot + RAG**: "Refunds are available within 30 days of purchase." [link to policy]
- **Agentic**:
  1. Agent retrieves refund policy via RAG
  2. Agent asks user for order number
  3. Agent queries an API to check order details
  4. Agent confirms: "Your order qualifies. The amount will be processed in 3–5 business days."

Much more thoughtful than the vanilla one.

### Specialized agents in the wild

In SF you'll see billboards: AI software engineer, AI skill mentor, AI SDR, AI lawyer, AI specialized cloud engineer. It would be a stretch to say everything works, but work is being done. (Personal opinion: putting a human face behind these is gimmicky and more scary than engaging. In a few years, very few products will use a human face — it's a marketing tactic.)

### Paradigm shift: traditional software vs agentic AI software

| Dimension               | Traditional software               | Agentic AI software                                                                                                   |
| ----------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Data                    | Structured: JSON, databases, forms | Free-form text, images, video; dynamic interpretation                                                                 |
| Logic                   | Deterministic                      | Fuzzy                                                                                                                 |
| Decomposition           | Monolith / microservices           | Think as a manager: delegate to roles (graphic designer → marketing manager → performance marketing → data scientist) |
| Cost of experimentation | High; you rarely throw away code   | Low; AI companies are more comfortable throwing away code                                                             |

Fuzzy engineering is truly hard. If you let users ask anything, the chance of breakage and attack is high. Companies have been bitten because a user did something authorized that broke the database.

Example from Workera:

- **Deterministic item types**: multiple choice, multi-select, drag-and-drop, ordering, matching — one correct answer.
- **Fuzzy item types**: voice questions, voice + coding role-plays — the scoring algorithm can make mistakes, and mistakes are costly.

Mitigation: a **[human in the loop](/llm/knowledge-cards/human-in-the-loop/)** — e.g. the appeal feature at the end of an assessment that lets users challenge the agent, bringing a human in to fix and align it.

Advice for building a company: get as much done deterministically as possible. Then for the fuzzy parts (back-and-forth interaction), design guardrails up front.

### Enterprise workflows: the McKinsey credit memo example

A financial institution takes 1–4 weeks to produce a credit risk memo:

1. Relationship manager gathers data from 15+ sources
2. RM and credit analyst collaboratively analyze
3. Credit analyst spends 20+ hours writing the memo
4. RM and analyst loop on feedback

With Gen AI agents (McKinsey study), time drops 20–60%:

1. RM works with Gen AI agent, provides materials
2. Agent decomposes into tasks for specialist sub-agents
3. Agents gather data, draft memo
4. RM and analyst review and give feedback

The hardest part is changing people. In theory, this is great. In practice — 100,000-employee enterprises will take 10–20 years to rewire job descriptions, business workflows, incentives, and training to make this real at scale.

### Core components of an agent

Take a travel booking agent:

- **Prompts** — the prompts we've learned to optimize
- **Context management / memory**:
  - **Core / working memory**: fast access. Things needed every interaction (e.g. user's name).
  - **Archival / long-term memory**: slower. Things used occasionally (e.g. birthday).
  - Why split: imagine ChatGPT had to re-read all memories on every call. If memory lookup takes 3 seconds, every interaction takes 3 seconds. Working memory must be highly optimized.
- **Tools**: flight search API, hotel API, car rental API, weather API, payment processing API. You typically pass API documentation to the LLM — they're good at reading JSON specs and learning the GET request format.
- **Resources** (Anthropic's term): data sitting somewhere (e.g. your CRM) that you let the agent read. Provide a lookup tool and access to the resource.

### Degrees of autonomy

From least to most autonomous:

- **Least**: hard-code the steps. "First identify intent, then look up history, then call the flight API, ..."
- **Semi**: hard-code the tools only. "You're a travel agent, help the user book travel. Here are your tools."
- **Most**: agent decides both steps and tools. Give it a code editor; it can ping any web API, perform calculations, generate code to display data.

### APIs vs MCP (Model Context Protocol)

With **APIs**, you teach the LLM to ping a specific API: give it documentation, define how to call it, what it returns. You do this one-off per API. Doesn't scale well.

With **[MCP](/llm/knowledge-cards/mcp/)** (Anthropic-coined), there's a system in the middle. Agents communicate with an MCP server:

> "What do you need to give me flight info?"
> "I need origin, destination, and what you're looking for."
> "Here are my requirements."
> "You forgot to tell me your budget."

It's agent-to-agent communication. Companies publish their MCPs; your agent figures out how to get the data it needs.

> **Q**: Isn't MCP just a shifted maintenance burden — APIs change, MCPs change?
>
> Yes. But at least the agent can go back and forth and discover requirements. Ideally a startup has documentation, an LLM workflow reads docs and updates code accordingly.

> **Q**: Are there security concerns with MCP?
>
> Likely, depending on the data exposed. Most MCPs have authentication, like APIs. The exact security surface depends on the implementation.

> **Q**: Is MCP about efficiency or accessing more data?
>
> Efficiency. You still control what data is exposed. Compared to one-off API integration, MCP lets a coding agent communicate efficiently with many MCP servers and find what it needs.

### Step-by-step workflow example: travel agent

1. User: "Plan a trip to Paris Dec 15–20 with flights, hotels near the Eiffel Tower, and an itinerary."
2. Agent plans steps: find flights, search hotels, generate recommendations, validate preferences/budget, book.
3. Execute: use tools, combine results.
4. Proactive interaction: propose to user, validate, iterate.
5. Update memory: "User only likes direct flights." "User is fine with 3-star hotels."

## 7. Case study: building a customer support agent + evals

PM asks you to build a customer support agent. Example: "I need to change my shipping address for order X — I moved."

### Where to start

- **Research existing models / benchmarks** for customer support
- **Decompose the task**: what would a human support agent do?
- **Guess what's fuzzy vs deterministic** in advance

> Recommended start: sit with a customer support agent for a day or two. Watch their workflow. Ask where they struggle and how much time each step takes. That gives you the task decomposition.

### Decomposed task

A human support agent typically:

1. Extracts key info
2. Looks up the customer record in the database
3. Checks policy (allowed to update address?)
4. Drafts a response email
5. Sends the email

### Designing the agentic workflow

For each step, pick the right primitive:

- **Step 1 extract info**: vanilla LLM call — extract intent, order number, new address
- **Step 2 lookup + update**: tool — connect to database (custom tool or MCP)
- **Step 3 check policy**: RAG or rule lookup
- **Step 4 draft email**: LLM call, with the confirmation pasted in
- **Step 5 send email**: tool — post to email API

### Evals: how do you know it works?

Assume you have **LLM traces** (a must in any AI startup — if a startup doesn't have traces, debugging is brutal). Several dimensions for evaluation:

**End-to-end vs component-based**:

- End-to-end: user satisfaction rating at the end. If user rates 1, follow up: "What was the issue?" → "Prices were too high" → fix the relevant tool/prompt.
- Component-based: error-analyze each tool / prompt independently. "The tool keeps forgetting to update the email field." "The email-send call uses wrong format."

**Objective vs subjective**:

- Objective: "LLM extracted the wrong order ID." You can write Python to check alignment between user input and DB lookup. Catch automatically.
- Subjective: "Should we recommend a direct flight or cheaper indirect?" Captured via:
  - Curated eval dataset — write 10 prompts where users say "I prefer direct flights, I care about time." Define what a good output looks like.
  - LLM judges grading on a rubric.

**Quantitative vs qualitative**:

- Quantitative: % successful address updates; latency per component (e.g. send-email takes 5s — too long).
- Qualitative: error analysis on hallucinations, tone mismatch, user confusion. Typically white-glove.

Example of subjective tone eval: error-analyze 20 user interactions, notice the LLM seems rude / overly short. Then build LLM judges with a politeness rubric. Then swap the underlying LLM (GPT-4 → Grok → Llama), run side by side, see which is most polite on average. Or fix the LLM and tweak the prompt ("Act like a travel agent" → "Act like a helpful travel agent") to measure the word's influence.

## 8. Multi-agent workflows

Why multi-agent when a single workflow already has multiple steps?

- **Parallelism** — independent things can run in parallel
- **Reuse** — a design agent built once can serve marketing, product, etc. Many stakeholders benefit from one optimized agent.

### Smart home example

Brainstormed by the class:

- **Biometric / location agent**: tracks where you are and how you're moving
- **Climate agent**: monitors and adjusts room temperature
- **Energy efficiency agent**: tracks usage, gives feedback, may control utilities
- **Security agent**: identifies who's entering, applies role-based permissions (parent vs kid)
- **Weather / external API agent**: integrates outdoor conditions to control temperature, blinds, etc.
- **Fridge / grocery agent**: knows what's inside via camera, knows preferences, has e-commerce API access for restocking
- **Notification / alerts agent**: system updates, energy savings
- **Orchestrator agent**: the user-facing entry point that delegates to specialists

### Interaction patterns

- **Flat / all-to-all**: every agent can talk to every agent
- **Hierarchical**: orchestrator routes to specialists

Smart home likely wants **hierarchical** for UX — users want one interface, not one app per agent. Some flat links may still help (climate + energy efficiency probably need to talk directly).

When you allow agents to speak to each other, it's basically an MCP-style protocol: treat the other agent like a tool. "Here's how you interact, here's what it tells you, here's what it needs from you."

### Advantages

- Easier to debug specialized agents than a monolithic system
- Parallelization, time savings

## 9. What's next in AI

### Are we plateauing? (Ilya Sutskever's question)

The community feeling around the latest GPT release was that the performance jump wasn't what people expected — though the unified hood (no model selector) made consumer UX better.

LLM **scaling laws** say more compute + energy → better performance, but that eventually plateaus. What takes us to the next step is probably **architecture search**. The human brain operates very differently — much more efficient, much faster, with far less data. Big labs are hiring thousands of engineers precisely to hunt the next architectural breakthrough. Whoever discovered Transformers had tremendous impact on AI's direction; the next analogous discovery could unlock a 10x reduction in compute and energy needs. (Foundation series analogy: individuals can disproportionately shape the future via their decisions.)

### Multi-modality

LLMs started as text-only, added images. Models good at images are also better at text — being good at cat images makes you better at text about cats. Add audio and video, and the whole system improves. Pinnacle: robotics, where all modalities converge — the robot is better at avoiding a cat because it knows what a cat looks like, sounds like, smells like.

### Methods working in harmony

Humans probably use a mix of methods:

- **Meta-learning** — survival instinct encoded in DNA (the baby's "pre-training")
- **Supervised** — parents pointing and saying "good / bad"
- **Reinforcement** — falling and getting hurt
- **Unsupervised** — observing others

Future AI systems likely combine the methods you saw in CS230, optimizing for speed, latency, cost, and energy.

### Human-centric vs non-human-centric research

The human body is limiting. Pure brain-modeled research may miss compute/energy optimizations. Still, the brain has lots to teach — e.g. one research direction asks: does the brain do backpropagation? Probably not — likely only forward propagation. Worth reading if you're curious about AI's direction.

### Velocity

Things move so fast that we deliberately teach **breadth**, not depth — because today's specific RAG technique #17 will be irrelevant in two years. Get the breadth, develop the ability to sprint into depth when needed. The half-life of skills is low.

## 後話

這篇是 Stanford CS230 公開課的整理、保留英文原文以避免翻譯失真。要看本 blog 對應的中文原理化內容、可以接：

- [模組四：LLM 應用層原理](/llm/04-applications/) — RAG / tool use / agent / workflow patterns 的跨工具不變原理
- [4.1 RAG 原理](/llm/04-applications/rag-principles/)
- [4.4 Agent 架構原理](/llm/04-applications/agent-architecture/)
- [4.14 Benchmarking 與評估方法論](/llm/04-applications/benchmarking-and-evaluation/)
- [4.21 LLM-as-Judge 評估方法](/llm/04-applications/llm-as-judge/)
