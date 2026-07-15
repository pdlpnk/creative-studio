# Visual Library v1

Visual Library is a local art-direction source used only by `agents/designer/prompt_builder.py`. It gives Designer concrete, reusable visual hooks, scene objects, reading patterns, compositions, palettes, backgrounds and emotions.

The `.yaml` files use JSON syntax, which is valid YAML 1.2. This keeps the library readable while allowing Designer to load it with the Python standard library and no new dependency.

## Selection rules

- One hook, one pattern and one composition per prompt.
- At most two supporting objects.
- A hook/pattern/composition tuple cannot repeat within a single Designer batch.
- Crypto, USDT, cashback, large numbers, membership and sports hooks require explicit confirmation in the input; they are never added from the library alone.
- All people are clearly adults. No real celebrities, protected brands, fake reviews, fabricated statistics, guaranteed outcomes or risk-free claims are permitted.

The library describes visuals only. It cannot author, alter or approve banner claims; `Approved Text` remains limited to text supplied by the Creative Plan.
