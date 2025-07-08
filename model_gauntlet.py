# model_gauntlet.py
import argparse
import ast
import json
import os
import sys
import time
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


# --- Pre-emptive Mocking of Django Modules ---
class MockTextChoices(str, Enum):
    def __new__(cls, value, label):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj


class MockModels:
    TextChoices = MockTextChoices


sys.modules['django'] = type('django', (), {})()
sys.modules['django.db'] = type('db', (), {'models': MockModels()})()
sys.modules['django.db.models'] = sys.modules['django.db'].models

# --- Add Project Directories to Python Path ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'services'))
sys.path.insert(0, os.path.join(project_root, '.'))

# --- Import Project Modules ---
from pydantic import BaseModel, Field, ValidationError
from ai.client import get_client
from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages
from learning.enums import CEFR, PhraseCategory


class ASTVisitor(ast.NodeVisitor):
    """
    An AST visitor to find and extract the _SYSTEM_PROMPT variable
    and the Pydantic BaseModel class definition from a service file.
    """

    def __init__(self):
        self.system_prompt: Optional[str] = None
        self.pydantic_class_source: Optional[str] = None
        self.pydantic_class_name: Optional[str] = None

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == '_SYSTEM_PROMPT':
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.system_prompt = node.value.value
                    print("✅ Successfully extracted _SYSTEM_PROMPT.")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        is_pydantic_model = any(isinstance(b, ast.Name) and b.id == 'BaseModel' for b in node.bases)
        if is_pydantic_model:
            self.pydantic_class_source = ast.unparse(node)
            self.pydantic_class_name = node.name
            print(f"✅ Successfully extracted Pydantic model source: '{self.pydantic_class_name}'.")
        self.generic_visit(node)


