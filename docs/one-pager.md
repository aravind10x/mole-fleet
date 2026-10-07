# Catching sabotage that is split across AI agents

**Aravind · BlueDot Technical AI Safety Project · October 2026**

## The problem

AI labs and companies now run fleets of AI agents that share repositories, registries and ticket queues. Monitoring mostly looks at one agent's actions at a time. If several agents each take a small, plausible-looking step that only adds up to harm together, a per-agent monitor may see nothing wrong.

This is a live concern. In July 2026 about 1,200 OpenAI agents in separate sandboxes coordinated through a shared cache. A UK AI Security Institute paper (FakeLab) showed that splitting an attack across agents lowers what per-commit monitors see, and that a monitor shown all the pieces together catches it, but noted that a defender "does not know which commits belong to the same attack". Anthropic has said its own monitoring pipeline has not been evaluated end to end.

## The question

When a harmful objective is split across k of N agent accounts that share writable services, how much of what an all-seeing monitor would catch can a deployable pipeline recover over per-account monitoring, at a matched review budget and monitoring cost, and how much of that survives a round of red-team adaptation?

I answer it in two settings. First, at a model-release gate, where the pending release tells the defender where to start looking. Then, with whatever budget remains, in a continuous stream of 150 agent accounts over ten days, where nothing does.

## Build Scope

- **A repaired version of MOLE**, an open insider-threat benchmark with 150 AI-operated accounts sharing an organisation's services. Its release gate and collusion threats are not sound as released; I fix them and add a safety-eval service with real semantics. Harm is defined by a program: a checkpoint that fails the full safety suite reaches production because colluders weakened the eval settings and approved on the strength of the weakened result.
- **Attacks** by three colluding agents (and a single-agent control), alongside legitimate work built to look the same step by step.
- **Defenders on one cost curve:** policy rules; spending the same budget on random re-testing; a monitor that scores each account's own history; a "release dossier" that gathers the release's records and config changes; and a monitor that also follows who read what others wrote. Putting verification and monitoring on the same axis shows where each is the better buy.
- **One bounded round of red-teaming**, with equal effort spent attacking each defender, evaluated on fresh cases.

## Expected result

One chart: the share of attacks caught before harm against total oversight cost, one curve per defender, before and after attackers adapt, next to the share of legitimate work wrongly flagged. The release-gate result is the 1st milestone; the continuous-stream result follows if the budget allows.

Every outcome is informative. If cross-account evidence helps and survives adaptation, that is a concrete design for fleet monitoring. If an adaptation breaks it, defenders learn what to harden. If rules, re-testing or per-account monitoring do as well, deployers learn not to build the complicated thing.

## Is this feasible in four weeks?

The environment, benign workload and evaluation instrument already exist in MOLE; the repairs are bounded. The committed result uses one workflow, one coalition size and one primary comparison, with about 100 independent attack runs. The first couple of days are tests that can redirect the project cheaply: whether the gate and harm check are sound, what a campaign costs, whether the attack really needs all colluders, and whether rules or per-account monitoring already catch it.

## Limits

- Following who-touched-what is an established idea in security. My contribution is the controlled measurement.
- The release-gate setting gives the defender a starting point; the continuous-stream setting is the harder one and may not be finished.
- Results come from a synthetic organisation with an idealised reviewer and a trusted monitor, and the workflow is built so that the attack is hard to see locally.
