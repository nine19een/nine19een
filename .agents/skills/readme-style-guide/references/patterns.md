# Structures and wording

Choose a short route through the supplied material. These are optional patterns, not mandatory headings or a reason to invent missing content.

| Type | Useful sequence | Keep it proportionate |
| --- | --- | --- |
| Profile | Supplied introduction → caller-selected work/links → interests or contact details supplied for publication | Do not inspect other repositories, select extra work or infer achievements. No install section is needed. |
| Product | Purpose → supplied result/demo → core workflow → confirmed quick start → necessary implementation → limits/docs → license/credits | A short feature table may help comparison; avoid repeating the workflow as a long feature list. |
| Small utility | One-sentence purpose → real command/prerequisites → essential usage and data behavior → limits/terms | Prefer a compact document over empty product sections. |
| Resource collection | Scope → useful navigation/categories → supplied contribution or usage notes → terms/attribution | Explain what links contain. Do not imply linked work is maintained or endorsed. |
| Experiment | Question → supplied setup → documented observations → limitations → supplied reproduction material/terms | Distinguish a hypothesis, a configured procedure and an observed result. Do not promise reproduction or generality. |

## General style

Use direct verbs, short connected paragraphs and descriptive headings. Lead with purpose instead of a stack list. Use lists for actual sequences and parallel items, tables for useful comparisons, and code blocks for exact commands. Do not add sections solely to fill a template.

Preserve distinctions that affect a reader's decision: input versus output, live session versus durable storage, display precision versus saved precision, optional versus default behavior, documented versus executed commands, configured formats versus tested browser results, and original terms versus absent license files.

## Translation

- Express the same meaning naturally; sentence order need not match.
- Keep names, technical identifiers, URLs and executable commands stable.
- Preserve caveats near the claim they qualify. Never translate an unknown as a negative fact or a future plan as an existing capability.
- Keep currency, units, versions and numerical bounds identical. Do not silently localize a price or currency.
- Retain legal notices and attribution accurately; use the original wording/link where necessary to avoid implying a new permission.

## Fictional wording contrasts

These short contrasts illustrate style decisions; they are unrelated to the separate evaluation cases.

| Supplied fact | Avoid | Prefer |
| --- | --- | --- |
| Sketch Nest holds drawings only in tab memory; closing the tab loses them. | “Your drawings are safely saved.” | “Drawings stay in this tab's memory. Closing it loses them.” / “绘图仅保留在当前标签页内存中，关闭后会丢失。” |
| A sample browser produced WebM; MP4 was not tested. | “Export MP4 on every browser.” | “The supplied trial produced WebM; MP4 output has not been tested.” / “提供的试录结果为 WebM，尚未测试 MP4 输出。” |
| The author supplied “All rights reserved; redistribution requires written permission,” with no LICENSE file. | “MIT licensed because the repository is public.” | Retain the supplied terms and explain any missing license-file information separately; do not choose a replacement license. |
| A conversion service is optional, disabled by default and billed after its free allowance; price was not supplied. | “Free conversions with no setup.” | “Optional hosted conversion is off by default and may incur charges beyond the free allowance.” / “可选托管转换默认关闭，超出免费额度后可能收费。” |

If an item is missing entirely, leave the finished document focused on what is known and report the gap to the caller. An unknown startup command is not a reason to guess `npm start`, and an absent demo is not a reason to invent a URL.