def extract_from_service_file(file_path: str) -> Tuple[str, str, str]:
    """
    Opens and parses a Python file to extract key components using AST.
    """
    print(f"🔬 Analyzing service file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"❌ ERROR: Service file not found at '{file_path}'")
        sys.exit(1)

    tree = ast.parse(source_code)
    visitor = ASTVisitor()
    visitor.visit(tree)

    if not all([visitor.system_prompt, visitor.pydantic_class_source, visitor.pydantic_class_name]):
        missing = [name for name, var in
                   [("_SYSTEM_PROMPT", visitor.system_prompt), ("Pydantic Class", visitor.pydantic_class_source)] if
                   not var]
        print(f"❌ ERROR: Could not extract: {', '.join(missing)}.")
        sys.exit(1)

    return visitor.system_prompt, visitor.pydantic_class_source, visitor.pydantic_class_name


def create_pydantic_model_from_source(class_name: str, source: str) -> type[BaseModel]:
    """
    Dynamically creates a Pydantic model class from its source code.
    """
    namespace = {
        'BaseModel': BaseModel, 'Field': Field, 'Optional': Optional,
        'CEFR': CEFR, 'PhraseCategory': PhraseCategory
    }
    exec(source, globals(), namespace)
    DynamicModel = namespace[class_name]
    print(f"✅ Dynamically compiled Pydantic model '{class_name}'.")
    return DynamicModel


def run_gauntlet(
        models: List[str],
        phrases: List[Dict[str, str]],
        system_prompt: str,
        pydantic_model: type[BaseModel]
) -> Dict:
    """
    Runs the main evaluation loop, saving successful results for later scoring.
    """
    try:
        client = get_client()
        print("✅ OpenAI client initialized.")
    except RuntimeError as e:
        print(f"❌ {e}\n   Please ensure NEBIUS_API_KEY or OPENAI_API_KEY is set.")
        sys.exit(1)

    results = {
        'by_model': {model: {'success': 0, 'failures': 0, 'latencies': []} for model in models},
        'successful_outputs': []
    }

    total_calls = len(models) * len(phrases)
    current_call = 0

    cefr_list = ", ".join([level.value for level in CEFR])
    category_list = ", ".join([cat.value for cat in PhraseCategory])
    json_schema = {"guided_json": pydantic_model.model_json_schema()}

    for model_id in models:
        print(f"\n🚀 Testing Model: {model_id}")
        for phrase in phrases:
            current_call += 1
            print(f"  [{current_call}/{total_calls}] Phrase: '{phrase['text']}'...", end=' ', flush=True)

            start_time = time.perf_counter()

            try:
                params = {
                    "text": phrase['text'], "language": phrase['language'],
                    "cefr_list": cefr_list, "category_list": category_list,
                }
                messages = get_templated_messages(system_prompt=system_prompt, user_prompt="", params=params)

                response_str = answer_with_llm(
                    client=client, messages=messages, model=model_id,
                    extra_body=json_schema, temperature=0.0,
                )

                validated_output = pydantic_model.model_validate_json(response_str)

                results['by_model'][model_id]['success'] += 1
                results['successful_outputs'].append({
                    "model_id": model_id,
                    "phrase": phrase,
                    "output": validated_output.model_dump(),
                    "score": None  # Placeholder for manual scoring
                })
                print("✅ Success")

            except (ValidationError, json.JSONDecodeError) as e:
                results['by_model'][model_id]['failures'] += 1
                print(f"❌ FAILED (Validation: {type(e).__name__})")
            except Exception as e:
                results['by_model'][model_id]['failures'] += 1
                print(f"❌ FAILED (API Error: {e})")

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            results['by_model'][model_id]['latencies'].append(latency_ms)

    return results


def save_results_for_review(successful_outputs: List[Dict], filename="gauntlet_results_for_review.jsonl"):
    """Saves the successful outputs to a .jsonl file for manual scoring."""
    if not successful_outputs:
        print("\nNo successful outputs to save.")
        return

    with open(filename, 'w', encoding='utf-8') as f:
        for item in successful_outputs:
            f.write(json.dumps(item) + '\n')
    print(f"\n✅ All successful outputs saved to '{filename}'.")
    print("   Next step: Manually edit this file to add a numeric 'score' to each entry.")


def print_summary(results: Dict):
    """Prints a summary of technical performance (success rate and latency)."""
    summary_data = []
    for model, data in results['by_model'].items():
        total = data['success'] + data['failures']
        success_rate = (data['success'] / total) * 100 if total > 0 else 0
        avg_latency = sum(data['latencies']) / len(data['latencies']) if data['latencies'] else 0
        summary_data.append({
            'Model': model,
            'Success Rate (%)': success_rate,
            'Avg. Latency (ms)': avg_latency,
            'Valid Outputs': data['success']
        })

    summary_data.sort(key=lambda x: (x['Success Rate (%)'], -x['Avg. Latency (ms)']), reverse=True)

    print("\n\n--- 📊 Gauntlet Technical Summary 📊 ---\n")
    if not summary_data:
        print("No results to display.")
        return

    headers = summary_data[0].keys()
    col_widths = {h: max(len(h), max(
        (len(f"{row[h]:.2f}") if isinstance(row[h], float) else len(str(row[h]))) for row in summary_data)) for h in
                  headers}
    header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
    print(header_line)
    print("-" * len(header_line))

    for row in summary_data:
        row_items = [
            f"{row[h]:.2f}".ljust(col_widths[h]) if isinstance(row[h], float) else str(row[h]).ljust(col_widths[h]) for
            h in headers]
        print(" | ".join(row_items))
    print("\n" + "=" * len(header_line))


def main():
    parser = argparse.ArgumentParser(
        description="A standalone script to evaluate LLMs and collect their outputs for quality review.",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--service-file', required=True, help="Path to the service file to analyze.")
    parser.add_argument('--models', required=True, nargs='+', help="One or more model IDs to test.")
    parser.add_argument('--phrases', required=True,
                        help='JSON string of a list of {"text": str, "language": str} objects.')
    args = parser.parse_args()

    prompt, pydantic_src, pydantic_name = extract_from_service_file(args.service_file)
    DynamicModel = create_pydantic_model_from_source(pydantic_name, pydantic_src)

    try:
        phrases_list = json.loads(args.phrases)
        assert isinstance(phrases_list, list) and all('text' in d and 'language' in d for d in phrases_list)
    except (json.JSONDecodeError, AssertionError):
        print("❌ ERROR: --phrases argument is not a valid JSON string of objects with 'text' and 'language' keys.")
        sys.exit(1)

    results = run_gauntlet(args.models, phrases_list, prompt, DynamicModel)
    print_summary(results)
    save_results_for_review(results['successful_outputs'])


if __name__ == "__main__":
    # Example:
    # python model_gauntlet.py --service-file services/enrich_phrase_details.py --models "mistralai/Mistral-Nemo-Instruct-2407" "google/gemma-2-9b-it" --phrases '[{"text": "A piece of cake", "language": "en"}, {"text": "Das ist unter aller Sau", "language": "de"}]'
    main()
