# Evaluation Harness

Run the sample evaluation:

```powershell
python -m eval.run_eval --golden eval/golden_cases.sample.json
```

Add more cases:
- Append items to `eval/golden_cases.sample.json`
- Each item needs: `id`, `text`, `sender`, `expected_categories`, `expected_karpman`
- Keep texts short and generic; avoid real personal data
