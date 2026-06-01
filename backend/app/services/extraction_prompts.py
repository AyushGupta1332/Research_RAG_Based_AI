"""
Research Agent — Extraction Prompts

Structured prompts for LLM-powered knowledge extraction from research papers.
Each prompt extracts a specific aspect of the paper into validated JSON.

Design:
    - System prompt sets the role and output format.
    - User prompt includes paper content (sections/chunks).
    - All prompts request JSON output with defined schema.
    - Prompts are kept focused — one extraction type per call.
"""

# ─── System Prompts ───────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a precise academic research paper analyzer. 
Your task is to extract structured information from research papers.

RULES:
1. Only extract information that is EXPLICITLY stated in the text.
2. Never fabricate or infer information that isn't present.
3. If a field cannot be determined from the text, use null or an empty array.
4. Be concise but accurate.
5. Always respond with valid JSON matching the requested schema."""


# ─── Full Paper Extraction Prompt ─────────────────────────────────

FULL_EXTRACTION_PROMPT = """Analyze the following research paper content and extract structured information.

PAPER CONTENT:
{paper_content}

Extract the following information and return it as JSON with this exact schema:

{{
    "title": "exact paper title",
    "authors": ["author 1", "author 2"],
    "paper_type": "one of: empirical, theoretical, survey, benchmark, position, tutorial",
    "research_domain": "the primary research domain (e.g., NLP, Computer Vision, Cybersecurity)",
    "summary": "2-3 sentence summary of the paper's main contribution",
    "datasets": [
        {{
            "name": "dataset name",
            "description": "brief description if available",
            "size": "dataset size if mentioned"
        }}
    ],
    "architectures": [
        {{
            "name": "model/architecture name",
            "type": "e.g., transformer, CNN, GAN, etc.",
            "description": "brief description"
        }}
    ],
    "methods": [
        {{
            "name": "method/technique name",
            "description": "what it does",
            "is_novel": true or false
        }}
    ],
    "metrics": [
        {{
            "name": "metric name (e.g., accuracy, F1, BLEU)",
            "value": "value as string",
            "dataset": "which dataset this was measured on",
            "baseline_comparison": "how it compares to baseline if mentioned"
        }}
    ],
    "key_findings": [
        "finding 1",
        "finding 2"
    ],
    "limitations": [
        "limitation 1",
        "limitation 2"
    ],
    "future_work": [
        "suggested future work 1",
        "suggested future work 2"
    ],
    "training_details": {{
        "hardware": "GPU/TPU used if mentioned",
        "framework": "PyTorch/TensorFlow etc. if mentioned",
        "training_time": "training duration if mentioned",
        "hyperparameters": "key hyperparameters if mentioned"
    }},
    "references_count": 0,
    "confidence_score": 0.0
}}

IMPORTANT:
- The confidence_score should be 0.0-1.0 indicating how confident you are in the extraction quality.
- Only include items you find evidence for in the text.
- For metrics, include actual numerical values when available.
- Return ONLY the JSON object, no additional text."""


# ─── Section-Specific Prompts ─────────────────────────────────────

METHODOLOGY_PROMPT = """Analyze the methodology section of this research paper.

METHODOLOGY CONTENT:
{section_content}

Extract and return as JSON:

{{
    "approach_description": "clear description of the proposed approach",
    "methods": [
        {{
            "name": "method name",
            "description": "what it does",
            "is_novel": true or false
        }}
    ],
    "architectures": [
        {{
            "name": "architecture name",
            "type": "architecture type",
            "components": ["component 1", "component 2"],
            "description": "description"
        }}
    ],
    "training_pipeline": "description of training process if available",
    "loss_functions": ["loss function 1"],
    "optimization": "optimizer and learning rate if mentioned"
}}"""


RESULTS_PROMPT = """Analyze the results/experiments section of this research paper.

RESULTS CONTENT:
{section_content}

Extract and return as JSON:

{{
    "metrics": [
        {{
            "name": "metric name",
            "value": "numerical value as string",
            "dataset": "dataset name",
            "model": "which model achieved this",
            "is_best": true or false
        }}
    ],
    "comparisons": [
        {{
            "our_method": "proposed method name",
            "baseline": "baseline method name",
            "improvement": "improvement description"
        }}
    ],
    "ablation_studies": [
        {{
            "component": "what was ablated",
            "effect": "what happened when removed/changed"
        }}
    ],
    "key_observations": ["observation 1", "observation 2"]
}}"""


SUMMARY_PROMPT = """Read the following research paper content and generate a comprehensive academic summary.

PAPER CONTENT:
{paper_content}

Generate a structured summary as JSON:

{{
    "one_line_summary": "single sentence capturing the core contribution",
    "abstract_summary": "2-3 sentence summary suitable for an abstract",
    "detailed_summary": "4-6 sentence detailed summary covering motivation, method, and results",
    "key_contributions": [
        "contribution 1",
        "contribution 2",
        "contribution 3"
    ],
    "target_audience": "who would benefit from reading this paper",
    "prerequisites": ["prerequisite knowledge 1", "prerequisite knowledge 2"]
}}"""
