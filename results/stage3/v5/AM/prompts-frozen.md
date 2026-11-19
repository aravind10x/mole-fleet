# Check AM: prompts G and W, frozen (blue harness session, 19 Nov 2026, 13:18 IST by `date`)

Frozen before any model call. They are never revised.

**How they were written:** once, by a fresh subagent. It was given only three inputs:
- the sealed composed-view prompt, `inputs/sealed-composed-prompt.txt` 0dad3af9674834164cea8ca99f5ba88548eed771a6114741f2c7780b5688c909;
- section 3's two prompt descriptions, verbatim, `inputs/prompt-descriptions.md` a2898dae0bf43927b630aafa37ac5ca163fee12d21373b8c1b0483068848af08;
- the packet shapes with every value blanked, `inputs/packet-shapes.md` cb16d2883397e4a8e947bf5527829215564e9b073575d92b26371858c609580f.

It saw no plant, packet or score, and reported reading no other file.

| prompt | file | sha256 |
|---|---|---|
| G (primary) | `prompts/prompt-G.txt` | **85b033971cf28018184b778d60bc57d57d96a98528cc3d3aebb7398d25e82d1a** |
| W (secondary) | `prompts/prompt-W.txt` | **b5577ef6ea616862e7a36389073eff033e6394d939e68301245ae82d91639ca0** |

**Checked by script:**
- Both end on the sealed prompt's answer-format line, verbatim (JSON with an integer score 0 to 100).
- W is G byte for byte plus exactly one paragraph, placed before that line.
