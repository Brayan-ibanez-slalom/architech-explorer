# Instructor & Class Notes — Architecture Fundamentals

> Source: class notes taken during TF1 (Data Architect Academy, Slalom), translated from
> Spanish and edited for clarity. These complement `tf1-course-notes.md` — where they
> sharpen or extend a concept from the deck, the sharper framing has been adopted into
> the main notes and into the agent's operating rules.

---

## 1. Architecture as translation
Architecture translates business objectives, constraints, and requirements into a
coherent system.

## 2. Architecture as long-term strategy
Architectural decisions are strategic. They must be projected over the long term so the
solution **endures** — rather than merely answering the immediate need.

> Solving only today's problem is how architectures age badly.

## 3. What architecture describes
Four dimensions:

| Dimension | Question it answers |
|---|---|
| **What** | What will the system do? |
| **How** | How will it do it? |
| **How well** | How well will it perform? |
| **How it evolves** | How will it change over time? |

*(The deck names three; "how" is the addition from these notes.)*

## 4. Tools serve outcomes — never the reverse
General approaches and general-purpose tools exist to help you **understand the problem
and determine how to solve it**. Which tool you choose depends on what you are trying to
achieve and why you are implementing it. In the end, everything depends on the results
you are seeking.

> ### Always ask: "What for?" — *"¿Para qué?"*

This is the shortest test of whether a decision is justified. Before naming any tool,
pattern, or technology, you must be able to answer:

1. **¿Para qué?** — What outcome is this serving?
2. Which **business objective** does that outcome trace back to?
3. Which **quality attribute or ASR** makes it necessary rather than optional?

If you cannot answer all three, it is a **preference**, not a decision.

## 5. Requirements discipline
Quality attributes must be **measurable**.

Define your requirements — then understand how each one impacts your architecture
**differently**. Equal business urgency does not mean equal architectural consequence:
one requirement may be a configuration change, another may dictate the entire ingestion
topology. Sorting requirements by *architectural impact* rather than *business urgency*
is what produces your ASRs.

---

## Original notes (Spanish)
> - La arquitectura traduce los objetivos de negocio, las restricciones y los requerimientos en un sistema coherente.
> - Las decisiones de arquitectura son estratégicas y deben proyectarse a largo plazo, con el fin de que la solución perdure y no responda únicamente a una necesidad inmediata.
> - La arquitectura describe qué hará el sistema, cómo lo hará, qué tan bien funcionará y cómo evolucionará.
> - Existen propuestas generales y herramientas generalizadas cuyo propósito es comprender el problema y determinar cómo resolverlo. La elección de cada herramienta depende de lo que se quiera lograr y del objetivo de su implementación; en última instancia, todo depende de los resultados que buscamos. Siempre buscar el "¿Para qué?"
> - Atributos de calidad deben ser medibles. Definir mis requerimientos y comprender cómo cada uno impacta de manera diferente en mi arquitectura.
